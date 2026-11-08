# config.py
import os
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

def cargar_env():
    """Lee el archivo .env manualmente sin dependencias externas."""
    config = {}
    if ENV_FILE.exists():
        with ENV_FILE.open("r", encoding="utf-8-sig") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    k, v = linea.split("=", 1)
                    config[k.strip()] = v.strip()
    return config

# En Render no hay .env: las variables llegan del entorno del servidor
env = {**os.environ, **cargar_env()}

class Config:
    SECRET_KEY = env.get("SECRET_KEY", "default-inseguro")
    
    # La URI se construye AQUÍ, no en app.py
    # Sin secretos aquí: los datos reales van en .env (PC) o en Environment (Render)
    _user = env.get("DB_USER", "postgres")
    _pass = quote_plus(env.get("DB_PASSWORD", ""))
    _host = env.get("DB_HOST", "127.0.0.1")
    _port = env.get("DB_PORT", "5432")
    _name = env.get("DB_NAME", "desercion_escolar")

    # prefer: cifra si el servidor lo ofrece (Supabase, URL externa de Render) y no falla si no
    _ssl = env.get("DB_SSLMODE", "prefer")

    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{_user}:{_pass}@{_host}:{_port}/{_name}?sslmode={_ssl}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 10,
    }