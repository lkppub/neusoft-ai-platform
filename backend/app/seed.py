"""
Seed script: Create demo users and sample data for all roles.
Run with: python -m app.seed  (from the backend directory)
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta, date

from app.core.database import async_session_factory, init_db
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.conversation import Conversation, Message, MessageRole
from app.models.knowledge import KnowledgeDocument, DocumentStatus, FAQEntry
from app.models.ticket import (
    CustomerServiceTicket, TicketMessage, TicketMessageType,
    ReplyTemplate, TicketPriority, TicketStatus,
)
from app.models.config import AIConfig, PromptTemplate
from app.models.analytics import DashboardSnapshot, AnalyticsReport


async def seed():
    await init_db()

    async with async_session_factory() as db:
        # ---- Users ----
        users = [
            User(id=str(uuid.uuid4()), username="admin", email="admin@neusoft.com", hashed_password=hash_password("123456"), role=UserRole.ADMIN, full_name="系统管理员", company_name="东软集团", department="信息技术部"),
            User(id=str(uuid.uuid4()), username="cs_staff", email="cs@neusoft.com", hashed_password=hash_password("123456"), role=UserRole.CUSTOMER_SERVICE, full_name="张客服", company_name="东软集团", department="客户服务部"),
            User(id=str(uuid.uuid4()), username="enterprise", email="enterprise@demo.com", hashed_password=hash_password("123456"), role=UserRole.ENTERPRISE, full_name="李企业", company_name="示范科技有限公司", department="运营部"),
            User(id=str(uuid.uuid4()), username="decision", email="decision@demo.com", hashed_password=hash_password("123456"), role=UserRole.DECISION_MAKER, full_name="王决策", company_name="示范科技有限公司", department="管理层"),
        ]
        user_map = {u.username: u for u in users}
        db.add_all(users)

        # ---- Conversations ----
        conv = Conversation(id=str(uuid.uuid4()), user_id=user_map["enterprise"].id, title="产品咨询对话", model_name="deepseek-chat", message_count=2)
        db.add(conv)
        db.add(Message(id=str(uuid.uuid4()), conversation_id=conv.id, role=MessageRole.USER, content="请问你们的专业版产品有哪些功能？"))
        db.add(Message(id=str(uuid.uuid4()), conversation_id=conv.id, role=MessageRole.ASSISTANT, content="关于产品信息，让我为您详细介绍：\n\n我们的产品线涵盖：\n- 基础版：适合小型企业\n- 专业版：适合中型企业\n- 企业版：适合大型企业\n\n每个版本都有不同的功能配置，您可以根据需求选择。"))

        conv2 = Conversation(id=str(uuid.uuid4()), user_id=user_map["enterprise"].id, title="退款问题咨询", model_name="deepseek-chat", message_count=2)
        db.add(conv2)
        db.add(Message(id=str(uuid.uuid4()), conversation_id=conv2.id, role=MessageRole.USER, content="我想申请退款，请问该怎么操作？"))
        db.add(Message(id=str(uuid.uuid4()), conversation_id=conv2.id, role=MessageRole.ASSISTANT, content="关于退款问题，我们的政策如下：\n\n1. 7天内无理由退款\n2. 超过7天需根据具体情况评估\n3. 退款将在3-5个工作日原路返回\n\n请问您需要我帮您提交退款申请吗？"))

        # ---- Knowledge Documents ----
        demo_kb_path = "./data/uploads/neusoft_knowledge_base.txt"
        demo_kb_size = 0
        try:
            import os as _os
            demo_kb_size = _os.path.getsize(demo_kb_path) if _os.path.exists(demo_kb_path) else 0
        except Exception:
            pass
        doc = KnowledgeDocument(
            id=str(uuid.uuid4()), uploaded_by=user_map["admin"].id,
            title="东软智慧商务产品与服务知识库", file_name="neusoft_knowledge_base.txt",
            file_type="txt", file_size=demo_kb_size, file_path=demo_kb_path,
            status=DocumentStatus.PROCESSING, chunk_count=0,
        )
        db.add(doc)
        await db.flush()
        doc_id = doc.id  # 保存 ID 供后续处理

        # ---- FAQ Entries ----
        faqs = [
            FAQEntry(category="退款", question="如何申请退款？", answer="登录您的账户，在订单页面找到对应订单，点击'申请退款'按钮。7天内可无理由退款。", created_by=user_map["cs_staff"].id),
            FAQEntry(category="账户", question="忘记密码怎么办？", answer="在登录页面点击'忘记密码'，输入注册邮箱，系统将发送重置链接到您的邮箱。", created_by=user_map["cs_staff"].id),
            FAQEntry(category="产品", question="专业版和企业版有什么区别？", answer="专业版支持50个用户、100GB存储；企业版支持无限用户、1TB存储，并提供API接入和定制开发服务。", created_by=user_map["cs_staff"].id),
            FAQEntry(category="技术", question="系统提示'连接超时'怎么办？", answer="请检查您的网络连接，尝试刷新页面。如果问题持续，请联系技术支持热线：400-xxx-xxxx。", created_by=user_map["cs_staff"].id),
        ]
        for f in faqs:
            db.add(f)

        # ---- Tickets ----
        tickets = [
            CustomerServiceTicket(
                id=str(uuid.uuid4()), user_id=user_map["enterprise"].id, assigned_to=user_map["cs_staff"].id,
                subject="无法登录系统", description="今天早上开始无法登录，提示'认证失败'。已尝试重置密码但未收到邮件。",
                problem_category="账户问题", priority=TicketPriority.HIGH, status=TicketStatus.IN_PROGRESS,
                ai_classification={"category": "账户问题", "priority": "high", "sentiment": "negative", "key_details": "用户无法登录，密码重置邮件未收到"},
            ),
            CustomerServiceTicket(
                id=str(uuid.uuid4()), user_id=user_map["enterprise"].id,
                subject="咨询产品价格", description="我们对贵公司的专业版产品很感兴趣，想了解具体的价格方案。",
                problem_category="产品咨询", priority=TicketPriority.MEDIUM, status=TicketStatus.OPEN,
            ),
        ]
        for t in tickets:
            db.add(t)
        db.add(TicketMessage(id=str(uuid.uuid4()), ticket_id=tickets[0].id, sender_id=user_map["enterprise"].id, message_type=TicketMessageType.CUSTOMER, content=tickets[0].description))
        db.add(TicketMessage(id=str(uuid.uuid4()), ticket_id=tickets[0].id, sender_id=user_map["cs_staff"].id, message_type=TicketMessageType.AGENT, content="您好，我们已收到您的问题，正在为您排查。请您提供一下注册邮箱，我们帮您检查账户状态。"))

        # ---- Reply Templates ----
        templates = [
            ReplyTemplate(category="通用", title="欢迎语", content="尊敬的{customer_name}，您好！感谢您联系东软客服中心。关于您咨询的{issue_summary}问题，我们将尽快为您处理。", variables=["customer_name", "issue_summary"], created_by=user_map["cs_staff"].id),
            ReplyTemplate(category="退款", title="退款确认", content="您好，您的退款申请已收到。退款将在3-5个工作日内原路返回到您的支付账户。如有疑问，请随时联系我们。", variables=[], created_by=user_map["cs_staff"].id),
            ReplyTemplate(category="技术", title="技术跟进", content="您好，关于您反馈的技术问题，我们的技术团队已开始排查。初步判断可能是{possible_cause}导致。我们会尽快解决并通知您。", variables=["possible_cause"], created_by=user_map["cs_staff"].id),
        ]
        for t in templates:
            db.add(t)

        # ---- AI Configs ----
        configs = [
            AIConfig(config_key="default_model", config_value="deepseek-chat", description="默认使用的AI模型"),
            AIConfig(config_key="max_tokens", config_value="4096", description="最大生成token数"),
            AIConfig(config_key="temperature", config_value="0.7", description="生成温度（0-1）"),
            AIConfig(config_key="system_prompt", config_value="你是东软智慧商务AI助手，帮助用户解决商务问题。回答应专业、准确、友好。", description="系统默认提示词"),
        ]
        for c in configs:
            db.add(c)

        # ---- Prompt Templates ----
        prompts = [
            PromptTemplate(name="通用客服", scenario="general_chat", system_prompt="你是专业的商务客服助手，请用友好、专业的态度回答用户问题。", user_prompt_template="用户问题：{question}\n请提供准确、有帮助的回答。", variables=[{"name": "question", "type": "string", "required": True}], created_by=user_map["admin"].id),
            PromptTemplate(name="知识库问答", scenario="knowledge_qa", system_prompt="基于提供的知识库内容回答问题。如果知识库中没有相关信息，请诚实告知。", user_prompt_template="知识库内容：\n{context}\n\n用户问题：{question}", variables=[{"name": "context", "type": "string", "required": True}, {"name": "question", "type": "string", "required": True}], created_by=user_map["admin"].id),
            PromptTemplate(name="问题分类", scenario="customer_service", system_prompt="分析客户问题，输出JSON格式的分类结果。", user_prompt_template="客户问题：{inquiry}\n请分析并分类。", variables=[{"name": "inquiry", "type": "string", "required": True}], created_by=user_map["admin"].id),
        ]
        for p in prompts:
            db.add(p)

        # ---- Dashboard Snapshots (last 7 days) ----
        today = date.today()
        for i in range(7):
            d = today - timedelta(days=i)
            snap = DashboardSnapshot(
                snapshot_date=d,
                total_inquiries=80 - i * 5 + (i % 3) * 10,
                total_tickets=25 - i * 2 + (i % 2) * 5,
                resolved_tickets=20 - i + i % 3,
                avg_response_time_seconds=120.0 + i * 10,
                satisfaction_score=min(5.0, 3.8 + i * 0.15),
                category_distribution={"技术支持": 45 - i, "账单咨询": 30, "产品咨询": 25 + i, "投诉建议": 12, "其他": 8},
                top_faq_queries={"退款流程": 120, "账户登录": 90, "产品规格": 80},
            )
            db.add(snap)

        # ---- Analytics Report ----
        report = AnalyticsReport(
            report_type="weekly_summary", title="本周运营分析报告",
            summary="本周平台运营状况良好。总咨询量较上周增长15%，工单处理率达92%。客户满意度评分4.1/5.0，略有提升。技术支持类问题占比最高（37.5%），建议加强FAQ知识库建设。AI自动回复率65%，有效减少了客服负担。",
            result_data={"total_inquiries": 560, "total_tickets": 175, "satisfaction": 4.1, "resolution_rate": 92.0},
            generated_by=user_map["admin"].id,
        )
        db.add(report)

        await db.commit()
        print("[OK] Seed data created successfully!")
        print(f"   Users: admin/123456, cs_staff/123456, enterprise/123456, decision/123456")
        print(f"   Login as 'admin' for full access.")

        # ---- 处理知识库文档并索引到 Chroma ----
        print("\n[..] Processing knowledge base document...")
        try:
            from app.services.knowledge.document_processor import process_document
            await process_document(doc_id, demo_kb_path, "txt", chunk_size=500, chunk_overlap=50)
            print("[OK] Knowledge document indexed into Chroma!")
        except Exception as e:
            print(f"[WARN] Document processing failed (non-fatal): {e}")

        # ---- 将 FAQ 条目也索引到 Chroma ----
        print("[..] Indexing FAQ entries into Chroma...")
        try:
            from app.services.knowledge.vector_store import get_vector_store
            vs = get_vector_store()
            faq_chunks = []
            for faq in faqs:
                faq_chunks.append({
                    "id": f"faq-{faq.id}",
                    "content": f"Q: {faq.question}\nA: {faq.answer}",
                    "metadata": {
                        "source": f"FAQ-{faq.category}",
                        "doc_id": "faq_seed",
                        "category": faq.category,
                    },
                })
            await vs.add_chunks(faq_chunks)
            print(f"[OK] {len(faq_chunks)} FAQ entries indexed into Chroma!")
        except Exception as e:
            print(f"[WARN] FAQ indexing failed (non-fatal): {e}")

        print("\n[OK] Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
