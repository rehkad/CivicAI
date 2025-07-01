"""Ingest Santa Barbara documents into a local Chroma vector store."""

"""Ingest text documents into a local Chroma vector store."""

from pathlib import Path
import os
import argparse

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings


DEFAULT_DATA_DIR = Path(__file__).parent / "santa_barbara"
DEFAULT_DB_DIR = Path(__file__).parent.parent / "vector_db"


def load_documents(data_dir: Path) -> list[str]:
    texts: list[str] = []
    for path in data_dir.glob("*.txt"):
        texts.append(path.read_text())
    return texts


def get_embeddings():
    try:
        return OpenAIEmbeddings(model="text-embedding-3-small")
    except Exception:
        model_dir = Path(__file__).parent.parent / "models" / "bge-small-en"
        if model_dir.exists():
            return HuggingFaceEmbeddings(model_name=str(model_dir))
        return HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")


def ingest(data_dir: Path, db_dir: Path) -> None:
    """Process ``data_dir`` and write embeddings to ``db_dir``."""
    documents = load_documents(data_dir)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = []
    for doc in documents:
        chunks.extend(splitter.split_text(doc))

    embeddings = get_embeddings()
    vectordb = Chroma(persist_directory=str(db_dir), embedding_function=embeddings)
    ids = [str(i) for i in range(len(chunks))]
    vectordb.add_texts(chunks, ids=ids)
    vectordb.persist()
    print(f"Ingested {len(chunks)} chunks into {db_dir}")


def main(data_dir: Path | None = None, db_dir: Path | None = None) -> None:
    data_env = os.getenv("DATA_DIR")
    db_env = os.getenv("VECTOR_DB_DIR")
    data_dir = Path(data_env) if data_env else data_dir or DEFAULT_DATA_DIR
    db_dir = Path(db_env) if db_env else db_dir or DEFAULT_DB_DIR
    ingest(data_dir, db_dir)


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into a Chroma vector store")
    parser.add_argument("--data-dir", type=Path, help="Directory of text files", default=None)
    parser.add_argument("--db-dir", type=Path, help="Destination for the vector DB", default=None)
    args = parser.parse_args()
    main(args.data_dir, args.db_dir)


if __name__ == "__main__":
    _cli()
