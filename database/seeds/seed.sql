-- Planes
INSERT INTO plans (name, description) VALUES
('Básico', 'Soporte en horario laboral para incidencias de baja y media prioridad'),
('Profesional', 'Soporte para incidencias hasta prioridad alta'),
('Empresarial', 'Soporte extendido y atención prioritaria');

-- Clientes
INSERT INTO clients (name, contact_email, created_at) VALUES
('Acme Corp', 'it@acme.com', '2025-01-10'),
('Beta Solutions', 'support@beta.com', '2025-02-01');

-- Contratos
INSERT INTO contracts (client_id, plan_id, start_date) VALUES
(1, 2, '2025-01-15'),
(2, 1, '2025-02-05');

-- Tickets
INSERT INTO tickets (client_id, priority, status, subject, created_at) VALUES
(1, 'Alta', 'Abierto', 'Servidor no responde', '2025-02-10'),
(2, 'Media', 'En progreso', 'Problemas de acceso VPN', '2025-02-12');
