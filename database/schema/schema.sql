PRAGMA foreign_keys = ON;

-- PLANES DE SERVICIO
CREATE TABLE plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    price_ars REAL NOT NULL DEFAULT 0,
    max_tickets_month INTEGER,          -- NULL = ilimitado
    support_hours TEXT NOT NULL DEFAULT 'Lun-Vie 08:00-18:00',
    includes_onsite INTEGER NOT NULL DEFAULT 0,
    includes_backup INTEGER NOT NULL DEFAULT 0,
    includes_drp INTEGER NOT NULL DEFAULT 0,
    maintenance_frequency TEXT,         -- trimestral, mensual, semanal
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- CLIENTES
CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    industry TEXT,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    contact_phone TEXT,
    phone TEXT UNIQUE,                  -- WhatsApp E.164 sin '+' (ej: 5493794285297)
    employee_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_clients_phone ON clients(phone);

-- CONTRATOS
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'Activo',   -- Activo, Cancelado, Suspendido, Vencido
    monthly_amount REAL,
    notes TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (plan_id) REFERENCES plans(id)
);

CREATE INDEX idx_contracts_client ON contracts(client_id);
CREATE INDEX idx_contracts_status ON contracts(status);

-- TICKETS DE SOPORTE
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    priority TEXT NOT NULL CHECK(priority IN ('Baja', 'Media', 'Alta', 'Crítica')),
    status TEXT NOT NULL CHECK(status IN ('Abierto', 'En progreso', 'Esperando cliente', 'Resuelto', 'Cerrado')),
    category TEXT,                      -- Hardware, Software, Red, Seguridad, Backup, Otro
    subject TEXT NOT NULL,
    description TEXT,
    assigned_to TEXT,
    resolution TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    resolved_at TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE INDEX idx_tickets_client ON tickets(client_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);

-- LOGS DE QUERIES DEL CHATBOT
CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    query TEXT NOT NULL,
    intent TEXT,
    response TEXT,
    success INTEGER DEFAULT 1,
    error TEXT,
    tokens_used INTEGER DEFAULT 0,
    processing_time REAL DEFAULT 0.0,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_timestamp ON query_logs(user_id, timestamp);

-- CONVERSACIONES (estado del agente por teléfono)
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL DEFAULT 'IDLE',
    context TEXT NOT NULL DEFAULT '{}', -- JSON blob
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_conversations_phone ON conversations(phone);

-- PAGOS (mock de pasarela)
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pendiente'
        CHECK(status IN ('Pendiente', 'Aprobado', 'Rechazado')),
    payment_method TEXT NOT NULL DEFAULT 'Transferencia',
    reference_code TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

CREATE INDEX idx_payments_contract ON payments(contract_id);
