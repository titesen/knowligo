-- PLANES (precios en ARS mensuales)
INSERT INTO plans (name, description, price_ars, max_tickets_month, support_hours, includes_onsite, includes_backup, includes_drp, maintenance_frequency) VALUES
('Básico',       'Soporte remoto en horario laboral. Ideal para PyMEs con necesidades básicas de IT.',
    199000, 15, 'Lun-Vie 08:00-18:00', 0, 0, 0, 'trimestral'),
('Profesional',  'Soporte remoto y presencial con horario extendido. Para empresas con infraestructura de complejidad media.',
    499000, 40, 'Lun-Vie 08:00-20:00, Sáb 09:00-13:00', 1, 1, 0, 'mensual'),
('Empresarial',  'Soporte integral 24/7 con técnico dedicado, backup diario y DRP. Para empresas con operación crítica.',
    999000, NULL, '24/7 los 365 días', 1, 1, 1, 'semanal');

-- CLIENTES
INSERT INTO clients (name, industry, contact_name, contact_email, contact_phone, phone, employee_count, created_at) VALUES
('Acme Corp',              'Manufactura',     'Carlos Méndez',     'carlos.mendez@acme.com.ar',       '+54 11 4321-0001', '541143210001', 120, '2024-08-15'),
('Beta Solutions',         'Tecnología',       'Laura Fernández',   'laura@betasolutions.com.ar',      '+54 11 4321-0002', '541143210002', 45,  '2024-09-01'),
('Distribuidora del Sur',  'Logística',        'Martín Rodríguez',  'mrodriguez@delsur.com.ar',        '+54 11 4321-0003', '541143210003', 80,  '2024-10-10'),
('Estudio Contable Ríos',  'Servicios prof.', 'Ana Ríos',          'arios@estudiorios.com.ar',         '+54 11 4321-0004', '541143210004', 15,  '2024-11-01'),
('Clínica San Martín',     'Salud',            'Dr. Pablo Herrera', 'pherrera@clinicasanmartin.com.ar', '+54 11 4321-0005', '541143210005', 200, '2024-11-20'),
('Hotel Palermo',          'Hotelería',        'Sofía López',       'slopez@hotelpalermo.com.ar',      '+54 11 4321-0006', '541143210006', 60,  '2024-12-05'),
('Constructora Vial',      'Construcción',     'Jorge Domínguez',   'jdominguez@vialsa.com.ar',        '+54 11 4321-0007', '541143210007', 95,  '2025-01-10'),
('Farmacia Central',       'Salud',            'María Torres',      'mtorres@farmaciacentral.com.ar',  '+54 11 4321-0008', '541143210008', 25,  '2025-01-20'),
('Demo Facundo',           'Tecnología',       'Facundo',           'facundo@demo.com.ar',             '+54 9 3794 28-5297', '5493794285297', 10, '2025-02-01'),
('Demo Contacto',          'Consultoría',      'Contacto Test',     'contacto@demo.com.ar',            '+54 9 3794 10-3485', '5493794103485', 5,  '2025-02-01');

-- CONTRATOS
INSERT INTO contracts (client_id, plan_id, start_date, end_date, status, monthly_amount, notes) VALUES
(1, 2, '2024-09-01', NULL,          'Activo',    499000, 'Upgrade desde Básico en Nov 2024'),
(2, 1, '2024-09-15', NULL,          'Activo',    199000, NULL),
(3, 2, '2024-10-15', NULL,          'Activo',    499000, NULL),
(4, 1, '2024-11-01', NULL,          'Activo',    199000, NULL),
(5, 3, '2024-12-01', NULL,          'Activo',    999000, 'Incluye servidor dedicado en datacenter'),
(6, 1, '2024-12-10', '2025-06-10', 'Cancelado', 199000, 'Canceló por reducción de presupuesto'),
(7, 2, '2025-01-15', NULL,          'Activo',    499000, NULL),
(8, 1, '2025-02-01', NULL,          'Activo',    199000, 'En período de prueba 30 días'),
(9, 2, '2025-02-01', NULL,          'Activo',    499000, 'Demo — Plan Profesional'),
(10, 1, '2025-02-01', NULL,         'Activo',    199000, 'Demo — Plan Básico');

-- TICKETS DE SOPORTE
INSERT INTO tickets (client_id, priority, status, category, subject, description, assigned_to, resolution, created_at, updated_at, resolved_at) VALUES
-- Acme Corp (cliente 1) - Plan Profesional
(1, 'Alta',   'Resuelto',   'Red',       'Servidor de archivos no responde',
    'El servidor FS01 dejó de responder a las 10:30. Los usuarios no pueden acceder a las carpetas compartidas.',
    'Técnico: Alejandro Vega', 'Se reinició el servicio SMB y se actualizó la configuración de red. Se programó mantenimiento preventivo.',
    '2025-02-10 10:45:00', '2025-02-10 12:30:00', '2025-02-10 12:30:00'),

(1, 'Media',  'Resuelto',   'Software',  'Outlook no sincroniza emails',
    'Varios usuarios reportan que Outlook no descarga correos nuevos desde esta mañana.',
    'Técnico: Lucía Morales', 'Se reconfiguró el perfil de Outlook y se verificó la conectividad con Exchange Online.',
    '2025-02-15 09:00:00', '2025-02-15 11:00:00', '2025-02-15 11:00:00'),

(1, 'Baja',   'Cerrado',    'Hardware',  'Solicitud de mouse inalámbrico',
    'El sector de RRHH solicita 3 mouse inalámbricos para notebooks nuevas.',
    'Técnico: Alejandro Vega', 'Se coordinó la compra con el proveedor y se entregaron los periféricos.',
    '2025-02-18 14:00:00', '2025-02-20 10:00:00', '2025-02-20 10:00:00'),

-- Beta Solutions (cliente 2) - Plan Básico
(2, 'Media',  'Resuelto',   'Red',       'Problemas de acceso VPN',
    'No puedo conectarme a la VPN corporativa desde mi casa. Da error de autenticación.',
    'Técnico: Lucía Morales', 'Se renovaron las credenciales de VPN y se actualizó el cliente FortiClient.',
    '2025-02-12 08:30:00', '2025-02-12 14:00:00', '2025-02-12 14:00:00'),

(2, 'Baja',   'Resuelto',   'Software',  'Instalar Adobe Reader en 5 PCs',
    'Necesitamos Adobe Reader actualizado en las PCs del área comercial.',
    'Técnico: Alejandro Vega', 'Se instaló Adobe Acrobat Reader DC en las 5 PCs indicadas.',
    '2025-02-20 10:00:00', '2025-02-21 16:00:00', '2025-02-21 16:00:00'),

-- Distribuidora del Sur (cliente 3) - Plan Profesional
(3, 'Alta',   'Resuelto',   'Seguridad', 'Alerta de ransomware en PC de contabilidad',
    'El antivirus detectó un intento de ransomware en la PC de la contadora. Se aisló el equipo.',
    'Técnico: Alejandro Vega', 'Se eliminó la amenaza, se restauró desde backup del día anterior. Se reforzó la política de email.',
    '2025-02-08 07:15:00', '2025-02-08 11:00:00', '2025-02-08 11:00:00'),

(3, 'Media',  'En progreso','Backup',    'Falla en backup semanal',
    'El backup de Veeam del viernes falló con error de espacio en disco en el NAS.',
    'Técnico: Lucía Morales', NULL,
    '2025-03-03 09:00:00', '2025-03-03 10:30:00', NULL),

(3, 'Baja',   'Resuelto',   'Software',  'Actualizar Windows en 10 PCs',
    'Hay actualizaciones pendientes de Windows en varias PCs del depósito.',
    'Técnico: Alejandro Vega', 'Se actualizaron las 10 PCs a Windows 11 23H2 fuera de horario laboral.',
    '2025-02-25 11:00:00', '2025-02-27 20:00:00', '2025-02-27 20:00:00'),

-- Estudio Contable Ríos (cliente 4) - Plan Básico
(4, 'Media',  'Abierto',    'Software',  'Error en sistema de facturación',
    'El sistema Tango Gestión muestra error al intentar generar facturas electrónicas.',
    NULL, NULL,
    '2025-03-04 08:00:00', NULL, NULL),

(4, 'Baja',   'Resuelto',   'Hardware',  'Impresora no imprime',
    'La impresora HP LaserJet del piso 2 no imprime. Aparece como offline.',
    'Técnico: Lucía Morales', 'Se reinstalaron los drivers y se reconfiguró la cola de impresión.',
    '2025-02-28 15:00:00', '2025-02-28 16:30:00', '2025-02-28 16:30:00'),

-- Clínica San Martín (cliente 5) - Plan Empresarial
(5, 'Crítica','Resuelto',   'Red',       'Caída total de red en clínica',
    'Toda la red de la clínica cayó. No hay acceso a historias clínicas ni sistemas de turnos. URGENTE.',
    'Técnico: Alejandro Vega', 'Switch core averiado. Se reemplazó con equipo de respaldo en 45 minutos. Se configuró monitoreo SNMP.',
    '2025-02-14 03:22:00', '2025-02-14 04:10:00', '2025-02-14 04:10:00'),

(5, 'Alta',   'Resuelto',   'Seguridad', 'Certificado SSL vencido en portal de turnos',
    'El sitio web de turnos muestra advertencia de seguridad. Los pacientes no pueden sacar turnos online.',
    'Técnico: Lucía Morales', 'Se renovó el certificado Let''s Encrypt y se configuró renovación automática.',
    '2025-02-22 09:15:00', '2025-02-22 10:00:00', '2025-02-22 10:00:00'),

(5, 'Media',  'En progreso','Backup',    'Migración de backup a nuevo NAS',
    'Se debe migrar la política de backup de Veeam al nuevo NAS Synology adquirido por la clínica.',
    'Técnico: Alejandro Vega', NULL,
    '2025-03-01 10:00:00', '2025-03-02 14:00:00', NULL),

(5, 'Baja',   'Resuelto',   'Software',  'Configurar 15 PCs nuevas',
    'La clínica adquirió 15 notebooks Dell para los consultorios. Necesitan SO, Office y sistema de HCE.',
    'Técnico: Lucía Morales', 'Se configuraron las 15 notebooks con Windows 11 Pro, Office 365 y cliente HCE.',
    '2025-02-05 08:00:00', '2025-02-07 18:00:00', '2025-02-07 18:00:00'),

-- Constructora Vial (cliente 7) - Plan Profesional
(7, 'Alta',   'Abierto',    'Seguridad', 'Posible acceso no autorizado',
    'Se detectaron intentos de login fallidos masivos en el servidor de archivos desde una IP externa.',
    'Técnico: Alejandro Vega', NULL,
    '2025-03-04 07:00:00', '2025-03-04 07:30:00', NULL),

(7, 'Media',  'Resuelto',   'Red',       'Configurar WiFi en oficina nueva',
    'La constructora abrió una nueva oficina y necesita configuración de red WiFi para 20 usuarios.',
    'Técnico: Lucía Morales', 'Se instalaron 3 APs Ubiquiti, se configuró VLAN para invitados y red corporativa.',
    '2025-02-17 09:00:00', '2025-02-19 17:00:00', '2025-02-19 17:00:00'),

-- Farmacia Central (cliente 8) - Plan Básico
(8, 'Media',  'Esperando cliente', 'Software', 'Lentitud en sistema de stock',
    'El sistema de gestión de stock se vuelve muy lento después de las 3 PM.',
    'Técnico: Lucía Morales', NULL,
    '2025-03-02 16:00:00', '2025-03-03 09:00:00', NULL),

-- Demo Facundo (cliente 9) - Plan Profesional
(9, 'Media',  'Abierto',    'Software',  'Configurar VPN corporativa',
    'Necesito que configuren acceso VPN para trabajo remoto.',
    NULL, NULL,
    '2025-02-10 09:00:00', NULL, NULL),

(9, 'Baja',   'Resuelto',   'Hardware',  'Cambio de disco SSD',
    'La notebook principal tiene disco lento, pasar a SSD.',
    'Técnico: Alejandro Vega', 'Se reemplazó HDD por SSD NVMe 512GB y se migró Windows.',
    '2025-02-05 10:00:00', '2025-02-06 15:00:00', '2025-02-06 15:00:00');
