from fastmcp import FastMCP
from langchain_tavily import TavilySearch
import aiohttp
import asyncio
import re
import os

mcp = FastMCP("Web-Search")

JINA_TOKEN = os.environ.get("JINA_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {JINA_TOKEN}"
}

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

tavily_tool = TavilySearch(
    max_results=5,
    topic="general",
    tavily_api_key=TAVILY_API_KEY
)


def remove_markdown_images(markdown_text: str) -> str:
    # Xóa markdown image: ![alt](url)
    clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)

    # Xóa dòng trống thừa
    clean_text = "\n".join(
        line.strip()
        for line in clean_text.splitlines()
        if line.strip()
    )
    return clean_text


async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    jina_url = f"https://r.jina.ai/{url}"
    async with session.get(
        jina_url,
        headers=HEADERS,
        timeout=aiohttp.ClientTimeout(total=30)
    ) as resp:
        resp.raise_for_status()
        return await resp.text()


@mcp.tool(
    annotations={
    "title": "Search for web content using URL",
    "readOnlyHint": True
}
)
async def web_search(url: str) -> dict:
    """
    Fetch and return the main readable content of a webpage.

    Use this tool ONLY IF:
    - The user explicitly provides a full URL or link (http/https).
    
    DO NOT use this tool IF:
    - The user asks to search the web in general
    - The user provides keywords instead of a URL

    Args:
        url (str): Website URL

    Returns:
        dict: Markdown content
    """
    try:
        async with aiohttp.ClientSession() as session:
            raw_content = await fetch_page(session, url)

        content = remove_markdown_images(raw_content)

        return {
            "success": True,
            "url": url,
            "content": content
        }

    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Request timeout"
        }

    except aiohttp.ClientError as e:
        return {
            "success": False,
            "error": str(e)
        }
    
@mcp.tool(
    annotations={
    "title": "Search for real-time information",
    "readOnlyHint": True
}
)
async def tavily_search(query: str) -> dict:
    """
    Search for real-time, up-to-date information using Tavily.

    Args:
        query (str): Natural language search query

    Returns:
        dict: Tavily search results
    """
    try:
        result = await tavily_tool.ainvoke({"query": query})

        return {
            "success": True,
            "source": "tavily",
            "query": query,
            "response_time": result.get("response_time"),
            "results": result.get("results"),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8300
    )
