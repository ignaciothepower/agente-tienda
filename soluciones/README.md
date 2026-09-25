# Soluciones · Sesión 13

## Ejercicio 1 · Básico: tu agente conversacional

La solución de referencia es **este mismo repositorio**. Para adaptarlo a tu dominio:

1. Sustituye los ficheros de `docs/` por tus documentos (una idea por línea, con un título en la primera línea).
2. `python rag.py --indexar` y mide distancias con `python rag.py "tu pregunta"` (de tu dominio y ajenas) para fijar `UMBRAL` en `agente.py`.
3. Cambia `TEMAS_DOCS`, `MONEDAS` y las reglas de `router.decidir()` por las de tus usuarios, **y sus tests** en `tests/test_router.py`.
4. Cambia `SYSTEM` en `agente.py`. Si tu dominio necesita otra herramienta, añádela al servidor MCP (repo `mcp-server-ci`) y crea su nodo.
5. Tres mensajes en procesos distintos con el mismo `--hilo`, `--historial`, y abre las trazas en LangFuse.
6. `ruff check . && ruff format --check . && pytest`, push, y CI en verde.

**Así debe verse**: las salidas reales de la clase están en `salidas/` (`03`-`07` = la conversación de Ana, `09`-`10` = Luis con las tools en AWS).

## Ejercicio 2 · Reto: tu pieza estrella del portfolio

Pistas (esta parte **no se ejecutó en clase**):

- **Todo en la nube (opción B)**: en `construir()` cambia `ChatOllama` por `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` de `langchain-google-genai`, con `GOOGLE_API_KEY` en `.env` y en GitHub Secrets. El grafo, la memoria, el RAG y las tools no cambian. Despliega el agente con su Dockerfile en Render, Railway o una EC2.
- **Validar la respuesta**: añade un nodo `validar` entre `responder` y `END` que pregunte al LLM si la respuesta usa solo `DATOS` (sí/no) y, si no, responda con una frase segura (como el CRAG de la S6).
- **Evaluación**: crea en LangFuse un dataset con 5 preguntas y su respuesta esperada y lanza un experimento (S3).
- **Router mixto**: si ninguna regla encaja, pide al LLM una etiqueta de la lista cerrada `pedido | precio | rag | charla` con salida estructurada y valida el resultado en código.
