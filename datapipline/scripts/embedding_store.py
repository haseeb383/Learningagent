from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import dotenv_values

config = dotenv_values(".env")

OPENROUTER_API_KEY = config.get("OPENROUTER_API_KEY")
HUGGINGFACE_API_KEY = config.get("HUGGINGFACE_API_KEY")
CLOUDFARE_ACCOUNT_ID = config.get("CLOUDFARE_ACCOUNT_ID")
CLOUDFARE_API_KEY = config.get("CLOUDFARE_API_KEY")

embedding_model = HuggingFaceEndpointEmbeddings(
    model="BAAI/bge-large-en-v1.5",
    task="feature-extraction",
    huggingfacehub_api_token=HUGGINGFACE_API_KEY
)


def clean_metadata(metadata: dict) -> dict:
    """Remove empty lists, None values, and empty strings from metadata.
    ChromaDB doesn't accept empty lists or None."""
    cleaned = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, list) and len(v) == 0:
            continue
        if isinstance(v, str) and v == "":
            continue
        cleaned[k] = v
    return cleaned


def store_chunks(chunks, model=embedding_model):
    persist_directory = "datapipline/ChromeDB"
    cleaned_chunks = []
    for doc in chunks:
        cleaned_chunks.append(type(doc)(
            page_content=doc.page_content,
            metadata=clean_metadata(doc.metadata)
        ))
    vector_store = Chroma.from_documents(
        documents=cleaned_chunks,
        persist_directory=persist_directory,
        embedding=model
    )
    return vector_store