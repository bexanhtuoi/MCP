import httpx
from urllib.parse import urlparse
import os

QUESTION_KEYS = {"question", "q", "query"}
ANSWER_KEYS = {"answer", "a", "response"}

def extract_qa(item: dict) -> tuple[str, str] | None:
    q = next((item[k] for k in QUESTION_KEYS if k in item), None)
    a = next((item[k] for k in ANSWER_KEYS if k in item), None)

    if not q or not a:
        return None

    return str(q).strip(), str(a).strip()


def extract_source_from_url(url: str) -> str:
    filename = os.path.basename(urlparse(url).path)
    return filename.split(".", 1)[1] 


async def read_file_from_url(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content