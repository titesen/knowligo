"""
Tests para agent/db_service.py — Capa de acceso a datos.

Usa una base de datos SQLite en memoria para cada test,
inicializada con el schema y seeds reales del proyecto.
"""

import sys
from pathlib import Path

import pytest

# Agregar raíz del proyecto al path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agent.db_service import DBService


# Fixtures

_SCHEMA_PATH = project_root / "database" / "schema" / "schema.sql"
_SEED_PATH = project_root / "database" / "seeds" / "seed.sql"


@pytest.fixture
def db(tmp_path) -> DBService:
    """DBService con schema + seeds en un DB temporal."""
    db_file = tmp_path / "test.db"
    service = DBService(db_file)

    # Crear schema y cargar seeds
    import sqlite3

    conn = sqlite3.connect(db_file)
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    with open(_SEED_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()

    return service


# Clients


class TestClientOperations:
    def test_find_existing_client_by_phone(self, db):
        client = db.find_client_by_phone("5493794285297")
        assert client is not None
        assert client["contact_name"] == "Facundo"
        assert client["name"] == "Demo Facundo"

    def test_find_nonexistent_client(self, db):
        assert db.find_client_by_phone("0000000000") is None

    def test_create_client(self, db):
        client = db.create_client(
            name="Test Company",
            contact_name="Juan Pérez",
            contact_email="juan@test.com",
            phone="5491199998888",
        )
        assert client["id"] is not None
        assert client["contact_name"] == "Juan Pérez"
        assert client["phone"] == "5491199998888"

        # Verificar que se puede encontrar por teléfono
        found = db.find_client_by_phone("5491199998888")
        assert found["id"] == client["id"]

    def test_get_client_by_id(self, db):
        client = db.get_client_by_id(1)
        assert client is not None
        assert client["name"] == "Acme Corp"


# Plans


class TestPlanOperations:
    def test_get_plans(self, db):
        plans = db.get_plans()
        assert len(plans) == 3
        assert plans[0]["name"] == "Básico"
        assert plans[2]["name"] == "Empresarial"

    def test_get_plan_by_id(self, db):
        plan = db.get_plan_by_id(2)
        assert plan is not None
        assert plan["name"] == "Profesional"

    def test_get_nonexistent_plan(self, db):
        assert db.get_plan_by_id(99) is None


# Contracts


class TestContractOperations:
    def test_get_active_contracts(self, db):
        # Client 1 (Acme Corp) has an active contract
        contracts = db.get_active_contracts(1)
        assert len(contracts) >= 1
        assert contracts[0]["status"] == "Activo"
        assert "plan_name" in contracts[0]

    def test_create_contract(self, db):
        contract = db.create_contract(
            client_id=1, plan_id=3, monthly_amount=999000, notes="Test"
        )
        assert contract["id"] is not None
        assert contract["status"] == "Activo"
        assert contract["plan_id"] == 3


# Tickets


class TestTicketOperations:
    def test_get_client_tickets(self, db):
        tickets = db.get_client_tickets(1)
        assert len(tickets) >= 1

    def test_get_open_tickets(self, db):
        # Client 9 (Demo Facundo) has an open ticket
        tickets = db.get_open_tickets(9)
        assert len(tickets) >= 1
        assert all(
            t["status"] in ("Abierto", "En progreso", "Esperando cliente")
            for t in tickets
        )

    def test_create_ticket(self, db):
        ticket = db.create_ticket(
            client_id=1,
            subject="Test ticket",
            description="This is a test",
            priority="Media",
        )
        assert ticket["id"] is not None
        assert ticket["status"] == "Abierto"
        assert ticket["subject"] == "Test ticket"


# Payments


class TestPaymentOperations:
    def test_create_payment(self, db):
        payment = db.create_payment(
            contract_id=1, amount=499000, payment_method="Transferencia bancaria"
        )
        assert payment["id"] is not None
        assert payment["status"] == "Aprobado"
        assert payment["reference_code"].startswith("PAY-")
        assert payment["amount"] == 499000


# Conversations


class TestConversationOperations:
    def test_get_nonexistent_conversation(self, db):
        assert db.get_conversation("9999999999") is None

    def test_upsert_and_get_conversation(self, db):
        db.upsert_conversation("5491111111111", "REG_AWAIT_NAME", {"step": 1})
        conv = db.get_conversation("5491111111111")
        assert conv is not None
        assert conv["state"] == "REG_AWAIT_NAME"
        assert conv["context"]["step"] == 1

    def test_upsert_updates_existing(self, db):
        db.upsert_conversation("5491111111111", "REG_AWAIT_NAME", {"step": 1})
        db.upsert_conversation("5491111111111", "REG_AWAIT_EMAIL", {"step": 2})
        conv = db.get_conversation("5491111111111")
        assert conv["state"] == "REG_AWAIT_EMAIL"
        assert conv["context"]["step"] == 2

    def test_clear_conversation(self, db):
        db.upsert_conversation("5491111111111", "REG_AWAIT_NAME", {"data": "x"})
        db.clear_conversation("5491111111111")
        conv = db.get_conversation("5491111111111")
        assert conv["state"] == "IDLE"
        assert conv["context"] == {}
