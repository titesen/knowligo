"""
Handlers — Lógica de negocio para flujos multi-turn.

Cada handler recibe (phone, message, client, state, context)
y devuelve un string de respuesta para el usuario.
"""

import logging
import re
from typing import Dict, Optional, Union

from agent.conversation import (
    ConversationManager,
    IDLE,
    REG_AWAIT_NAME,
    REG_AWAIT_COMPANY,
    REG_AWAIT_EMAIL,
    TICKET_AWAIT_SUBJECT,
    TICKET_AWAIT_DESCRIPTION,
    TICKET_AWAIT_PRIORITY,
    CONTRACT_AWAIT_PLAN,
    CONTRACT_AWAIT_CONFIRM,
    CONTRACT_AWAIT_PAYMENT,
)
from agent.db_service import DBService
from agent.messages import (
    AgentResponse,
    ButtonMessage,
    ListMessage,
    ListRow,
    ListSection,
    ReplyButton,
)

logger = logging.getLogger(__name__)

# Hint de cancelación que se muestra en cada paso de los flujos
_CANCEL_HINT = "\n\n_(Escribí *cancelar* para salir del proceso)_"

# Helpers

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

VALID_PRIORITIES = {"baja", "media", "alta", "crítica"}
PRIORITY_MAP = {
    "baja": "Baja",
    "media": "Media",
    "alta": "Alta",
    "crítica": "Crítica",
    "critica": "Crítica",
    # Interactive button IDs (WhatsApp list_reply)
    "prioridad_baja": "Baja",
    "prioridad_media": "Media",
    "prioridad_alta": "Alta",
    "prioridad_critica": "Crítica",
}

# Mapeo fuzzy para lenguaje natural → prioridad
_FUZZY_PRIORITY = {
    # Baja
    "no es grave": "Baja",
    "no es urgente": "Baja",
    "poco importante": "Baja",
    "puede esperar": "Baja",
    "cuando puedan": "Baja",
    "sin apuro": "Baja",
    "leve": "Baja",
    "menor": "Baja",
    "bajo": "Baja",
    # Media
    "normal": "Media",
    "moderada": "Media",
    "moderado": "Media",
    "intermedia": "Media",
    "medio": "Media",
    "regular": "Media",
    # Alta
    "importante": "Alta",
    "bastante importante": "Alta",
    "urgente": "Alta",
    "grave": "Alta",
    "serio": "Alta",
    "seria": "Alta",
    "afecta mucho": "Alta",
    "impacto alto": "Alta",
    # Crítica
    "muy urgente": "Crítica",
    "es urgente": "Crítica",
    "super urgente": "Crítica",
    "crítico": "Crítica",
    "critico": "Crítica",
    "emergencia": "Crítica",
    "no podemos trabajar": "Crítica",
    "parado": "Crítica",
    "detenido": "Crítica",
    "caído": "Crítica",
    "caido": "Crítica",
    "máxima": "Crítica",
    "maxima": "Crítica",
}


def _parse_priority(text: str) -> str | None:
    """Intenta parsear prioridad desde texto libre.

    1. Exacto against PRIORITY_MAP
    2. Fuzzy against _FUZZY_PRIORITY (longest match first)
    3. None si no se pudo determinar
    """
    key = text.strip().lower()

    # 1. Exacto
    if key in PRIORITY_MAP:
        return PRIORITY_MAP[key]

    # 2. Fuzzy — buscar si alguna frase clave aparece en el texto
    #    Ordenar por longitud descendente para que frases más específicas
    #    ("muy urgente") coincidan antes que substrings genéricos ("urgente")
    for phrase, priority in sorted(
        _FUZZY_PRIORITY.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if phrase in key:
            return priority

    return None


# Mapeo fuzzy para selección de planes
_PLAN_KEYWORDS: dict[str, int] = {
    "básico": 1,
    "basico": 1,
    "basic": 1,
    "primero": 1,
    "primer": 1,
    "el 1": 1,
    "profesional": 2,
    "professional": 2,
    "segundo": 2,
    "el 2": 2,
    "empresarial": 3,
    "enterprise": 3,
    "tercero": 3,
    "tercer": 3,
    "el 3": 3,
    # Interactive button IDs (WhatsApp list_reply)
    "plan_1": 1,
    "plan_2": 2,
    "plan_3": 3,
}


def _parse_plan_selection(text: str, db: DBService) -> dict | None:
    """Parsea selección de plan desde texto libre.

    Acepta: número (1/2/3), nombre del plan, o expresiones coloquiales.
    """
    clean = text.strip().lower()

    # 1. Número directo
    try:
        plan_id = int(clean)
        return db.get_plan_by_id(plan_id)
    except ValueError:
        pass

    # 2. Keyword matching
    for keyword, plan_id in _PLAN_KEYWORDS.items():
        if keyword in clean:
            return db.get_plan_by_id(plan_id)

    return None


def _format_price(amount: float) -> str:
    """Formatea un precio en ARS."""
    return f"${amount:,.0f}".replace(",", ".")


#  REGISTRO DE NUEVO CLIENTE


def start_registration(phone: str, conv: ConversationManager) -> str:
    """Inicia el flujo de registro."""
    conv.set_state(phone, REG_AWAIT_NAME, {})
    return (
        "¡Bienvenido a KnowLigo! Para registrarlo como cliente necesito algunos datos.\n\n"
        "¿Cuál es su nombre completo?" + _CANCEL_HINT
    )


def handle_registration(
    phone: str,
    message: str,
    state: str,
    context: Dict,
    conv: ConversationManager,
    db: DBService,
) -> str:
    """Procesa los pasos del flujo de registro."""

    if state == REG_AWAIT_NAME:
        name = message.strip()
        if len(name) < 2:
            return (
                "Por favor, ingrese un nombre válido (mínimo 2 caracteres)."
                + _CANCEL_HINT
            )
        conv.set_state(phone, REG_AWAIT_COMPANY, {"name": name})
        return (
            f"Gracias, {name}. ¿Cuál es el nombre de su empresa u organización?"
            + _CANCEL_HINT
        )

    if state == REG_AWAIT_COMPANY:
        company = message.strip()
        if len(company) < 2:
            return "Por favor, ingrese un nombre de empresa válido." + _CANCEL_HINT
        conv.update_context(phone, company=company)
        conv.set_state(phone, REG_AWAIT_EMAIL)
        return "¿Cuál es su dirección de correo electrónico?" + _CANCEL_HINT

    if state == REG_AWAIT_EMAIL:
        email = message.strip().lower()
        if not _EMAIL_RE.match(email):
            return (
                "El formato del email no es válido. Por favor, ingrese un email correcto (ej: nombre@empresa.com)."
                + _CANCEL_HINT
            )

        # Crear el cliente
        ctx = conv.get_context(phone)
        client = db.create_client(
            name=ctx["company"],
            contact_name=ctx["name"],
            contact_email=email,
            phone=phone,
        )

        conv.reset(phone)

        return (
            f"✅ ¡Registro completado exitosamente!\n\n"
            f"• Nombre: {ctx['name']}\n"
            f"• Empresa: {ctx['company']}\n"
            f"• Email: {email}\n"
            f"• ID de cliente: #{client['id']}\n\n"
            f"Ahora puede consultar planes, crear tickets de soporte y más. "
            f"¿En qué puedo ayudarle?"
        )

    return "Ha ocurrido un error en el registro. Intente nuevamente."


#  CREAR TICKET


def start_create_ticket(phone: str, client: Dict, conv: ConversationManager) -> str:
    """Inicia el flujo de creación de ticket."""
    conv.set_state(phone, TICKET_AWAIT_SUBJECT, {"client_id": client["id"]})
    return (
        "Vamos a crear un ticket de soporte.\n\n"
        "¿Cuál es el asunto o título del problema? (breve descripción)" + _CANCEL_HINT
    )


def handle_create_ticket(
    phone: str,
    message: str,
    state: str,
    context: Dict,
    conv: ConversationManager,
    db: DBService,
) -> AgentResponse:
    """Procesa los pasos de creación de ticket."""

    if state == TICKET_AWAIT_SUBJECT:
        subject = message.strip()
        if len(subject) < 5:
            return (
                "Por favor, describa el asunto con al menos 5 caracteres."
                + _CANCEL_HINT
            )
        conv.update_context(phone, subject=subject)
        conv.set_state(phone, TICKET_AWAIT_DESCRIPTION)
        return (
            "Describa el problema con más detalle. ¿Qué está ocurriendo?" + _CANCEL_HINT
        )

    if state == TICKET_AWAIT_DESCRIPTION:
        description = message.strip()
        if len(description) < 10:
            return (
                "Por favor, proporcione una descripción más detallada (mínimo 10 caracteres)."
                + _CANCEL_HINT
            )
        conv.update_context(phone, description=description)
        conv.set_state(phone, TICKET_AWAIT_PRIORITY)
        return ListMessage(
            body="¿Cuál es la prioridad del ticket?",
            button_text="Elegir prioridad",
            footer="_(Escribí *cancelar* para salir del proceso)_",
            sections=[
                ListSection(
                    title="Prioridad",
                    rows=[
                        ListRow("prioridad_baja", "Baja", "No afecta operaciones"),
                        ListRow("prioridad_media", "Media", "Afecta parcialmente"),
                        ListRow("prioridad_alta", "Alta", "Impacto significativo"),
                        ListRow("prioridad_critica", "Crítica", "Operación detenida"),
                    ],
                ),
            ],
        )

    if state == TICKET_AWAIT_PRIORITY:
        priority = _parse_priority(message)
        if not priority:
            return ListMessage(
                body='No pude identificar la prioridad. También vale algo como "es urgente" o "puede esperar".',
                button_text="Elegir prioridad",
                footer="_(Escribí *cancelar* para salir del proceso)_",
                sections=[
                    ListSection(
                        title="Prioridad",
                        rows=[
                            ListRow("prioridad_baja", "Baja", "No afecta operaciones"),
                            ListRow("prioridad_media", "Media", "Afecta parcialmente"),
                            ListRow("prioridad_alta", "Alta", "Impacto significativo"),
                            ListRow(
                                "prioridad_critica", "Crítica", "Operación detenida"
                            ),
                        ],
                    ),
                ],
            )

        ctx = conv.get_context(phone)
        ticket = db.create_ticket(
            client_id=ctx["client_id"],
            subject=ctx["subject"],
            description=ctx["description"],
            priority=priority,
        )

        conv.reset(phone)

        return (
            f"✅ Ticket creado exitosamente.\n\n"
            f"• Ticket #{ticket['id']}\n"
            f"• Asunto: {ticket['subject']}\n"
            f"• Prioridad: {ticket['priority']}\n"
            f"• Estado: {ticket['status']}\n\n"
            f"Nuestro equipo técnico lo revisará a la brevedad. "
            f"¿Necesita algo más?"
        )

    return "Ha ocurrido un error creando el ticket. Intente nuevamente."


#  CONTRATAR PLAN


def start_contract_plan(
    phone: str, client: Dict, plans: list, conv: ConversationManager
) -> AgentResponse:
    """Inicia el flujo de contratación mostrando planes disponibles."""
    rows = []
    for p in plans:
        rows.append(
            ListRow(
                id=f"plan_{p['id']}",
                title=p["name"],
                description=f"{_format_price(p['price_ars'])}/mes",
            )
        )

    conv.set_state(phone, CONTRACT_AWAIT_PLAN, {"client_id": client["id"]})
    return ListMessage(
        body="Estos son nuestros planes disponibles:",
        button_text="Ver planes",
        footer="_(Escribí *cancelar* para salir del proceso)_",
        sections=[
            ListSection(title="Planes", rows=rows),
        ],
    )


def handle_contract_plan(
    phone: str,
    message: str,
    state: str,
    context: Dict,
    conv: ConversationManager,
    db: DBService,
) -> AgentResponse:
    """Procesa los pasos de contratación de plan."""

    if state == CONTRACT_AWAIT_PLAN:
        plan = _parse_plan_selection(message.strip(), db)
        if not plan:
            return (
                "Por favor, indicá el plan: el número (1, 2 o 3), "
                "o su nombre (básico, profesional, empresarial)." + _CANCEL_HINT
            )

        plan_id = plan["id"]

        conv.update_context(phone, plan_id=plan_id)
        conv.set_state(phone, CONTRACT_AWAIT_CONFIRM)

        features = []
        if plan["includes_onsite"]:
            features.append("Soporte presencial")
        if plan["includes_backup"]:
            features.append("Backup")
        if plan["includes_drp"]:
            features.append("DRP")
        features_text = ", ".join(features) if features else "Soporte remoto"

        return ButtonMessage(
            body=(
                f"Ha seleccionado el *Plan {plan['name']}*:\n\n"
                f"• Precio: {_format_price(plan['price_ars'])}/mes (ARS, sujeto a ajuste trimestral)\n"
                f"• Tickets/mes: {plan['max_tickets_month'] or 'Ilimitados'}\n"
                f"• Horario: {plan['support_hours']}\n"
                f"• Incluye: {features_text}\n"
                f"• Mantenimiento: {plan['maintenance_frequency']}\n\n"
                f"¿Confirma la contratación?"
            ),
            buttons=[
                ReplyButton("confirmar_si", "✅ Sí, confirmo"),
                ReplyButton("confirmar_no", "❌ No, cancelar"),
            ],
            footer="_(Escribí *cancelar* para salir del proceso)_",
        )

    if state == CONTRACT_AWAIT_CONFIRM:
        answer = message.strip().lower()
        if answer in (
            "sí",
            "si",
            "s",
            "yes",
            "confirmo",
            "dale",
            "confirmar_si",
            "✅ sí, confirmo",
        ):
            conv.set_state(phone, CONTRACT_AWAIT_PAYMENT)
            return ButtonMessage(
                body="Perfecto. Para completar la contratación, seleccioné el método de pago:",
                buttons=[
                    ReplyButton("pago_transferencia", "Transferencia"),
                    ReplyButton("pago_tarjeta", "Tarjeta de crédito"),
                    ReplyButton("pago_mercadopago", "Mercado Pago"),
                ],
                footer="_(Escribí *cancelar* para salir del proceso)_",
            )
        elif answer in ("no", "n", "cancelar", "confirmar_no", "❌ no, cancelar"):
            conv.reset(phone)
            return "Contratación cancelada. ¿Puedo ayudarle con algo más?"
        else:
            return (
                "Por favor, responda *sí* para confirmar o *no* para cancelar."
                + _CANCEL_HINT
            )

    if state == CONTRACT_AWAIT_PAYMENT:
        payment_methods = {
            "1": "Transferencia bancaria",
            "2": "Tarjeta de crédito",
            "3": "Mercado Pago",
            # IDs from interactive buttons
            "pago_transferencia": "Transferencia bancaria",
            "pago_tarjeta": "Tarjeta de crédito",
            "pago_mercadopago": "Mercado Pago",
            # Button titles (lowercase)
            "transferencia": "Transferencia bancaria",
            "tarjeta de crédito": "Tarjeta de crédito",
            "mercado pago": "Mercado Pago",
        }
        method = payment_methods.get(message.strip().lower()) or payment_methods.get(
            message.strip()
        )
        if not method:
            return "Opción no válida. Escriba 1, 2 o 3." + _CANCEL_HINT

        ctx = conv.get_context(phone)
        plan = db.get_plan_by_id(ctx["plan_id"])

        # Crear contrato
        contract = db.create_contract(
            client_id=ctx["client_id"],
            plan_id=ctx["plan_id"],
            monthly_amount=plan["price_ars"],
            notes=f"Contratado vía WhatsApp — Método: {method}",
        )

        # Registrar pago mock
        payment = db.create_payment(
            contract_id=contract["id"],
            amount=plan["price_ars"],
            payment_method=method,
        )

        conv.reset(phone)

        return (
            f"✅ ¡Contratación exitosa!\n\n"
            f"• Plan: {plan['name']}\n"
            f"• Monto mensual: {_format_price(plan['price_ars'])}\n"
            f"• Método de pago: {method}\n"
            f"• Código de referencia: {payment['reference_code']}\n"
            f"• Contrato #{contract['id']}\n\n"
            f"Bienvenido al plan {plan['name']} de KnowLigo. "
            f"¿Necesita algo más?"
        )

    return "Ha ocurrido un error en la contratación. Intente nuevamente."


#  HELPERS DE RESPUESTA RÁPIDA


def format_tickets_response(tickets: list) -> str:
    """Formatea lista de tickets para WhatsApp."""
    if not tickets:
        return "No tiene tickets abiertos en este momento."

    lines = [f"Tiene {len(tickets)} ticket(s) abierto(s):\n"]
    for t in tickets:
        emoji = {"Baja": "🟢", "Media": "🟡", "Alta": "🟠", "Crítica": "🔴"}.get(
            t["priority"], "⚪"
        )
        lines.append(
            f"{emoji} *#{t['id']}* — {t['subject']}\n"
            f"   Estado: {t['status']} | Prioridad: {t['priority']}"
        )
    lines.append("\n¿Desea crear un nuevo ticket o consultar algo más?")
    return "\n".join(lines)


def format_plans_response(plans: list) -> str:
    """Formatea lista de planes para WhatsApp."""
    lines = ["Estos son nuestros planes de soporte IT:\n"]
    for p in plans:
        lines.append(
            f"*{p['id']}. {p['name']}* — {_format_price(p['price_ars'])}/mes\n"
            f"   {p['description'][:100]}\n"
            f"   Tickets/mes: {p['max_tickets_month'] or 'Ilimitados'} | "
            f"Horario: {p['support_hours']}"
        )
    lines.append(
        "\nTodos los precios en ARS, sujetos a ajuste trimestral.\n"
        "Si desea contratar algún plan, escriba *contratar*."
    )
    return "\n".join(lines)


def format_account_response(client: Dict, contracts: list) -> str:
    """Formatea información de cuenta del cliente."""
    lines = [
        f"*Datos de su cuenta:*\n",
        f"• Empresa: {client['name']}",
        f"• Contacto: {client['contact_name']}",
        f"• Email: {client['contact_email']}",
        f"• ID Cliente: #{client['id']}",
    ]

    if contracts:
        lines.append(f"\n*Contratos activos ({len(contracts)}):*")
        for c in contracts:
            lines.append(
                f"• Plan {c['plan_name']} — {_format_price(c['plan_price'])}/mes "
                f"(desde {c['start_date']})"
            )
    else:
        lines.append("\nNo tiene contratos activos actualmente.")

    lines.append("\n¿Necesita algo más?")
    return "\n".join(lines)
