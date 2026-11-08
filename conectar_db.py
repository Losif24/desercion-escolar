# conectar_db.py
import os
import sys
from datetime import datetime
from pathlib import Path
import psycopg2

# Buscar el .env en la misma carpeta
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Leer el .env manualmente, ignorando la terminal
def leer_env():
    config = {}
    if ENV_FILE.exists():
        with ENV_FILE.open("r", encoding="utf-8-sig") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    k, v = linea.split("=", 1)
                    config[k.strip()] = v.strip()
    return config

def main():
    print("=" * 60)
    print(f"Prueba de conexión (Python {sys.version_info[0]}.{sys.version_info[1]})")

    config = leer_env()
    
    host = config.get("DB_HOST")
    puerto = config.get("DB_PORT")
    usuario = config.get("DB_USER")
    password = config.get("DB_PASSWORD", "")
    base = config.get("DB_NAME")

    if not host:
        print(" ERROR DE CONFIGURACIÓN: Falta DB_HOST en el archivo .env")
        print(" Resultado: CONEXIÓN FALLIDA")
        print("=" * 60)
        return

    try:
        conexion = psycopg2.connect(
            host=host,
            port=int(puerto),
            user=usuario,
            password=password,
            dbname=base,
            sslmode=config.get("DB_SSLMODE", "prefer")
        )

        with conexion.cursor() as cur:
            cur.execute("SHOW server_version")
            version = cur.fetchone()[0]
            cur.execute("SELECT current_database()")
            base_actual = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
            tablas = cur.fetchone()[0]
        conexion.close()

        print(f"  Host     : {host}:{puerto}")
        print(f"  Motor    : PostgreSQL {version}")
        print(f"  Base     : {base_actual} ({tablas} tablas)")
        print("  Resultado: Conexión establecida")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  Resultado: CONEXIÓN FALLIDA")
        
    print("=" * 60)

if __name__ == "__main__":
    main()