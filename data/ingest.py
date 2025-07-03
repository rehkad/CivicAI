"""Ingest text documents into a local Chroma vector store."""

from pathlib import Path
import os
import argparse
import logging

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings


DEFAULT_DATA_DIR = Path(__file__).parent / "santa_barbara"
DEFAULT_DB_DIR = Path(__file__).parent.parent / "vector_db"

logger = logging.getLogger(__name__)


def load_documents(data_dir: Path) -> list[str]:
    """Return the UTF-8 contents of all ``*.txt`` files sorted by name."""
    texts: list[str] = []
    for path in sorted(data_dir.glob("*.txt")):
        texts.append(path.read_text(encoding="utf-8"))
    return texts


def get_embeddings():
    """Return an embeddings backend, preferring OpenAI when available."""
    try:
        return OpenAIEmbeddings(model="text-embedding-3-small")
    except Exception:
        model_dir = Path(__file__).parent.parent / "models" / "bge-small-en"
        if model_dir.exists():
            return HuggingFaceEmbeddings(model_name=str(model_dir))
        return HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")


def ingest(data_dir: Path, db_dir: Path) -> None:
    """Process ``data_dir`` and write embeddings to ``db_dir``."""
    data_dir = data_dir.expanduser()
    db_dir = db_dir.expanduser()
    if not data_dir.exists():
        raise FileNotFoundError(f"{data_dir} does not exist")

    logger.info("Ingesting documents from %s", data_dir)
    documents = load_documents(data_dir)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks: list[str] = []
    for doc in documents:
        chunks.extend(splitter.split_text(doc))

    embeddings = get_embeddings()
    vectordb = Chroma(persist_directory=str(db_dir), embedding_function=embeddings)
    ids = [str(i) for i in range(len(chunks))]
    vectordb.add_texts(chunks, ids=ids)
    vectordb.persist()
    logger.info("Ingested %d chunks into %s", len(chunks), db_dir)


def main(data_dir: Path | None = None, db_dir: Path | None = None) -> None:
    data_env = os.getenv("DATA_DIR")
    db_env = os.getenv("VECTOR_DB_DIR")
    data_dir = Path(data_env) if data_env else data_dir or DEFAULT_DATA_DIR
    db_dir = Path(db_env) if db_env else db_dir or DEFAULT_DB_DIR
    ingest(data_dir, db_dir)


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest documents into a Chroma vector store"
    )
    parser.add_argument(
        "--data-dir", type=Path, help="Directory of text files", default=None
    )
    parser.add_argument(
        "--db-dir", type=Path, help="Destination for the vector DB", default=None
    )
    args = parser.parse_args()
    main(args.data_dir, args.db_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _cli()
