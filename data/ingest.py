"""Ingest Santa Barbara documents into a local Chroma vector store."""

from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings


DATA_DIR = Path(__file__).parent / "santa_barbara"
DB_DIR = Path(__file__).parent.parent / "vector_db"


def load_documents() -> list[str]:
    texts = []
    for path in DATA_DIR.glob("*.txt"):
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


def main():
    documents = load_documents()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = []
    for doc in documents:
        chunks.extend(splitter.split_text(doc))

    embeddings = get_embeddings()
    vectordb = Chroma(persist_directory=str(DB_DIR), embedding_function=embeddings)
    ids = [str(i) for i in range(len(chunks))]
    vectordb.add_texts(chunks, ids=ids)
    vectordb.persist()
    print(f"Ingested {len(chunks)} chunks into {DB_DIR}")


if __name__ == "__main__":
    main()
