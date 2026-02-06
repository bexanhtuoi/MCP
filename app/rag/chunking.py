from app.rag.file_handle import extract_qa, extract_source_from_url, read_file_from_url
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
import re
from io import BytesIO
import json

def chunking_pdf(
    file_bytes: bytes,
    tag: str,
    source: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict]:

    documents: list[dict] = []

    reader = PdfReader(BytesIO(file_bytes))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        chunks = splitter.split_text(text)

        for chunk in chunks:
            clean_text = re.sub(r"\s+", " ", chunk.replace("\n", " ")).strip()

            documents.append({
                "text": clean_text,
                "metadata": {
                    "source": source,
                    "location": f"Page {page_idx + 1}",
                    "tag": tag,
                }
            })

    return documents

def chunking_md(
    file_bytes: bytes,
    tag: str,
    source: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict]:

    documents: list[dict] = []

    text = file_bytes.decode("utf-8", errors="ignore")

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ]
    )

    md_docs = header_splitter.split_text(text)

    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    for doc in md_docs:
        section_text = doc.page_content.strip()
        if not section_text:
            continue

        sub_chunks = recursive_splitter.split_text(section_text)

        headers = doc.metadata
        location_parts = [
            headers.get("h1"),
            headers.get("h2"),
            headers.get("h3"),
            headers.get("h4"),
        ]
        location = " > ".join([h for h in location_parts if h])

        for chunk in sub_chunks:
            clean_text = re.sub(
                r"\s+",
                " ",
                chunk.replace("\n", " ")
            ).strip()

            documents.append({
                "text": clean_text,
                "metadata": {
                    "source": source,
                    "location": location or "ROOT",
                    "tag": tag,
                }
            })

    return documents

def chunking_json(
    file_bytes: bytes,
    tag: str,
    source: str,
) -> list[dict]:

    documents: list[dict] = []

    try:
        data = json.loads(file_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid JSON file: {e}")

    if isinstance(data, dict):
        if "qa" in data and isinstance(data["qa"], list):
            items = data["qa"]
        else:
            items = [data]

    elif isinstance(data, list):
        items = data

    else:
        raise ValueError("JSON must be dict or list[dict]")

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        qa = extract_qa(item)
        if not qa:
            continue

        question, answer = qa

        text = f"Question: {question}\nAnswer: {answer}"

        documents.append({
            "text": text,
            "metadata": {
                "source": source,
                "location": f"Q&A #{idx}",
                "tag": tag,
            }
        })

    if not documents:
        raise ValueError("No valid Q&A found in JSON")

    return documents



async def chunking_file(tag: str, file_path: str ="./REAME.md", chunk_size: int = 500, chunk_overlap: int = 50) -> list[dict]:
    file_bytes = await read_file_from_url(file_path)

    source = extract_source_from_url(file_path)

    if file_path.endswith(".pdf"):
        file_documents: list[dict] = chunking_pdf(file_bytes, tag, source, chunk_size, chunk_overlap)
        return file_documents

    elif file_path.endswith(".md"):
        file_documents: list[dict] = chunking_md(file_bytes, tag, source, chunk_size, chunk_overlap)
        return file_documents

    elif file_path.endswith(".json"):
        file_documents: list[dict] = chunking_json(file_bytes, tag, source)
        return file_documents
    
    else:
        ValueError("Unsupport this type of file")