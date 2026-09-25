"""RAG de la tienda (S4 + S5): indexar los documentos en PGVector y recuperar los fragmentos mas cercanos.

Es el mismo codigo de la S5 (ingesta.py + db.py + rag.py) con dos cambios: los documentos son los de la
tienda (carpeta docs/) y la tabla se llama tienda_fragmentos. Los imports pesados (torch) van dentro de
las funciones para que los tests y la CI no los necesiten.
"""

import os
from pathlib import Path

from config import DATABASE_URL, TABLA_RAG

os.environ.setdefault("HF_HUB_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

MODELO_EMB = "paraphrase-multilingual-MiniLM-L12-v2"  # multilingue, 384 dimensiones (lo elegimos en la S4)
DOCS = Path(__file__).parent / "docs"

_conn = None
_modelo = None


def conectar():
    """Conexion a Neon con el tipo vector registrado (igual que db.py de la S4-S5)."""
    global _conn
    if _conn is None:
        import psycopg
        from pgvector.psycopg import register_vector

        _conn = psycopg.connect(DATABASE_URL, autocommit=True)
        _conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(_conn)
    return _conn


def embedding(textos):
    global _modelo
    if _modelo is None:
        from sentence_transformers import SentenceTransformer

        _modelo = SentenceTransformer(MODELO_EMB)
    return _modelo.encode(textos, normalize_embeddings=True)


def trocear() -> list[dict]:
    """Un fragmento = UNA regla de la tienda (cada linea que empieza por '- '), con el titulo delante.

    Primera version: RecursiveCharacterTextSplitter con chunk_size=300. Juntaba 2-3 reglas por trozo (8 en total)
    y la de los auriculares Volta quedaba enterrada: ni aparecia en el top 3. Documentos de listas cortas = trocear
    por linea (ver salidas/02a_chunks_300.txt).
    """
    fragmentos = []
    for ruta in sorted(DOCS.glob("*.txt")):
        titulo, *lineas = ruta.read_text(encoding="utf-8").splitlines()
        tema = titulo.split("·")[0].strip()
        for linea in lineas:
            if linea.startswith("- "):
                fragmentos.append({"documento": ruta.name, "texto": f"{tema}: {linea[2:].strip()}"})
    return fragmentos


def indexar() -> int:
    """Crea la tabla (si no existe), la vacia y mete los fragmentos con su embedding. Devuelve cuantos."""
    conn = conectar()
    columnas = "id serial PRIMARY KEY, documento text, texto text, embedding vector(384)"
    conn.execute(f"CREATE TABLE IF NOT EXISTS {TABLA_RAG} ({columnas})")
    conn.execute(f"TRUNCATE {TABLA_RAG}")
    fragmentos = trocear()
    vectores = embedding([f["texto"] for f in fragmentos])
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO {TABLA_RAG} (documento, texto, embedding) VALUES (%s, %s, %s)",  # noqa: S608
            [(f["documento"], f["texto"], v) for f, v in zip(fragmentos, vectores, strict=True)],
        )
    return len(fragmentos)


def recuperar(pregunta: str, k: int = 4) -> list[dict]:
    """Los k fragmentos mas cercanos por distancia coseno (<=>): cuanto mas pequena, mas parecido."""
    q = embedding(pregunta)
    filas = (
        conectar()
        .execute(
            # noqa S608: TABLA_RAG es una constante de config.py; lo que escribe el usuario va SIEMPRE como %s
            f"SELECT documento, texto, embedding <=> %s AS d FROM {TABLA_RAG} ORDER BY embedding <=> %s LIMIT %s",  # noqa: S608
            (q, q, k),
        )
        .fetchall()
    )
    return [{"documento": doc, "texto": t, "distancia": round(float(d), 3)} for doc, t, d in filas]


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--indexar"]:
        print(f"Indexados {indexar()} fragmentos en la tabla {TABLA_RAG} (Neon)")
    else:
        for f in recuperar(" ".join(sys.argv[1:]) or "cuanto cuesta el envio"):
            print(f"{f['distancia']:.3f}  [{f['documento']}]  {f['texto']}")
