"""Smoke test de secretos: comprueba que las claves de LangFuse llegan por el entorno y son validas.

Lo ejecuta la CI con las claves inyectadas desde GitHub Secrets, y tu en local con tu .env.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402,F401  (carga el .env)

LANGFUSE = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")
faltan = [n for n in LANGFUSE if not os.environ.get(n)]


def enmascarar(valor: str) -> str:
    return valor[:6] + "****"  # jamas se imprime una clave entera


if faltan:
    print(f"Faltan variables de entorno: {', '.join(faltan)}. Revisa tu .env o los Secrets del repositorio.")
    sys.exit(1)

from langfuse import get_client  # noqa: E402

print(f"LANGFUSE_HOST       = {os.environ['LANGFUSE_HOST']}")
print(f"LANGFUSE_PUBLIC_KEY = {enmascarar(os.environ['LANGFUSE_PUBLIC_KEY'])}")
print(f"LANGFUSE_SECRET_KEY = {enmascarar(os.environ['LANGFUSE_SECRET_KEY'])}")
if get_client().auth_check():
    print("OK: LangFuse acepta las credenciales")
else:
    print("ERROR: LangFuse rechaza las credenciales")
    sys.exit(1)
