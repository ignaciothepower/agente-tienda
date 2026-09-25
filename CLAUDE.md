# agente-tienda · contexto para Claude Code

Proyecto final del Master AI Engineer (Sesion 13): el asistente de una tienda online ficticia.

## Arquitectura (cada pieza es una sesion)
- `agente.py`: grafo LangGraph (S2). router -> pedido | precio | rag | charla -> responder.
- `router.py`: decide la ruta con REGLAS, sin LLM (S9: "el LLM propone, el codigo dispone").
- `rag.py`: PGVector en Neon (S4-S5), modelo paraphrase-multilingual-MiniLM-L12-v2, tabla tienda_fragmentos.
- `herramientas.py`: cliente MCP por HTTP al servidor de la S10-S12 (repo mcp-server-ci), en MCP_URL.
- Memoria: PostgresSaver de LangGraph en Neon (S4). Trazas: LangFuse Cloud (S3, S11).
- LLM: llama3.1 local con Ollama (num_predict 200).

## Convenciones
- Todo en espanol: codigo, comentarios, mensajes y commits.
- Ninguna clave en el codigo: todo por `.env` (plantilla `.env.example`) o GitHub Secrets. Nunca subir `.env`.
- Antes de cada commit: `ruff check . && ruff format --check . && pytest`.
- Los tests NO usan Ollama, Neon ni la red: LLM falso (FakeListChatModel) y memoria en RAM (InMemorySaver).
- Imports pesados (torch, psycopg, mcp) dentro de las funciones, para que la CI no los necesite.
