from app.rag.vector_store import init_vector_store
from app.rag.embedding import get_embedding_model
from langchain_core.runnables.config import run_in_executor
from langchain_core.documents import Document
import asyncio

vector_store = init_vector_store()
embed_model = get_embedding_model()


async def retrieve_relevant_documents(query: str, k: int = 20, tag: str | None = None) -> list[dict]:

    filter_dict = {"tag": tag} if tag is not None else None
    documents: list[Document] = await run_in_executor(None, vector_store.similarity_search, query, k, filter=filter_dict)
    retrieved_texts = [
        {
            "text": item.page_content,
            "metadata": item.metadata
        }
        for item in documents
                    ]
    
    return retrieved_texts

if __name__ == "__main__":

    query = "MCP là gì?"
    
    results = asyncio.run(retrieve_relevant_documents(query, k=20, tag="AI"))

    for item in results:
        print("\n\nDocument:", item["text"])
        print("\nMetadata:", item["metadata"])

    print(len(results))

