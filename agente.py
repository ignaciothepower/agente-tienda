"""El agente de la tienda: el proyecto final del master. Cada pieza es una sesion del curso.

    router (reglas, S9) -> pedido | precio  (tools MCP en AWS, S10-S12)
                        -> rag              (PGVector en Neon, S4-S5)
                        -> charla
                        -> responder        (llama3.1 con Ollama, S1-S2)
    memoria: checkpointer de LangGraph en Postgres (Neon, S4) · trazas: LangFuse (S3, S11)

Uso:
    python agente.py --hilo ana "Hola, soy Ana"      un mensaje (cada ejecucion es un proceso nuevo)
    python agente.py --hilo ana                       modo chat por consola
    python agente.py --hilo ana --historial           ver lo que el agente recuerda de ese hilo
"""

import argparse
import json
import time
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

import config
import router

SYSTEM = (
    "Eres el asistente de una tienda online. Responde en espanol, en 1-3 frases, con tono cercano.\n"
    "Si hay DATOS, usa SOLO esos datos (no inventes precios ni plazos) y termina citando la fuente entre "
    "corchetes, por ejemplo [envios.txt] o [tool consultar_pedido]. Si no hay datos y te preguntan algo de la "
    "tienda, di que no lo sabes y ofrece hablar con una persona."
)
UMBRAL = 0.72  # distancia coseno maxima: medida en salidas/02_indexar_y_distancias.txt (lo ajeno sale > 0.75)
VENTANA = 8  # mensajes del historial que ve el LLM: la memoria guarda todo, el prompt solo lo reciente


class Estado(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # historial (el reducer add_messages ANADE, S2)
    ruta: str
    datos: str  # contexto para el LLM: fragmentos del RAG o resultado de una tool
    ultimo_pedido: dict  # sobrevive entre turnos gracias al checkpointer: "¿y eso en dolares?"


def _ultimo(estado: Estado) -> str:
    return estado["messages"][-1].content


def _observar(nombre: str, tipo: str, entrada, funcion):
    """Envuelve un paso en una observacion de LangFuse (si hay claves); si no, lo ejecuta sin mas."""
    if not config.langfuse_activo():
        return funcion()
    from langfuse import get_client

    with get_client().start_as_current_observation(as_type=tipo, name=nombre, input=entrada) as obs:
        salida = funcion()
        obs.update(output=salida)
        return salida


# ---------------- nodos ----------------
def nodo_router(estado: Estado) -> dict:
    ruta = router.decidir(_ultimo(estado))
    print(f"  [router] -> {ruta}")
    return {"ruta": ruta, "datos": ""}


def nodo_rag(estado: Estado) -> dict:
    import rag

    frags = _observar("pgvector", "retriever", _ultimo(estado), lambda: rag.recuperar(_ultimo(estado)))
    buenos = [f for f in frags if f["distancia"] <= UMBRAL]
    for f in frags:
        print(f"  [rag] {f['distancia']:.3f} {'OK ' if f in buenos else 'no '}[{f['documento']}] {f['texto'][:70]}")
    return {"datos": "\n".join(f"[{f['documento']}] {f['texto']}" for f in buenos)}


def _tool(nombre: str, args: dict) -> str:
    import herramientas

    texto, ms = _observar(nombre, "tool", args, lambda: herramientas.llamar_tool(nombre, args))
    print(f"  [mcp] {nombre}({json.dumps(args, ensure_ascii=False)}) -> {texto}  [{ms} ms, {config.MCP_URL}]")
    return texto


def nodo_pedido(estado: Estado) -> dict:
    numero = router.numero_pedido(_ultimo(estado))  # el numero lo saca una regex, no el LLM
    texto = _tool("consultar_pedido", {"numero": numero})
    try:
        pedido = {"numero": numero, **json.loads(texto)}
    except json.JSONDecodeError:
        pedido = {"numero": numero, "error": texto}
    return {"datos": f"[tool consultar_pedido] {texto}", "ultimo_pedido": pedido}


def nodo_precio(estado: Estado) -> dict:
    texto = _ultimo(estado)
    euros = router.importe(texto) or (estado.get("ultimo_pedido") or {}).get("importe_eur")  # <- memoria
    if not euros:
        return {"datos": "Falta el importe en euros: pidele al cliente la cantidad o el numero de pedido."}
    resultado = _tool("convertir_precio", {"importe_eur": float(euros), "moneda": router.moneda(texto)})
    return {"datos": f"[tool convertir_precio] {resultado}"}


def nodo_responder(estado: Estado, llm) -> dict:
    datos = estado.get("datos") or "(sin datos)"
    mensajes = [SystemMessage(f"{SYSTEM}\n\nDATOS:\n{datos}"), *estado["messages"][-VENTANA:]]
    t0 = time.time()
    respuesta = llm.invoke(mensajes)
    print(f"  [llm] {config.MODELO} {time.time() - t0:.0f} s")
    return {"messages": [AIMessage(respuesta.content)]}


# ---------------- grafo ----------------
def construir(llm=None, checkpointer=None):
    """El grafo completo. En los tests se le pasa un LLM falso y memoria en RAM."""
    if llm is None:
        from langchain_ollama import ChatOllama

        llm = ChatOllama(model=config.MODELO, temperature=0, num_predict=200)
    g = StateGraph(Estado)
    g.add_node("router", nodo_router)
    g.add_node("rag", nodo_rag)
    g.add_node("pedido", nodo_pedido)
    g.add_node("precio", nodo_precio)
    g.add_node("responder", lambda e: nodo_responder(e, llm))
    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router", lambda e: e["ruta"], {"rag": "rag", "pedido": "pedido", "precio": "precio", "charla": "responder"}
    )
    for n in ("rag", "pedido", "precio"):
        g.add_edge(n, "responder")
    g.add_edge("responder", END)
    return g.compile(checkpointer=checkpointer)


def turno(grafo, hilo: str, mensaje: str) -> str:
    """Un mensaje del cliente = una invocacion del grafo = una traza en LangFuse."""
    cfg = {"configurable": {"thread_id": hilo}}  # el hilo es la "conversacion" que guarda el checkpointer
    if not config.langfuse_activo():
        return grafo.invoke({"messages": [HumanMessage(mensaje)]}, cfg)["messages"][-1].content
    from langfuse import get_client, propagate_attributes
    from langfuse.langchain import CallbackHandler

    lf = get_client()
    with lf.start_as_current_observation(as_type="span", name="agente-tienda", input=mensaje) as traza:
        with propagate_attributes(session_id=hilo, user_id=hilo, tags=["s13", config.MODELO]):
            cfg["callbacks"] = [CallbackHandler()]  # cada nodo del grafo y la llamada al LLM, dentro de la traza
            salida = grafo.invoke({"messages": [HumanMessage(mensaje)]}, cfg)["messages"][-1].content
        traza.update(output=salida)
        lf.set_current_trace_as_public()  # demo de clase: la traza se ve sin login
        print(f"  [langfuse] {lf.get_trace_url()}")
    lf.flush()
    return salida


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--hilo", default="demo")
    p.add_argument("--historial", action="store_true")
    p.add_argument("mensaje", nargs="*")
    a = p.parse_args()
    from langgraph.checkpoint.postgres import PostgresSaver

    # Memoria persistente: el estado de cada hilo se guarda en Postgres (Neon) despues de cada nodo
    with PostgresSaver.from_conn_string(config.DATABASE_URL) as memoria:
        memoria.setup()  # crea las tablas checkpoints* la primera vez (idempotente)
        grafo = construir(checkpointer=memoria)
        if a.historial:
            estado = grafo.get_state({"configurable": {"thread_id": a.hilo}}).values
            for m in estado.get("messages", []):
                print(f"{'Cliente' if m.type == 'human' else 'Agente '}: {m.content}")
            print(f"ultimo_pedido: {estado.get('ultimo_pedido')}")
            return
        mensajes = [" ".join(a.mensaje)] if a.mensaje else iter(lambda: input("Tu: "), "salir")
        for m in mensajes:
            print(f"Cliente [{a.hilo}]: {m}")
            print(f"Agente: {turno(grafo, a.hilo, m)}")


if __name__ == "__main__":
    main()
