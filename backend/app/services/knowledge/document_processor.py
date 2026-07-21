import os
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk, DocumentStatus


async def process_document(
    document_id: str,
    file_path: str,
    file_type: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
):
    """Process a document: extract text, chunk, and store embeddings."""
    async with async_session_factory() as db:
        try:
            # Get document record
            result = await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                return

            doc.status = DocumentStatus.PROCESSING
            await db.commit()

            # Extract text based on file type
            text = await _extract_text(file_path, file_type)
            if not text.strip():
                doc.status = DocumentStatus.ERROR
                doc.error_message = "无法提取文本内容"
                await db.commit()
                return

            # Chunk the text
            chunks = await _chunk_text(text, chunk_size, chunk_overlap)

            # Create chunk records
            from app.services.knowledge.vector_store import get_vector_store
            vs = get_vector_store()

            chunk_docs = []
            chroma_docs = []
            for i, chunk_text in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                chunk = KnowledgeChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk_text,
                    token_count=len(chunk_text),
                    metadata={"source": doc.file_name, "type": file_type},
                )
                chunk_docs.append(chunk)
                chroma_docs.append({"id": chunk_id, "content": chunk_text, "metadata": {"source": doc.file_name, "doc_id": document_id, "chunk_index": i}})

            db.add_all(chunk_docs)

            # Add to vector store
            await vs.add_chunks(chroma_docs)

            # Update document status
            doc.status = DocumentStatus.READY
            doc.chunk_count = len(chunks)
            await db.commit()

        except Exception as e:
            await db.rollback()
            # Re-fetch document in a new session-safe way
            async with async_session_factory() as retry_db:
                retry_result = await retry_db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
                )
                retry_doc = retry_result.scalar_one_or_none()
                if retry_doc:
                    retry_doc.status = DocumentStatus.ERROR
                    retry_doc.error_message = str(e)[:500]
                    await retry_db.commit()


async def _extract_text(file_path: str, file_type: str) -> str:
    """Extract text from a file based on its type."""
    if file_type == "txt" or file_type == "md":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif file_type == "pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except ImportError:
            return _fallback_read(file_path)

    elif file_type == "docx":
        try:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except ImportError:
            return _fallback_read(file_path)

    return ""


def _fallback_read(file_path: str) -> str:
    """Fallback: try reading as text."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


async def _chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Chunk text using LangChain's RecursiveCharacterTextSplitter."""
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )
        return splitter.split_text(text)
    except ImportError:
        # Simple fallback chunking
        chunks = []
        for i in range(0, len(text), chunk_size - chunk_overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        return chunks
