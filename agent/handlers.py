"""
Handlers — Lógica de negocio para flujos multi-turn.

Cada handler recibe (phone, message, client, state, context)
y devuelve un string de respuesta para el usuario.
"""

import logging
import re
from typing import Dict, Optional

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

logger = logging.getLogger(__name__)

# Helpers

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

VALID_PRIORITIES = {"baja", "media", "alta", "crítica"}
PRIORITY_MAP = {
    "baja": "Baja",
    "media": "Media",
    "alta": "Alta",
    "crítica": "Crítica",
    "critica": "Crítica",
}


def _format_price(amount: float) -> str:
    """Formatea un precio en ARS."""
    return f"${amount:,.0f}".replace(",", ".")


#  REGISTRO DE NUEVO CLIENTE


def start_registration(phone: str, conv: ConversationManager) -> str:
    """Inicia el flujo de registro."""
    conv.set_state(phone, REG_AWAIT_NAME, {})
    return (
        "¡Bienvenido a KnowLigo! Para registrarlo como cliente necesito algunos datos.\n\n"
        "¿Cuál es su nombre completo?"
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
            return "Por favor, ingrese un nombre válido (mínimo 2 caracteres)."
        conv.set_state(phone, REG_AWAIT_COMPANY, {"name": name})
        return f"Gracias, {name}. ¿Cuál es el nombre de su empresa u organización?"

    if state == REG_AWAIT_COMPANY:
        company = message.strip()
        if len(company) < 2:
            return "Por favor, ingrese un nombre de empresa válido."
        conv.update_context(phone, company=company)
        conv.set_state(phone, REG_AWAIT_EMAIL)
        return "¿Cuál es su dirección de correo electrónico?"

    if state == REG_AWAIT_EMAIL:
        email = message.strip().lower()
        if not _EMAIL_RE.match(email):
            return "El formato del email no es válido. Por favor, ingrese un email correcto (ej: nombre@empresa.com)."

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
        "¿Cuál es el asunto o título del problema? (breve descripción)"
    )


def handle_create_ticket(
    phone: str,
    message: str,
    state: str,
    context: Dict,
    conv: ConversationManager,
    db: DBService,
) -> str:
    """Procesa los pasos de creación de ticket."""

    if state == TICKET_AWAIT_SUBJECT:
        subject = message.strip()
        if len(subject) < 5:
            return "Por favor, describa el asunto con al menos 5 caracteres."
        conv.update_context(phone, subject=subject)
        conv.set_state(phone, TICKET_AWAIT_DESCRIPTION)
        return "Describa el problema con más detalle. ¿Qué está ocurriendo?"

    if state == TICKET_AWAIT_DESCRIPTION:
        description = message.strip()
        if len(description) < 10:
            return "Por favor, proporcione una descripción más detallada (mínimo 10 caracteres)."
        conv.update_context(phone, description=description)
        conv.set_state(phone, TICKET_AWAIT_PRIORITY)
        return (
            "¿Cuál es la prioridad del ticket?\n\n"
            "• *Baja* — No afecta operaciones\n"
            "• *Media* — Afecta parcialmente\n"
            "• *Alta* — Impacto significativo\n"
            "• *Crítica* — Operación detenida\n\n"
            "Escriba la prioridad:"
        )

    if state == TICKET_AWAIT_PRIORITY:
        priority_input = message.strip().lower()
        priority = PRIORITY_MAP.get(priority_input)
        if not priority:
            return "Prioridad no válida. Elija: Baja, Media, Alta o Crítica."

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
) -> str:
    """Inicia el flujo de contratación mostrando planes disponibles."""
    lines = ["Estos son nuestros planes disponibles:\n"]
    for p in plans:
        lines.append(
            f"*{p['id']}. {p['name']}* — {_format_price(p['price_ars'])}/mes\n"
            f"   {p['description'][:80]}…"
        )

    lines.append("\nEscriba el *número* del plan que desea contratar:")
    conv.set_state(phone, CONTRACT_AWAIT_PLAN, {"client_id": client["id"]})
    return "\n".join(lines)


def handle_contract_plan(
    phone: str,
    message: str,
    state: str,
    context: Dict,
    conv: ConversationManager,
    db: DBService,
) -> str:
    """Procesa los pasos de contratación de plan."""

    if state == CONTRACT_AWAIT_PLAN:
        try:
            plan_id = int(message.strip())
        except ValueError:
            return "Por favor, escriba el número del plan (1, 2 o 3)."

        plan = db.get_plan_by_id(plan_id)
        if not plan:
            return "Plan no encontrado. Escriba el número del plan (1, 2 o 3)."

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

        return (
            f"Ha seleccionado el *Plan {plan['name']}*:\n\n"
            f"• Precio: {_format_price(plan['price_ars'])}/mes (ARS, sujeto a ajuste trimestral)\n"
            f"• Tickets/mes: {plan['max_tickets_month'] or 'Ilimitados'}\n"
            f"• Horario: {plan['support_hours']}\n"
            f"• Incluye: {features_text}\n"
            f"• Mantenimiento: {plan['maintenance_frequency']}\n\n"
            f"¿Confirma la contratación? Responda *sí* o *no*."
        )

    if state == CONTRACT_AWAIT_CONFIRM:
        answer = message.strip().lower()
        if answer in ("sí", "si", "s", "yes", "confirmo", "dale"):
            conv.set_state(phone, CONTRACT_AWAIT_PAYMENT)
            return (
                "Perfecto. Para completar la contratación, seleccione el método de pago:\n\n"
                "1. Transferencia bancaria\n"
                "2. Tarjeta de crédito\n"
                "3. Mercado Pago\n\n"
                "Escriba el número de su preferencia:"
            )
        elif answer in ("no", "n", "cancelar"):
            conv.reset(phone)
            return "Contratación cancelada. ¿Puedo ayudarle con algo más?"
        else:
            return "Por favor, responda *sí* para confirmar o *no* para cancelar."

    if state == CONTRACT_AWAIT_PAYMENT:
        payment_methods = {
            "1": "Transferencia bancaria",
            "2": "Tarjeta de crédito",
            "3": "Mercado Pago",
        }
        method = payment_methods.get(message.strip())
        if not method:
            return "Opción no válida. Escriba 1, 2 o 3."

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
