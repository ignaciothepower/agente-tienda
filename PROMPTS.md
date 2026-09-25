# Sesión 13 · Proyecto final: tu agente conversacional · Prompts para Claude Code

Estos son los prompts que usamos en la práctica, en el mismo orden que en clase. Cópialos y pégalos en Claude Code uno a uno.

**Cómo usarlos**
1. Pega el prompt del paso y deja que Claude Code proponga los cambios.
2. **Lee el código antes de aceptar** (y los comandos, como `pip install`, antes de permitirlos).
3. Ejecuta y compara con el apartado *Qué deberías ver*.
4. Si no sale lo esperado, vuelve a pedírselo con lo que has aprendido.

> Antes de empezar: todo lo del curso. Ollama con `llama3.1` (S1), tu base de datos de Neon de la S4 (`DATABASE_URL`), tus claves de LangFuse Cloud de la S3, el servidor MCP de la S10-S12 (repo `mcp-server-ci`) y Git con tu cuenta de GitHub (S11). AWS es opcional (S12). Todo va en un `.env` (plantilla en `.env.example`; **nunca subas tu `.env`**). Repositorio de referencia, público: https://github.com/ignaciothepower/agente-tienda. **Si usas AWS, al terminar apaga todo** (`bash aws/apagar.sh`).

El resultado de referencia, con todo el código comentado, está en la carpeta `agente-tienda` del material de la sesión.

---

## Paso 1 · Scaffold del proyecto y el grafo base

**Qué construye**

- Repositorio + CLAUDE.md con las convenciones
- Estado con historial y datos
- router -> 4 caminos -> responder
- llama3.1 local: solo redacta

**Prompt**

```text
Crea el scaffold de un agente conversacional con LangGraph para una tienda online: un repositorio con un CLAUDE.md que explique el contexto y las convenciones (todo en espanol, claves en .env, tests sin LLM), y un grafo con un estado (historial de mensajes con add_messages, la ruta elegida y los datos para el LLM), un nodo router y un nodo responder que usa llama3.1 con Ollama (temperature 0, num_predict 200). Explica estado, nodos y aristas recordando la Sesion 2 y deja algo que ya responda por consola con python agente.py "mensaje".
```

**Qué deberías ver**

Una arista condicional desde el router a cuatro nodos, y todos acaban en 'responder'. El checkpointer entra al compilar.

---

## Paso 2 · Memoria persistente con PostgreSQL

**Qué construye**

- PostgresSaver de LangGraph
- La misma base de Neon de la S4
- thread_id = el cliente
- Proceso nuevo en cada mensaje

**Prompt**

```text
Anade memoria persistente al agente con el checkpointer de LangGraph sobre PostgreSQL (Sesion 4). Usa la base de datos de Neon de la S4 (DATABASE_URL en el .env) en lugar de Docker, con PostgresSaver.from_conn_string y setup(). Cada cliente es un thread_id que paso con --hilo. Anade una opcion --historial que muestre lo que el agente recuerda. Comprueba que si lanzo cuatro mensajes en cuatro procesos distintos, el agente recuerda lo que hablamos. Explica que es un thread y como se recupera una conversacion previa.
```

**Qué deberías ver**

El cuarto proceso no sabe nada, pero responde 'te llamas Ana'. Y --historial lee de Neon toda la conversacion.

---

## Paso 3 · RAG sobre tus documentos (PGVector)

**Qué construye**

- docs/: envios, tallas, garantia, devoluciones
- Embeddings multilingues de la S4
- Tabla tienda_fragmentos en Neon
- Nodo rag antes de responder

**Prompt**

```text
Anade RAG al agente: usa PGVector (Sesion 4 y 5) en la misma base de Neon para indexar los documentos de docs/ con paraphrase-multilingual-MiniLM-L12-v2 en una tabla propia, y crea un nodo en el grafo que, antes de responder, recupere los 4 fragmentos mas cercanos y pase al LLM solo los que esten por debajo de un umbral de distancia. Ensename las distancias de varias preguntas (de la tienda y ajenas) para elegir el umbral, y prueba una pregunta que solo se pueda responder con esos documentos. Comenta como enlaza con la Sesion 5.
```

**Qué deberías ver**

Cuatro fragmentos, todos por debajo de 0,72, y el primero (0,382) es justo el de Canarias. La respuesta cita [envios.txt].

---

## Paso 4 · Herramientas via un MCP propio

**Qué construye**

- Reutilizamos el servidor de la S10-S12
- Cliente MCP por Streamable HTTP
- consultar_pedido y convertir_precio
- MCP_URL: local o AWS

**Prompt**

```text
Conecta herramientas al agente mediante MCP (Sesion 10): reutiliza el servidor MCP de la tienda de la S10-S12 (consultar_pedido y convertir_precio) arrancado en modo HTTP, y crea un cliente MCP por Streamable HTTP cuya URL venga de MCP_URL en el .env. Haz que el grafo invoque consultar_pedido cuando el router detecte un numero de pedido, y convertir_precio cuando pida otra moneda, sacando el importe del mensaje o del ultimo pedido guardado en el estado. Muestra al agente usando las tools y recuerda la regla de los buenos docstrings.
```

**Qué deberías ver**

El segundo mensaje no dice ningun importe: el 49,90 sale de ultimo_pedido, guardado en Neon en el turno anterior.

---

## Paso 5 · Observabilidad con LangFuse

**Qué construye**

- Una traza por mensaje del cliente
- Cada nodo del grafo, dentro
- pgvector y las tools, como observaciones
- session_id = el hilo

**Prompt**

```text
Instrumenta el agente completo con LangFuse (Sesion 3): que cada mensaje genere una traza con todos los nodos del grafo (router, RAG, herramientas y respuesta) usando el CallbackHandler de LangChain, que la busqueda en PGVector y cada tool MCP aparezcan como observaciones propias, y que la sesion sea el hilo del cliente. Haz la traza publica para ensenarla en clase. Abre el dashboard y ensename la traza de una conversacion de punta a punta con su latencia, tokens y coste. Comenta por que esto es imprescindible antes de desplegar.
```

**Qué deberías ver**

La traza del mensaje de Canarias: 46 s en total, 450 tokens, sesion y usuario 'ana' y las etiquetas s13 y llama3.1.

---

## Paso 6 · Tests, secretos y CI

**Qué construye**

- ruff check + ruff format
- 10 tests con un LLM falso
- Claves en .env y en GitHub Secrets
- Dos jobs: calidad y secretos

**Prompt**

```text
Prepara el proyecto para produccion (Sesion 11): anade tests con pytest que no usen Ollama, Neon ni la red (un LLM falso con FakeListChatModel, InMemorySaver y las tools simuladas) para el router, la memoria entre turnos y los hilos separados. Mueve todas las claves a un .env con .gitignore y una plantilla .env.example, y crea el workflow de CI en GitHub Actions con un job que pase ruff y pytest y otro que compruebe las claves de LangFuse desde GitHub Secrets. Comprueba que el check sale en verde.
```

**Qué deberías ver**

Run #1, segundo intento: calidad y secretos en verde. El primer intento fallo a proposito... bueno, casi.

---

## Paso 7 · Desplegar y cierre del master

**Qué construye**

- CloudShell: sin claves en el portatil
- EC2 t3.micro + Docker (S12)
- MCP_URL = la IP de la EC2
- apagar.sh: todo a cero

**Prompt**

```text
Despliega la parte del agente que cabe en la capa gratuita (Sesion 12): el servidor MCP de la tienda en una EC2 t3.micro con Docker, lanzado desde AWS CloudShell con un script (security group solo con mi IP, par de claves, IMDSv2) y otro script para apagarlo todo y comprobar que queda a cero. Conecta el agente de mi portatil a esa URL y comprueba que funciona de punta a punta en la nube. Explicame por que el LLM no cabe en una t3.micro y que haria falta para tenerlo todo en la nube. Recuerdame apagar los recursos.
```

**Qué deberías ver**

2 min 21 s de un comando a un servidor MCP respondiendo en AWS. La IP de tu portatil, la unica que puede entrar al 8000.

---

## Ejercicio 1 · Basico: tu agente conversacional

**Qué construye**

- Grafo + memoria + RAG + MCP + LangFuse
- Tests + CI en verde
- Desplegado
- README de portfolio

**Prompt**

```text
Quiero adaptar el proyecto agente-tienda a mi propio dominio: [describe tu dominio]. Cambia los documentos de docs/ por los mios, adapta las reglas del router (y sus tests) a las preguntas de mis usuarios, el SYSTEM del agente y, si tiene sentido, una tool MCP propia. Reindexa en PGVector, mide las distancias para elegir el umbral y ensename una conversacion de 3 mensajes en procesos distintos que demuestre memoria, RAG y tool, con su traza en LangFuse. Termina con la CI en verde y el README actualizado.
```

**Qué deberías ver**

Una conversacion como la de Ana, pero en tu dominio, con sus trazas y la CI en verde.

---

## Ejercicio 2 · Reto: tu pieza estrella del portfolio

**Qué construye**

- Todo en la nube
- Validacion de respuestas
- Dataset de evaluacion
- README de portfolio

**Prompt**

```text
Lleva mi agente conversacional a nivel de portfolio: 1) opcion B, cambia el LLM local por una API gratuita (por ejemplo Gemini free tier) con la clave en GitHub Secrets y despliega el agente completo (Render, Railway o AWS) para que sea accesible; 2) anade un nodo que compruebe que la respuesta solo usa los datos recuperados (como el CRAG de la Sesion 6); 3) crea en LangFuse un dataset de 5 preguntas con su respuesta esperada y evaluame el agente; 4) escribe un README de portfolio con arquitectura, decisiones, costes y como apagarlo.
```

**Qué deberías ver**

La URL o un video de la demo, el experimento en LangFuse y un README que otro pueda seguir.

---

*Material del Master AI Engineer · The Power · Ignacio de Pastors*
