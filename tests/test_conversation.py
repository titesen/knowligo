"""
Tests para agent/conversation.py — Máquina de estados.
"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agent.conversation import (
    ConversationManager,
    IDLE,
    REG_AWAIT_NAME,
    REG_AWAIT_COMPANY,
    TICKET_AWAIT_SUBJECT,
)
from agent.db_service import DBService

_SCHEMA_PATH = project_root / "database" / "schema" / "schema.sql"


@pytest.fixture
def conv(tmp_path) -> ConversationManager:
    """ConversationManager con DB temporal (solo schema, sin seeds)."""
    db_file = tmp_path / "test.db"
    import sqlite3

    conn = sqlite3.connect(db_file)
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()

    db = DBService(db_file)
    return ConversationManager(db)


class TestConversationManager:
    def test_initial_state_is_idle(self, conv):
        assert conv.get_state("5491111111111") == IDLE

    def test_set_state(self, conv):
        conv.set_state("5491111111111", REG_AWAIT_NAME, {})
        assert conv.get_state("5491111111111") == REG_AWAIT_NAME

    def test_set_invalid_state_raises(self, conv):
        with pytest.raises(ValueError, match="Estado inválido"):
            conv.set_state("5491111111111", "INVALID_STATE", {})

    def test_update_context(self, conv):
        conv.set_state("5491111111111", REG_AWAIT_NAME, {"name": "Juan"})
        conv.update_context("5491111111111", email="juan@test.com")
        ctx = conv.get_context("5491111111111")
        assert ctx["name"] == "Juan"
        assert ctx["email"] == "juan@test.com"

    def test_get_full(self, conv):
        conv.set_state("5491111111111", REG_AWAIT_COMPANY, {"name": "Juan"})
        state, ctx = conv.get_full("5491111111111")
        assert state == REG_AWAIT_COMPANY
        assert ctx["name"] == "Juan"

    def test_reset(self, conv):
        conv.set_state("5491111111111", TICKET_AWAIT_SUBJECT, {"x": 1})
        conv.reset("5491111111111")
        assert conv.get_state("5491111111111") == IDLE
        assert conv.get_context("5491111111111") == {}

    def test_is_active_flow(self, conv):
        assert conv.is_active_flow("5491111111111") is False
        conv.set_state("5491111111111", REG_AWAIT_NAME, {})
        assert conv.is_active_flow("5491111111111") is True

    def test_set_state_preserves_context_when_none(self, conv):
        """set_state con context=None mantiene el contexto previo."""
        conv.set_state("5491111111111", REG_AWAIT_NAME, {"name": "Test"})
        conv.set_state("5491111111111", REG_AWAIT_COMPANY)
        ctx = conv.get_context("5491111111111")
        assert ctx["name"] == "Test"
