"""El grafo completo con piezas falsas: un LLM de mentira, memoria en RAM y tools/RAG simulados.

Asi la CI comprueba el CABLEADO (router -> nodo -> responder, y la memoria entre turnos) sin Ollama,
sin Neon y sin AWS. Lo caro se prueba a mano; lo que se rompe al tocar el codigo, en cada push.
"""

import json

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import InMemorySaver

import agente

PEDIDO = {"estado": "enviado", "transportista": "SEUR", "llegada": "jueves", "importe_eur": 49.90}


def falsa_tool(monkeypatch, llamadas):
    def tool(nombre, args):
        llamadas.append((nombre, args))
        if nombre == "consultar_pedido":
            return json.dumps(PEDIDO)
        return f"{args['importe_eur']:.2f} EUR = 57.00 USD"

    monkeypatch.setattr(agente, "_tool", tool)


def test_memoria_entre_turnos_y_tool_encadenada(monkeypatch):
    llamadas = []
    falsa_tool(monkeypatch, llamadas)
    monkeypatch.setattr(agente.config, "langfuse_activo", lambda: False)
    grafo = agente.construir(llm=FakeListChatModel(responses=["Llega el jueves", "Son 57 USD"]),
                             checkpointer=InMemorySaver())  # fmt: skip

    assert agente.turno(grafo, "t1", "¿Cuándo llega mi pedido 1234?") == "Llega el jueves"
    assert agente.turno(grafo, "t1", "¿Y eso cuánto es en dólares?") == "Son 57 USD"

    # el segundo turno NO dice el importe: sale de ultimo_pedido, que guardo el checkpointer
    assert llamadas == [
        ("consultar_pedido", {"numero": "1234"}),
        ("convertir_precio", {"importe_eur": 49.9, "moneda": "USD"}),
    ]
    estado = grafo.get_state({"configurable": {"thread_id": "t1"}}).values
    assert len(estado["messages"]) == 4  # 2 del cliente + 2 del agente


def test_hilos_separados(monkeypatch):
    monkeypatch.setattr(agente.config, "langfuse_activo", lambda: False)
    grafo = agente.construir(llm=FakeListChatModel(responses=["hola", "hola"]), checkpointer=InMemorySaver())
    agente.turno(grafo, "ana", "Hola, soy Ana")
    agente.turno(grafo, "luis", "Hola, soy Luis")
    ana = grafo.get_state({"configurable": {"thread_id": "ana"}}).values["messages"]
    assert [m.content for m in ana] == ["Hola, soy Ana", "hola"]  # Luis no aparece en la memoria de Ana


def test_rag_filtra_por_umbral(monkeypatch):
    import rag

    frags = [{"documento": "envios.txt", "texto": "gratis > 50 EUR", "distancia": 0.3},
             {"documento": "tallas.txt", "texto": "S = 88-94", "distancia": 0.9}]  # fmt: skip
    monkeypatch.setattr(rag, "recuperar", lambda pregunta: frags)
    monkeypatch.setattr(agente.config, "langfuse_activo", lambda: False)
    salida = agente.nodo_rag({"messages": [agente.HumanMessage("envio gratis?")]})
    assert "envios.txt" in salida["datos"] and "tallas.txt" not in salida["datos"]
