"""Configuracion: TODO sale del entorno (.env en local, Secrets en GitHub). Ninguna clave en el codigo (S11)."""

import os

from dotenv import load_dotenv

load_dotenv()  # si no hay .env (por ejemplo en la CI) no pasa nada: se usan las variables ya definidas

MODELO = os.environ.get("MODELO", "llama3.1")  # el mismo LLM local de todo el master (Ollama)
MCP_URL = os.environ.get("MCP_URL", "http://localhost:8000")  # el servidor MCP de la S10-S12 (local o en AWS)
DATABASE_URL = os.environ.get("DATABASE_URL", "")  # Neon (S4): memoria del agente + PGVector
TABLA_RAG = "tienda_fragmentos"  # tabla propia, para no pisar la de la S5 (fragmentos)

NECESARIAS = ("DATABASE_URL", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")


def faltan() -> list[str]:
    """Nombres de las variables que faltan (nunca sus valores)."""
    return [n for n in NECESARIAS if not os.environ.get(n)]


def langfuse_activo() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))
