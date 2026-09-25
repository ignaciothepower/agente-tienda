"""Las herramientas del agente viven en el servidor MCP de la S10-S12 (mcp-server-ci), no aqui.

El agente es un CLIENTE MCP por HTTP: le da igual que el servidor este en tu portatil (localhost)
o en una EC2 de AWS. Solo cambia la variable MCP_URL.
"""

import asyncio
import time

from config import MCP_URL


async def _llamar(nombre: str, args: dict) -> str:
    from mcp.client import Client  # mcp 2.x (S10): una URL en vez de un comando = Streamable HTTP

    async with Client(MCP_URL.rstrip("/") + "/mcp") as mcp:
        res = await mcp.call_tool(nombre, args)
        return " ".join(c.text for c in res.content if getattr(c, "text", None))


def llamar_tool(nombre: str, args: dict) -> tuple[str, int]:
    """tools/call sincrono (el grafo es sincrono). Devuelve (resultado en texto, milisegundos)."""
    t0 = time.perf_counter()
    texto = asyncio.run(_llamar(nombre, args))
    return texto, round((time.perf_counter() - t0) * 1000)
