PRAGMA foreign_keys = ON;

-- Clientes
CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Planes de servicio
CREATE TABLE plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

-- Contratos
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (plan_id) REFERENCES plans(id)
);

-- Tickets de soporte
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    subject TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);
