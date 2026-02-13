"""
Script para inicializar la base de datos SQLite de KnowLigo.
Ejecuta el schema y los datos de seed.
"""

import sqlite3
import os
from pathlib import Path


def init_database():
    """Inicializa la base de datos con schema y seed data"""

    # Rutas - el script está en scripts/utils/, el proyecto está 2 niveles arriba
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    db_path = project_root / "database" / "sqlite" / "knowligo.db"
    schema_path = project_root / "database" / "schema" / "schema.sql"
    seed_path = project_root / "database" / "seeds" / "seed.sql"

    # Crear directorio si no existe
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Si la DB ya existe, preguntar antes de sobrescribir
    if db_path.exists():
        print(f"⚠️  La base de datos ya existe en {db_path}")
        response = input("¿Deseas recrearla? Esto borrará todos los datos (y/n): ")
        if response.lower() != "y":
            print("❌ Operación cancelada")
            return
        db_path.unlink()

    print(f"📦 Creando base de datos en {db_path}")

    # Conectar a la base de datos (la crea si no existe)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Ejecutar schema
        print("📋 Ejecutando schema.sql...")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            cursor.executescript(schema_sql)

        # Ejecutar seeds
        print("🌱 Insertando seed data...")
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_sql = f.read()
            cursor.executescript(seed_sql)

        # Commit cambios
        conn.commit()

        # Verificar tablas creadas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"\n✅ Base de datos inicializada correctamente")
        print(f"📊 Tablas creadas: {', '.join([t[0] for t in tables])}")

        # Mostrar conteo de registros
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} registros")

    except Exception as e:
        print(f"\n❌ Error al inicializar la base de datos: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()

    print(f"\n🎉 Inicialización completada. DB: {db_path}")


if __name__ == "__main__":
    init_database()
