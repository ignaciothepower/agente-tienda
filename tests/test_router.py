"""El router es codigo puro: se prueba sin LLM, sin base de datos y sin red (milisegundos)."""

import pytest

import router


@pytest.mark.parametrize(
    ("mensaje", "ruta"),
    [
        ("¿Cuándo llega mi pedido 1234?", "pedido"),
        ("¿Cuánto es eso en dólares?", "precio"),
        ("Convierte 20 euros a libras", "precio"),
        ("¿Cuánto cuesta el envío a Canarias?", "rag"),
        ("Soy una L, ¿qué talla de camiseta me pido?", "rag"),
        ("Hola, me llamo Ana", "charla"),
    ],
)
def test_decidir(mensaje, ruta):
    assert router.decidir(mensaje) == ruta


def test_extraer_datos():
    assert router.numero_pedido("el pedido #5678 no llega") == "5678"
    assert router.moneda("¿y en Yenes?") == "JPY"
    assert router.importe("son 49,90 € al final") == 49.90
    assert router.importe("sin importe") is None
