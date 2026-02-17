"""
DB Service — Capa de acceso a datos para el agente.

Encapsula TODAS las operaciones SQLite en métodos tipados,
evitando SQL inline disperso en el orquestador/handlers.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DBService:
    """Servicio de acceso a datos SQLite para el agente conversacional."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    # helpers

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # Clients

    def find_client_by_phone(self, phone: str) -> Optional[Dict]:
        """Busca un cliente por su número WhatsApp (E.164 sin '+')."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM clients WHERE phone = ?", (phone,)
            ).fetchone()
            return dict(row) if row else None

    def create_client(
        self,
        name: str,
        contact_name: str,
        contact_email: str,
        phone: str,
        industry: str = None,
        employee_count: int = None,
    ) -> Dict:
        """Registra un nuevo cliente y devuelve su dict."""
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO clients
                    (name, industry, contact_name, contact_email, contact_phone, phone, employee_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    industry,
                    contact_name,
                    contact_email,
                    phone,
                    phone,
                    employee_count,
                ),
            )
            conn.commit()
            client_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
            return dict(row)

    def get_client_by_id(self, client_id: int) -> Optional[Dict]:
        """Obtiene un cliente por ID."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
            return dict(row) if row else None

    # Plans

    def get_plans(self) -> List[Dict]:
        """Devuelve todos los planes ordenados por precio."""
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM plans ORDER BY price_ars").fetchall()
            return [dict(r) for r in rows]

    def get_plan_by_id(self, plan_id: int) -> Optional[Dict]:
        """Obtiene un plan por ID."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM plans WHERE id = ?", (plan_id,)
            ).fetchone()
            return dict(row) if row else None

    # Contracts

    def get_active_contracts(self, client_id: int) -> List[Dict]:
        """Contratos activos de un cliente con info del plan."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT c.*, p.name AS plan_name, p.price_ars AS plan_price
                FROM contracts c
                JOIN plans p ON c.plan_id = p.id
                WHERE c.client_id = ? AND c.status = 'Activo'
                ORDER BY c.start_date DESC
                """,
                (client_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def create_contract(
        self, client_id: int, plan_id: int, monthly_amount: float, notes: str = None
    ) -> Dict:
        """Crea un contrato nuevo."""
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO contracts (client_id, plan_id, start_date, status, monthly_amount, notes)
                VALUES (?, ?, ?, 'Activo', ?, ?)
                """,
                (
                    client_id,
                    plan_id,
                    datetime.now().strftime("%Y-%m-%d"),
                    monthly_amount,
                    notes,
                ),
            )
            conn.commit()
            contract_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM contracts WHERE id = ?", (contract_id,)
            ).fetchone()
            return dict(row)

    # Tickets

    def get_client_tickets(self, client_id: int, limit: int = 10) -> List[Dict]:
        """Tickets de un cliente, más recientes primero."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tickets
                WHERE client_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (client_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_open_tickets(self, client_id: int) -> List[Dict]:
        """Tickets abiertos / en progreso de un cliente."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tickets
                WHERE client_id = ? AND status IN ('Abierto', 'En progreso', 'Esperando cliente')
                ORDER BY created_at DESC
                """,
                (client_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def create_ticket(
        self,
        client_id: int,
        subject: str,
        description: str,
        priority: str = "Media",
        category: str = "Software",
    ) -> Dict:
        """Crea un ticket nuevo y lo devuelve."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tickets (client_id, priority, status, category, subject, description, created_at)
                VALUES (?, ?, 'Abierto', ?, ?, ?, ?)
                """,
                (client_id, priority, category, subject, description, now),
            )
            conn.commit()
            ticket_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
            ).fetchone()
            return dict(row)

    # Payments (mock)

    def create_payment(
        self,
        contract_id: int,
        amount: float,
        payment_method: str = "Transferencia",
    ) -> Dict:
        """Registra un pago mock (siempre aprobado para demo)."""
        ref_code = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO payments (contract_id, amount, status, payment_method, reference_code)
                VALUES (?, ?, 'Aprobado', ?, ?)
                """,
                (contract_id, amount, payment_method, ref_code),
            )
            conn.commit()
            payment_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
            return dict(row)

    # Conversations

    def get_conversation(self, phone: str) -> Optional[Dict]:
        """Obtiene el estado de conversación para un teléfono."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE phone = ?", (phone,)
            ).fetchone()
            if row:
                d = dict(row)
                d["context"] = json.loads(d["context"])
                return d
            return None

    def upsert_conversation(self, phone: str, state: str, context: Dict) -> None:
        """Crea o actualiza el estado de conversación."""
        now = datetime.now().isoformat()
        ctx_json = json.dumps(context, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO conversations (phone, state, context, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(phone) DO UPDATE SET
                    state = excluded.state,
                    context = excluded.context,
                    updated_at = excluded.updated_at
                """,
                (phone, state, ctx_json, now),
            )
            conn.commit()

    def clear_conversation(self, phone: str) -> None:
        """Limpia el estado de conversación (vuelve a IDLE)."""
        self.upsert_conversation(phone, "IDLE", {})

    def cleanup_stale_conversations(self, max_age_minutes: int = 30) -> int:
        """Elimina conversaciones inactivas. Retorna cuántas se limpiaron."""
        with self._conn() as conn:
            cursor = conn.execute(
                """
                DELETE FROM conversations
                WHERE state != 'IDLE'
                  AND updated_at < datetime('now', ? || ' minutes')
                """,
                (f"-{max_age_minutes}",),
            )
            conn.commit()
            return cursor.rowcount

    # Message history (from query_logs)

    def get_recent_messages(self, phone: str, limit: int = 6) -> list[dict]:
        """Obtiene los últimos mensajes usuario/asistente desde query_logs.

        Returns:
            Lista de dicts con 'role' y 'content', ordenados cronológicamente
            (más viejo primero). Formato compatible con OpenAI messages.
        """
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT query, response FROM query_logs
                WHERE user_id = ? AND success = 1
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (phone, limit),
            ).fetchall()

        # rows vienen DESC; invertir para orden cronológico
        messages: list[dict] = []
        for row in reversed(rows):
            messages.append({"role": "user", "content": row["query"]})
            if row["response"]:
                messages.append({"role": "assistant", "content": row["response"]})
        return messages
