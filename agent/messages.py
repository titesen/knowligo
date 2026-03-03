"""
Messages — Modelos de respuesta para mensajes de WhatsApp interactivos.

Permite que el orchestrator y handlers retornen objetos tipados
que la capa API convierte al formato correcto:
- WhatsApp Cloud API → Interactive List / Reply Buttons
- Endpoint /query → texto plano (fallback)

Tipos soportados:
- TextMessage: mensaje de texto simple
- ListMessage: Interactive List (hasta 10 opciones en secciones)
- ButtonMessage: Reply Buttons (hasta 3 botones)

Spec de referencia:
https://developers.facebook.com/docs/whatsapp/cloud-api/messages/interactive-messages
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass(frozen=True)
class ListRow:
    """Una fila dentro de una sección de Interactive List."""

    id: str
    title: str
    description: str = ""


@dataclass(frozen=True)
class ListSection:
    """Sección de una Interactive List (título + filas)."""

    title: str
    rows: list[ListRow] = field(default_factory=list)


@dataclass(frozen=True)
class ReplyButton:
    """Un botón de tipo Reply Button."""

    id: str
    title: str


# Mensajes tipados


@dataclass(frozen=True)
class TextMessage:
    """Mensaje de texto simple (equivale a un str)."""

    body: str

    def to_text(self) -> str:
        """Serializa como texto plano."""
        return self.body


@dataclass(frozen=True)
class ListMessage:
    """
    Interactive List Message de WhatsApp.

    Muestra un cuerpo de texto + botón que abre una lista seleccionable
    con secciones y filas. Máximo 10 filas totales, títulos ≤24 chars.
    """

    body: str
    button_text: str
    sections: list[ListSection] = field(default_factory=list)
    header: str = ""
    footer: str = ""

    def to_text(self) -> str:
        """Serializa como texto plano con emojis (fallback sin WhatsApp)."""
        lines = []
        if self.header:
            lines.append(f"📌 *{self.header}*")
            lines.append("━━━━━━━━━━━━━━━━━━━━")
        if self.body:
            lines.append(self.body)
            lines.append("")
        for section in self.sections:
            if section.title:
                lines.append(f"*{section.title}*")
            for row in section.rows:
                desc = f" — {row.description}" if row.description else ""
                lines.append(f"• *{row.title}*{desc}")
            lines.append("")
        if self.footer:
            lines.append(self.footer)
        return "\n".join(lines).rstrip()

    def to_whatsapp_payload(self) -> dict:
        """Construye el objeto 'interactive' para la API de WhatsApp."""
        sections = []
        for section in self.sections:
            rows = []
            for row in section.rows:
                r = {"id": row.id, "title": row.title[:24]}
                if row.description:
                    r["description"] = row.description[:72]
                rows.append(r)
            sections.append({"title": section.title[:24], "rows": rows})

        interactive: dict = {
            "type": "list",
            "body": {"text": self.body},
            "action": {
                "button": self.button_text[:20],
                "sections": sections,
            },
        }
        if self.header:
            interactive["header"] = {"type": "text", "text": self.header[:60]}
        if self.footer:
            interactive["footer"] = {"text": self.footer[:60]}
        return interactive


@dataclass(frozen=True)
class ButtonMessage:
    """
    Reply Button Message de WhatsApp.

    Muestra un cuerpo de texto + hasta 3 botones inline.
    El usuario toca un botón y se envía el id + title al webhook.
    """

    body: str
    buttons: list[ReplyButton] = field(default_factory=list)
    header: str = ""
    footer: str = ""

    def to_text(self) -> str:
        """Serializa como texto plano con opciones numeradas (fallback)."""
        lines = []
        if self.header:
            lines.append(f"*{self.header}*\n")
        lines.append(self.body)
        if self.buttons:
            lines.append("")
            for i, btn in enumerate(self.buttons, 1):
                lines.append(f"{i}. {btn.title}")
        if self.footer:
            lines.append(f"\n{self.footer}")
        return "\n".join(lines).rstrip()

    def to_whatsapp_payload(self) -> dict:
        """Construye el objeto 'interactive' para la API de WhatsApp."""
        buttons = [
            {
                "type": "reply",
                "reply": {"id": btn.id, "title": btn.title[:20]},
            }
            for btn in self.buttons[:3]
        ]

        interactive: dict = {
            "type": "button",
            "body": {"text": self.body},
            "action": {"buttons": buttons},
        }
        if self.header:
            interactive["header"] = {"type": "text", "text": self.header[:60]}
        if self.footer:
            interactive["footer"] = {"text": self.footer[:60]}
        return interactive


# Union type para todo mensaje de respuesta
AgentResponse = Union[str, TextMessage, ListMessage, ButtonMessage]


def to_text(response: AgentResponse) -> str:
    """
    Extrae texto plano de cualquier tipo de respuesta del agente.

    - str → se retorna tal cual
    - TextMessage/ListMessage/ButtonMessage → se llama .to_text()

    Usar en /query endpoint y en tests para compatibilidad con str.
    """
    if isinstance(response, str):
        return response
    return response.to_text()
