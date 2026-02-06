from fastmcp import FastMCP
from app.rag.retrieval import retrieve_relevant_documents
import asyncio

mcp = FastMCP("RAG")


@mcp.tool(
    annotations={
        "title": "Retrieve Relevant Documents",
        "readOnlyHint": True
})
async def retrieval(query: str, k: int, tag: str | None) -> list[dict]:
    """
     Retrieve relevant information from a curated document knowledge base
    to ground the chatbot’s responses with accurate and reliable sources.

    Arg:
        - query: refined from the user question
        - k: number of documents (higher for broad questions, lower for specific ones), max k = 20
        - tag: inferred from the question

    Return:
        List of dict documents
    """
    k = int((k + 20 - abs(k-20)) / 2) if k > 0 else 1 

    try:

        results = await asyncio.wait_for(
            retrieve_relevant_documents(query, k, tag),
            timeout=5.0
        )
    except asyncio.TimeoutError:

        results = []


    return results

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8100)