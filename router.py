"""El ROUTER: decide el camino de cada mensaje con reglas en codigo, sin gastar una llamada al LLM.

Por que no dejamos que llama3.1 elija las tools: en la S10 vimos que un modelo de 8B no encadena
herramientas (llamo a dos a la vez y relleno importe_eur="importe en euros"). Asi que aplicamos la
leccion de la S9: el LLM propone, el codigo dispone. Aqui el codigo decide y el LLM solo redacta.
"""

import re
from typing import Literal

Ruta = Literal["pedido", "precio", "rag", "charla"]

MONEDAS = {
    "dolar": "USD", "dolares": "USD", "usd": "USD", "libra": "GBP", "libras": "GBP", "gbp": "GBP",
    "yen": "JPY", "yenes": "JPY", "franco": "CHF", "francos": "CHF", "peso": "MXN", "pesos": "MXN",
    "real": "BRL", "reales": "BRL",
}  # fmt: skip
TEMAS_DOCS = ("envio", "enviar", "llega", "tarda", "gastos", "talla", "devol", "devuelv", "garantia", "reembolso",
              "cambiar", "cambio", "roto", "defecto", "seguimiento", "canarias", "baleares", "urgente")  # fmt: skip


def normalizar(texto: str) -> str:
    """minusculas y sin tildes: 'Envío' y 'envio' tienen que ser la misma palabra para las reglas."""
    return texto.lower().translate(str.maketrans("áéíóúü", "aeiouu"))


def numero_pedido(texto: str) -> str | None:
    m = re.search(r"\b(\d{4})\b", texto)
    return m.group(1) if m else None


def moneda(texto: str) -> str | None:
    for palabra in re.findall(r"[a-z]+", normalizar(texto)):
        if palabra in MONEDAS:
            return MONEDAS[palabra]
    return None


def importe(texto: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur|euros)", normalizar(texto))
    return float(m.group(1).replace(",", ".")) if m else None


def decidir(texto: str) -> Ruta:
    """Orden de las reglas: moneda > numero de pedido > tema de los documentos > charla."""
    t = normalizar(texto)
    if moneda(t):
        return "precio"
    if numero_pedido(t) and ("pedido" in t or "llega" in t or "estado" in t or "#" in t):
        return "pedido"
    if any(p in t for p in TEMAS_DOCS):
        return "rag"
    return "charla"
