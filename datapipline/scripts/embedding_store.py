from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import dotenv_values

config = dotenv_values(".env")

OPENROUTER_API_KEY=config.get("OPENROUTER_API_KEY")
HUGGINGFACE_API_KEY=config.get("HUGGINGFACE_API_KEY")
CLOUDFARE_ACCOUNT_ID=config.get("CLOUDFARE_ACCOUNT_ID")
CLOUDFARE_API_KEY=config.get("CLOUDFARE_API_KEY")

embedding_model = HuggingFaceEndpointEmbeddings(
  model="BAAI/bge-large-en-v1.5",
  task="feature-extraction",
  huggingfacehub_api_token=HUGGINGFACE_API_KEY
)

def store_chunks(chunks, model=embedding_model):
  persist_directory = "datapipline/ChromeDB"
  vector_store = Chroma.from_documents(
    documents=chunks,
    persist_directory=persist_directory,
    embedding=model
  )
  return vector_store