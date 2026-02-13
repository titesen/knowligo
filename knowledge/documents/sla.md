# Acuerdo de Nivel de Servicio (SLA) de KnowLigo

## Definiciones

- **Tiempo de respuesta inicial**: Tiempo máximo desde que se registra el ticket hasta que un técnico asignado contacta al usuario para iniciar el diagnóstico.
- **Tiempo de resolución objetivo**: Tiempo objetivo para resolver la incidencia completamente. No es un compromiso contractual absoluto, ya que depende de la complejidad del caso, pero es la meta operativa de KnowLigo.
- **Disponibilidad del servicio**: Porcentaje del tiempo en que los sistemas de soporte de KnowLigo (portal web, teléfono, email) están operativos y accesibles para los clientes.

## Tiempos de respuesta por prioridad y plan

### Plan Básico

| Prioridad | Tiempo de respuesta | Tiempo de resolución objetivo | Horario aplicable |
|---|---|---|---|
| Baja | 24 horas hábiles | 72 horas hábiles | L-V 08:00-18:00 |
| Media | 8 horas hábiles | 24 horas hábiles | L-V 08:00-18:00 |
| Alta | 4 horas hábiles | 12 horas hábiles | L-V 08:00-18:00 |
| Crítica | No disponible | No disponible | No aplica |

Nota: Las horas hábiles para el Plan Básico se cuentan únicamente de lunes a viernes de 08:00 a 18:00. Los tickets registrados fuera de este horario se atienden al inicio del siguiente día hábil.

### Plan Profesional

| Prioridad | Tiempo de respuesta | Tiempo de resolución objetivo | Horario aplicable |
|---|---|---|---|
| Baja | 16 horas hábiles | 48 horas hábiles | L-V 08:00-20:00, S 09:00-13:00 |
| Media | 6 horas hábiles | 16 horas hábiles | L-V 08:00-20:00, S 09:00-13:00 |
| Alta | 2 horas hábiles | 8 horas hábiles | L-V 08:00-20:00, S 09:00-13:00 |
| Crítica | No disponible | No disponible | No aplica |

### Plan Empresarial

| Prioridad | Tiempo de respuesta | Tiempo de resolución objetivo | Horario aplicable |
|---|---|---|---|
| Baja | 8 horas | 24 horas | 24/7/365 |
| Media | 4 horas | 12 horas | 24/7/365 |
| Alta | 2 horas | 6 horas | 24/7/365 |
| Crítica | 30 minutos | 4 horas | 24/7/365 |

Nota: Para el Plan Empresarial, las horas se cuentan de forma corrida (24/7), incluyendo fines de semana y feriados.

## Proceso de escalamiento

KnowLigo implementa un proceso de escalamiento estructurado para asegurar que las incidencias se resuelvan dentro de los tiempos comprometidos.

### Escalamiento por tiempo

- Si el tiempo de respuesta se excede en un 50%, se escala automáticamente al líder de equipo del nivel correspondiente.
- Si el tiempo de resolución objetivo se excede, se escala al gerente de operaciones y se notifica al ejecutivo de cuenta del cliente.
- Para incidencias de prioridad Crítica, el CTO de KnowLigo es notificado inmediatamente si no se resuelve dentro del 75% del tiempo objetivo.

### Escalamiento por nivel técnico

1. **Nivel 1 (Mesa de Ayuda)**: Resolución de incidencias estándar de usuario final. Si no se puede resolver en los primeros 30 minutos de trabajo activo, se escala a Nivel 2.
2. **Nivel 2 (Infraestructura)**: Problemas de red, servidores, servicios de directorio. Si requiere intervención de fabricante o conocimiento especializado, se escala a Nivel 3.
3. **Nivel 3 (Especialistas)**: Incidencias complejas que involucran múltiples sistemas, seguridad avanzada, o coordinación con proveedores externos.

## Compromisos de disponibilidad

| Componente | Disponibilidad garantizada |
|---|---|
| Portal de soporte web | 99.5% mensual |
| Línea telefónica de soporte | 99.0% mensual (en horario del plan) |
| Email de soporte | 99.5% mensual |
| Monitoreo de servidores (Plan Empresarial) | 99.9% mensual |

La disponibilidad se mide excluyendo ventanas de mantenimiento programado, las cuales son notificadas con al menos 48 horas de anticipación.

## Compensaciones por incumplimiento de SLA

Si KnowLigo no cumple con los tiempos de respuesta establecidos en el SLA en más del 10% de los tickets mensuales, se aplican las siguientes compensaciones:

| Nivel de incumplimiento | Compensación |
|---|---|
| Entre 10% y 20% de tickets fuera de SLA | 10% de descuento en la factura del mes siguiente |
| Entre 20% y 30% de tickets fuera de SLA | 20% de descuento en la factura del mes siguiente |
| Más del 30% de tickets fuera de SLA | 30% de descuento + reunión obligatoria con el cliente para plan de mejora |

Las compensaciones aplican únicamente a tiempos de respuesta inicial, no a tiempos de resolución objetivo, ya que estos últimos dependen de factores que pueden estar fuera del control de KnowLigo (ej: disponibilidad del usuario, tiempos de respuesta de fabricantes, adquisición de repuestos).

## Exclusiones del SLA

Los tiempos de SLA no aplican en los siguientes casos:

- Fallas causadas por desastres naturales, cortes de energía eléctrica generalizados o problemas de conectividad del proveedor de internet del cliente.
- Incidencias originadas por modificaciones realizadas por el cliente sin autorización de KnowLigo.
- Problemas causados por software no autorizado o no licenciado.
- Incidencias relacionadas con hardware fuera de garantía que el cliente decida no reemplazar.
- Casos que requieran adquisición de hardware o licencias que dependan de la aprobación y compra por parte del cliente.
- Períodos de mantenimiento programado previamente notificados.

## Métricas y reportes

KnowLigo genera reportes mensuales de cumplimiento de SLA que incluyen:

- Cantidad total de tickets abiertos y cerrados en el período
- Porcentaje de tickets resueltos dentro del SLA
- Tiempo promedio de respuesta por prioridad
- Tiempo promedio de resolución por prioridad
- Distribución de tickets por categoría (software, hardware, red, seguridad)
- Índice de satisfacción del cliente (basado en encuestas post-resolución)
- Tendencias y comparativa con meses anteriores

Estos reportes se entregan al ejecutivo de cuenta del cliente en la reunión de seguimiento mensual (Plan Profesional) o quincenal (Plan Empresarial). Los clientes del Plan Básico pueden solicitar un resumen trimestral sin costo adicional.
