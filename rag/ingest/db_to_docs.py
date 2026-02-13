"""
Script para generar documentos Markdown a partir de datos públicos de la base de datos.
Solo expone información agregada y de planes/servicios. NUNCA expone datos de clientes
(nombres, emails, teléfonos, nombres de contacto).
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def generate_db_docs(db_path: str = None, output_dir: str = None):
    """Genera archivos .md con datos públicos de la DB para vectorización."""

    project_root = Path(__file__).resolve().parent.parent.parent
    if db_path is None:
        db_path = project_root / "database" / "sqlite" / "knowligo.db"
    else:
        db_path = Path(db_path)

    if output_dir is None:
        output_dir = project_root / "knowledge" / "documents" / "db_generated"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        print(f"❌ Base de datos no encontrada en {db_path}")
        print("   Ejecute primero: python scripts/utils/init_db.py")
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    generated_files = []

    # --- 1. Documento de planes desde la DB ---
    try:
        cursor.execute("SELECT * FROM plans ORDER BY price_ars ASC")
        plans = cursor.fetchall()

        if plans:
            content = _generate_plans_doc(plans)
            path = output_dir / "db_planes.md"
            path.write_text(content, encoding="utf-8")
            generated_files.append(str(path))
            print(f"✅ Generado: {path.name} ({len(plans)} planes)")
    except Exception as e:
        print(f"⚠️  Error generando planes: {e}")

    # --- 2. Documento de estadísticas operativas (agregadas, sin datos de clientes) ---
    try:
        content = _generate_stats_doc(cursor)
        path = output_dir / "db_estadisticas.md"
        path.write_text(content, encoding="utf-8")
        generated_files.append(str(path))
        print(f"✅ Generado: {path.name}")
    except Exception as e:
        print(f"⚠️  Error generando estadísticas: {e}")

    # --- 3. Documento de distribución de tickets (categorías, prioridades) ---
    try:
        content = _generate_ticket_summary_doc(cursor)
        path = output_dir / "db_tickets_resumen.md"
        path.write_text(content, encoding="utf-8")
        generated_files.append(str(path))
        print(f"✅ Generado: {path.name}")
    except Exception as e:
        print(f"⚠️  Error generando resumen de tickets: {e}")

    conn.close()
    print(f"\n📄 Total documentos generados: {len(generated_files)}")
    return generated_files


def _generate_plans_doc(plans) -> str:
    """Genera documento Markdown con los planes desde la DB."""
    lines = [
        "# Planes de Servicio KnowLigo (Datos del Sistema)",
        "",
        "Información actualizada de los planes de soporte disponibles.",
        "",
    ]

    for plan in plans:
        name = plan["name"]
        desc = plan["description"]
        price = plan["price_ars"]
        max_tickets = plan["max_tickets_month"]
        hours = plan["support_hours"]
        onsite = "Sí" if plan["includes_onsite"] else "No"
        backup = "Sí" if plan["includes_backup"] else "No"
        drp = "Sí" if plan["includes_drp"] else "No"
        maint = plan["maintenance_frequency"] or "No incluido"

        tickets_text = str(max_tickets) if max_tickets else "Ilimitados"
        price_text = f"${price:,.0f} ARS/mes".replace(",", ".")

        lines.extend(
            [
                f"## Plan {name}",
                "",
                f"**Precio**: {price_text}",
                f"**Descripción**: {desc}",
                f"**Tickets mensuales**: {tickets_text}",
                f"**Horario de soporte**: {hours}",
                f"**Soporte presencial**: {onsite}",
                f"**Backup gestionado**: {backup}",
                f"**Plan de recuperación ante desastres (DRP)**: {drp}",
                f"**Mantenimiento preventivo**: {maint}",
                "",
            ]
        )

    return "\n".join(lines)


def _generate_stats_doc(cursor) -> str:
    """Genera estadísticas agregadas sin exponer datos de clientes."""
    lines = [
        "# Estadísticas Operativas de KnowLigo",
        "",
        f"Datos actualizados al {datetime.now().strftime('%d/%m/%Y')}.",
        "",
    ]

    # Total de clientes activos (sin nombres)
    cursor.execute("""
        SELECT COUNT(DISTINCT c.id) 
        FROM clients c 
        JOIN contracts ct ON c.id = ct.client_id 
        WHERE ct.status = 'Activo'
    """)
    active_clients = cursor.fetchone()[0]

    # Distribución por plan
    cursor.execute("""
        SELECT p.name, COUNT(*) as qty
        FROM contracts ct
        JOIN plans p ON ct.plan_id = p.id
        WHERE ct.status = 'Activo'
        GROUP BY p.name
        ORDER BY p.price_ars ASC
    """)
    plan_dist = cursor.fetchall()

    # Distribución por industria
    cursor.execute("""
        SELECT c.industry, COUNT(*) as qty
        FROM clients c
        JOIN contracts ct ON c.id = ct.client_id
        WHERE ct.status = 'Activo' AND c.industry IS NOT NULL
        GROUP BY c.industry
        ORDER BY qty DESC
    """)
    industry_dist = cursor.fetchall()

    lines.extend(
        [
            "## Clientes",
            "",
            f"KnowLigo cuenta actualmente con **{active_clients} empresas clientes** con contratos activos.",
            "",
        ]
    )

    if plan_dist:
        lines.extend(["### Distribución por Plan", ""])
        for row in plan_dist:
            lines.append(f"- **Plan {row['name']}**: {row['qty']} clientes")
        lines.append("")

    if industry_dist:
        lines.extend(["### Industrias Atendidas", ""])
        for row in industry_dist:
            lines.append(f"- {row['industry']}: {row['qty']} empresas")
        lines.append("")

    # Estadísticas de tickets
    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tickets WHERE status IN ('Resuelto', 'Cerrado')"
    )
    resolved = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tickets WHERE status IN ('Abierto', 'En progreso', 'Esperando cliente')"
    )
    open_tickets = cursor.fetchone()[0]

    resolution_rate = (resolved / total_tickets * 100) if total_tickets > 0 else 0

    lines.extend(
        [
            "## Tickets de Soporte",
            "",
            f"- **Total de tickets gestionados**: {total_tickets}",
            f"- **Tickets resueltos/cerrados**: {resolved}",
            f"- **Tickets abiertos actualmente**: {open_tickets}",
            f"- **Tasa de resolución**: {resolution_rate:.0f}%",
            "",
        ]
    )

    return "\n".join(lines)


def _generate_ticket_summary_doc(cursor) -> str:
    """Genera resumen de tipos de ticket sin datos de clientes."""
    lines = [
        "# Resumen de Tickets de Soporte",
        "",
        "Distribución de incidencias por categoría y prioridad.",
        "",
    ]

    # Por categoría
    cursor.execute("""
        SELECT category, COUNT(*) as qty
        FROM tickets
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY qty DESC
    """)
    cat_dist = cursor.fetchall()

    if cat_dist:
        lines.extend(["## Por Categoría", ""])
        for row in cat_dist:
            lines.append(f"- **{row['category']}**: {row['qty']} tickets")
        lines.append("")

    # Por prioridad
    cursor.execute("""
        SELECT priority, COUNT(*) as qty
        FROM tickets
        GROUP BY priority
        ORDER BY 
            CASE priority 
                WHEN 'Crítica' THEN 1 
                WHEN 'Alta' THEN 2 
                WHEN 'Media' THEN 3 
                WHEN 'Baja' THEN 4 
            END
    """)
    pri_dist = cursor.fetchall()

    if pri_dist:
        lines.extend(["## Por Prioridad", ""])
        for row in pri_dist:
            lines.append(f"- **{row['priority']}**: {row['qty']} tickets")
        lines.append("")

    # Por estado
    cursor.execute("""
        SELECT status, COUNT(*) as qty
        FROM tickets
        GROUP BY status
        ORDER BY qty DESC
    """)
    status_dist = cursor.fetchall()

    if status_dist:
        lines.extend(["## Por Estado", ""])
        for row in status_dist:
            lines.append(f"- **{row['status']}**: {row['qty']} tickets")
        lines.append("")

    # Tipos de incidencia más comunes (sin datos de clientes)
    cursor.execute("""
        SELECT category, subject
        FROM tickets
        WHERE status IN ('Resuelto', 'Cerrado') AND resolution IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 5
    """)
    recent = cursor.fetchall()

    if recent:
        lines.extend(
            [
                "## Tipos de Incidencia Más Frecuentes",
                "",
                "Ejemplos de incidencias resueltas recientemente:",
                "",
            ]
        )
        for row in recent:
            lines.append(f"- [{row['category']}] {row['subject']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    generated = generate_db_docs()
    if generated:
        print(f"\nArchivos generados en knowledge/documents/db_generated/:")
        for f in generated:
            print(f"  - {f}")
