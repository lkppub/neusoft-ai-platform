import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk, FAQEntry, DocumentStatus
from app.schemas.knowledge import (
    RAGQueryRequest, RAGQueryResponse,
    DocumentResponse, DocumentListResponse,
    CreateFAQRequest, UpdateFAQRequest, FAQResponse, FAQListResponse,
)
from app.services.knowledge.rag_pipeline import get_rag_pipeline

router = APIRouter(prefix="/knowledge", tags=["知识库"])

UPLOAD_DIR = "./data/uploads"


def ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(default="未命名文档"),
    chunk_size: int = Form(default=500),
    chunk_overlap: int = Form(default=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库"""
    ensure_upload_dir()

    # Determine file type
    ext = os.path.splitext(file.filename)[1].lower()
    type_map = {".pdf": "pdf", ".docx": "docx", ".doc": "docx", ".txt": "txt", ".md": "md"}
    file_type = type_map.get(ext)
    if not file_type:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    # Save file
    file_id = str(uuid.uuid4())
    save_name = f"{file_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, save_name)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = KnowledgeDocument(
        id=file_id,
        uploaded_by=current_user.id,
        title=title or file.filename,
        file_name=file.filename,
        file_type=file_type,
        file_size=len(content),
        file_path=save_path,
        status=DocumentStatus.PROCESSING,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    db.add(doc)
    await db.flush()

    # Commit so the background/inline processor can see this document from its own session.
    await db.commit()

    # Process in background (small files processed synchronously for immediate feedback)
    from app.services.knowledge.document_processor import process_document
    import logging
    logger = logging.getLogger(__name__)

    if len(content) <= 5 * 1024 * 1024:  # ≤5MB: process inline so user sees result immediately
        try:
            logger.info("Processing document %s synchronously (%d bytes)", file_id, len(content))
            await process_document(file_id, save_path, file_type, chunk_size, chunk_overlap)
        except Exception as e:
            logger.error("Document processing failed: %s", e)
    else:
        background_tasks.add_task(process_document, file_id, save_path, file_type, chunk_size, chunk_overlap)

    await db.refresh(doc)
    return doc


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表"""
    base_q = select(KnowledgeDocument)
    if current_user.role.value not in ["admin"]:
        base_q = base_q.where(KnowledgeDocument.uploaded_by == current_user.id)
    if status:
        base_q = base_q.where(KnowledgeDocument.status == status)

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar()

    q = base_q.order_by(desc(KnowledgeDocument.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情"""
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除文档"""
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # Delete file on disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Delete chunks from DB and vector store
    from app.services.knowledge.vector_store import get_vector_store
    vs = get_vector_store()
    await vs.delete_by_document(doc.id)

    await db.delete(doc)
    return {"message": "文档已删除"}


@router.post("/query", response_model=RAGQueryResponse)
async def query_knowledge(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG知识库查询"""
    from app.services.cache.redis_cache import get_cache
    cache = get_cache()

    # Try cache first
    cached = await cache.get_rag_result(request.question)
    if cached:
        return cached

    rag = get_rag_pipeline()
    result = await rag.query(request.question, top_k=request.top_k, score_threshold=request.score_threshold)

    # Cache result
    await cache.set_rag_result(request.question, result)
    return result


# ---- FAQ Endpoints ----

@router.get("/faqs", response_model=FAQListResponse)
async def list_faqs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str = Query(default=None),
    include_drafts: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """获取FAQ列表。include_drafts=True 时返回全部（含草稿），供管理页面使用。"""
    base_q = select(FAQEntry)
    if not include_drafts:
        base_q = base_q.where(FAQEntry.is_published == True)
    if category:
        base_q = base_q.where(FAQEntry.category == category)

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar()

    q = base_q.order_by(desc(FAQEntry.updated_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return FAQListResponse(
        items=[FAQResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/faqs", response_model=FAQResponse)
async def create_faq(
    request: CreateFAQRequest,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """创建FAQ条目（自动同步到 ChromaDB 向量库）"""
    faq = FAQEntry(
        category=request.category,
        question=request.question,
        answer=request.answer,
        created_by=current_user.id,
        is_published=request.is_published,
    )
    db.add(faq)
    await db.flush()
    await db.refresh(faq)

    # 同步到 ChromaDB 向量库
    try:
        from app.services.knowledge.vector_store import get_vector_store
        vs = get_vector_store()
        await vs.add_chunks([{
            "id": f"faq-{faq.id}",
            "content": f"Q: {faq.question}\nA: {faq.answer}",
            "metadata": {
                "source": f"FAQ-{faq.category}",
                "doc_id": f"faq-{faq.id}",
                "category": faq.category,
            },
        }])
    except Exception:
        pass  # ChromaDB 同步失败不影响主流程

    return faq


@router.put("/faqs/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: str,
    request: UpdateFAQRequest,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """更新FAQ条目（自动同步到 ChromaDB 向量库）"""
    result = await db.execute(select(FAQEntry).where(FAQEntry.id == faq_id))
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ不存在")

    if request.category is not None:
        faq.category = request.category
    if request.question is not None:
        faq.question = request.question
    if request.answer is not None:
        faq.answer = request.answer
    if request.is_published is not None:
        faq.is_published = request.is_published

    await db.flush()
    await db.refresh(faq)

    # 更新 ChromaDB：删旧加新
    try:
        from app.services.knowledge.vector_store import get_vector_store
        vs = get_vector_store()
        collection = vs._get_collection()
        try:
            collection.delete(ids=[f"faq-{faq_id}"])
        except Exception:
            pass
        await vs.add_chunks([{
            "id": f"faq-{faq.id}",
            "content": f"Q: {faq.question}\nA: {faq.answer}",
            "metadata": {
                "source": f"FAQ-{faq.category}",
                "doc_id": f"faq-{faq.id}",
                "category": faq.category,
            },
        }])
    except Exception:
        pass  # ChromaDB 同步失败不影响主流程

    return faq


@router.delete("/faqs/{faq_id}")
async def delete_faq(
    faq_id: str,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """删除FAQ条目（同步清理 ChromaDB）"""
    result = await db.execute(select(FAQEntry).where(FAQEntry.id == faq_id))
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ不存在")
    await db.delete(faq)

    # 从 ChromaDB 清理
    try:
        from app.services.knowledge.vector_store import get_vector_store
        vs = get_vector_store()
        collection = vs._get_collection()
        try:
            collection.delete(ids=[f"faq-{faq_id}"])
        except Exception:
            pass
    except Exception:
        pass

    return {"message": "FAQ已删除"}


@router.get("/faqs/categories")
async def get_faq_categories(
    include_drafts: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取FAQ分类列表。include_drafts=True（仅admin/cs）返回含草稿的分类。"""
    base_q = select(FAQEntry.category, func.count(FAQEntry.id))
    if not include_drafts or current_user.role.value not in ["admin", "customer_service"]:
        base_q = base_q.where(FAQEntry.is_published == True)
    base_q = base_q.group_by(FAQEntry.category)
    result = await db.execute(base_q)
    rows = result.all()
    return [{"category": row[0], "count": row[1]} for row in rows]


@router.get("/faqs/{faq_id}", response_model=FAQResponse)
async def get_faq(
    faq_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个FAQ详情（同时增加查看计数）"""
    result = await db.execute(select(FAQEntry).where(FAQEntry.id == faq_id))
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ不存在")

    faq.view_count += 1
    await db.flush()
    await db.refresh(faq)
    return faq
