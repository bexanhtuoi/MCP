from langchain_nomic import NomicEmbeddings
import os

def get_embedding_model(model_name: str ="nomic-embed-text-v1.5") -> NomicEmbeddings:
    model = NomicEmbeddings(
    model=model_name,
    nomic_api_key=os.environ["NOMIC_API_KEY"],
    dimensionality=768,
    inference_mode="remote"
    )
    return model

async def text_embedding(text: str, embed_model: NomicEmbeddings) -> list[float]:
    vector: list[float] = await embed_model.aembed_query(text)
    return vector

def documents_embedding(documents: list[str], embed_model: NomicEmbeddings) -> list[list[float]]:
    vector: list[list[float]] = embed_model.embed_documents(documents)
    return vector