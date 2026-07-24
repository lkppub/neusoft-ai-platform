"""
Generate test tickets for Week 29 (July 12-18, 2026) and randomly resolve some.
Run: python seed_week29_tickets.py
"""
import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta

from app.core.database import async_session_factory
from app.models.ticket import (
    CustomerServiceTicket, TicketMessage, TicketStatus,
    TicketPriority, TicketMessageType,
)
from app.models.user import User
from sqlalchemy import select

# User IDs from DB
ENTERPRISE_USER_ID = "14fd0465-7425-4634-9fb0-3dde8da3ab6f"  # enterprise
CS_STAFF_ID = "4aac089b-2507-435c-8289-571b13c2ed9f"  # cs_staff
ADMIN_ID = "36be1066-a619-4fcb-a063-ab2df8032c51"  # admin

# Week 29: July 12 (Sun) to July 18 (Sat), 2026
WEEK_START = datetime(2026, 7, 12, 0, 0, 0, tzinfo=timezone.utc)
WEEK_END = datetime(2026, 7, 18, 23, 59, 59, tzinfo=timezone.utc)


def random_time_in_week():
    """Generate a random datetime within week 29."""
    delta = WEEK_END - WEEK_START
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return WEEK_START + timedelta(seconds=random_seconds)


# Ticket templates with varied realistic scenarios
TICKET_TEMPLATES = [
    {
        "subject": "无法登录企业账号",
        "description": "从今天早上开始，我使用正确的账号密码无法登录系统，提示"认证失败"，已尝试重置密码但仍然无法登录。需要紧急处理。",
        "category": "账号问题",
        "priority": TicketPriority.URGENT,
    },
    {
        "subject": "产品报价咨询",
        "description": "请问贵公司智慧商务平台的基础版和专业版分别是什么价格？我们公司有200人左右，想了解适合哪个版本以及是否有批量优惠。",
        "category": "商务咨询",
        "priority": TicketPriority.LOW,
    },
    {
        "subject": "数据报表导出失败",
        "description": "在数据分析模块中导出月度报表时，点击"导出Excel"按钮后一直显示"处理中"，等了10分钟也没有下载文件。尝试了Chrome和Edge浏览器都是同样的问题。",
        "category": "技术问题",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "API接口调用报500错误",
        "description": "调用 /api/v1/data/sync 接口时返回500 Internal Server Error。请求参数完全按照文档来的，昨天还正常使用。请帮忙排查。",
        "category": "技术问题",
        "priority": TicketPriority.HIGH,
    },
    {
        "subject": "员工账号批量开通申请",
        "description": "我司新入职30名员工，需要批量开通系统账号。请问是否有批量导入功能？如果没有，我需要提供什么格式的信息来加快开通流程？",
        "category": "账号问题",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "退款申请流程咨询",
        "description": "我们购买的专业版服务使用不到一个月，因业务调整不再需要了，想了解退款政策和具体申请流程。合同编号：HT-2026-0712",
        "category": "售后服务",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "系统响应速度变慢",
        "description": "最近三天系统整体响应速度明显变慢，特别是高峰期（9:00-11:00）打开一个页面需要10秒以上。严重影响正常办公，请尽快优化。",
        "category": "技术问题",
        "priority": TicketPriority.HIGH,
    },
    {
        "subject": "PDF合同模板生成错误",
        "description": "使用合同管理模块生成PDF合同时，生成的文档中公司公章位置偏移到了页面之外，且部分中文字符显示为乱码。已测试多个模板都有此问题。",
        "category": "技术问题",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "客户信息导入后数据丢失",
        "description": "导入CSV客户信息文件（约500条记录）后，系统提示导入成功，但实际只显示了320条。检查原始CSV文件格式正确，编码为UTF-8。",
        "category": "数据问题",
        "priority": TicketPriority.HIGH,
    },
    {
        "subject": "手机端App无法查看工单附件",
        "description": "iOS客户端最新版本（v3.2.1）中，工单详情页的附件（PDF、图片）点击后无法预览，显示"文件格式不支持"。安卓端正常。",
        "category": "技术问题",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "权限配置需求",
        "description": "我们部门新设了"区域经理"角色，需要配置以下权限：查看本区域客户数据、创建和分配工单、查看本区域报表。请问能否支持自定义角色权限？",
        "category": "功能需求",
        "priority": TicketPriority.LOW,
    },
    {
        "subject": "合同到期续费提醒设置",
        "description": "希望系统能增加合同到期自动提醒功能，提前30天/7天/1天分别发送邮件和站内信通知。目前我们只能人工查看，容易遗漏。",
        "category": "功能需求",
        "priority": TicketPriority.LOW,
    },
    {
        "subject": "订单金额计算有误",
        "description": "订单号ORD-20260715-0892的总额计算不正确。商品明细：A产品x3（单价5000）+ B服务x1（年费12000），正确应为27000元，但系统显示为30000元。请核查。",
        "category": "商务咨询",
        "priority": TicketPriority.HIGH,
    },
    {
        "subject": "培训需求 — 新员工系统操作培训",
        "description": "我司近期有新员工入职，希望贵方能提供一次线上系统操作培训，内容包括：工单系统使用、数据查询导出、权限申请流程。人数约20人，时间可协调。",
        "category": "售后服务",
        "priority": TicketPriority.LOW,
    },
    {
        "subject": "消息通知延迟严重",
        "description": "工单状态变更后，邮件和站内信通知延迟严重，有时超过2小时才收到。上周五（7月10日）开始出现此问题，之前一切正常。",
        "category": "技术问题",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "多语言界面支持咨询",
        "description": "我们与日本客户有业务往来，想了解系统是否支持日语界面？如果目前不支持，是否有国际化计划和时间表？",
        "category": "功能需求",
        "priority": TicketPriority.LOW,
    },
    {
        "subject": "数据库备份策略咨询",
        "description": "作为信息安全负责人，我需要了解贵平台的数据备份策略：备份频率、保留周期、灾难恢复时间目标（RTO）和数据恢复点目标（RPO）。这对我们的合规审查很重要。",
        "category": "商务咨询",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "第三方系统集成方案",
        "description": "我们使用Salesforce作为CRM系统，希望能与贵平台实现数据双向同步：客户信息、合同数据、工单状态。请问是否提供标准API或 connectors？",
        "category": "功能需求",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "安全漏洞反馈 — XSS风险",
        "description": "我们在做安全测试时发现，工单描述字段存在反射型XSS漏洞。输入<script>alert(1)</script>后，在工单详情页会执行该脚本。这是严重安全隐患，请尽快修复。",
        "category": "技术问题",
        "priority": TicketPriority.URGENT,
    },
    {
        "subject": "历史工单数据迁移",
        "description": "我们从旧系统导出了近3年的工单数据（约5000条），希望迁移到贵平台。数据格式为Excel，包含工单编号、主题、描述、状态、创建时间等字段。请问迁移流程是怎样的？",
        "category": "数据问题",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "系统维护时段调整请求",
        "description": "贵平台目前的维护窗口是每周日凌晨2:00-4:00，但我们有海外业务，这个时段正好是北美工作日高峰。能否调整为周六维护，或提供分区域维护方案？",
        "category": "售后服务",
        "priority": TicketPriority.LOW,
    },
    {
        "subject": "自定义报表字段需求",
        "description": "目前的数据分析报表只支持预设字段，我们希望能自定义选择维度和指标，比如按产品线+区域+时间段的多维交叉分析。这个功能在规划中吗？",
        "category": "功能需求",
        "priority": TicketPriority.LOW,
    },
    {
        "subject": "大文件上传失败",
        "description": "尝试上传一个150MB的产品手册PDF时，进度到60%左右就失败了，提示"网络错误"。已尝试3次，均失败。100MB以下的小文件上传正常。需要确认是否有限制。",
        "category": "技术问题",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "工单自动分配规则配置",
        "description": "希望支持按工单分类自动分配给对应的客服组：技术类→技术组，商务类→商务组，账号类→运营组。目前的分配方式是手动或随机，效率太低。",
        "category": "功能需求",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "增值税发票信息修改",
        "description": "我司税务信息变更，需要在系统中更新开票信息：税号从91110108MA001XXXX变更为91110108MA002YYYY，公司地址也变了。请问如何操作？",
        "category": "账号问题",
        "priority": TicketPriority.LOW,
    },
    {
        "subject": "知识库文章审核太慢",
        "description": "我们提交了5篇FAQ文章到知识库，已经等了3个工作日还在"审核中"。客户在咨询这些问题时AI无法自动回答，只能转人工。能否加快审核流程？",
        "category": "售后服务",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "登录二次验证需求",
        "description": "出于安全合规要求，我们希望为所有账号启用双因素认证（2FA）。请问平台支持哪些方式？短信验证码、TOTP（如Google Authenticator）、还是硬件密钥？",
        "category": "功能需求",
        "priority": TicketPriority.MEDIUM,
    },
    {
        "subject": "月度账单明细查询",
        "description": "6月份的账单金额比5月多了约3000元，但我们的使用量没有明显变化。请提供6月的详细消费明细，包括各项服务的具体用量和单价。",
        "category": "商务咨询",
        "priority": TicketPriority.MEDIUM,
    },
]

# Resolution replies for resolved tickets
RESOLUTION_REPLIES = [
    "问题已解决。经排查是服务器缓存导致，清理缓存后恢复正常。如有问题请随时联系我们。",
    "已为您处理完毕。账号权限已更新，请退出重新登录后生效。",
    "该问题已在最新版本中修复，请升级至v3.3.0版本。升级包和说明文档已发送至您的邮箱。",
    "经核查，该问题属于配置错误，已修正相关参数。建议对关键配置项增加变更审批流程以避免类似问题。",
    "已与产品团队确认，您反馈的问题已纳入下个迭代（Sprint 35），预计8月初上线。届时会邮件通知您。",
    "数据已恢复。建议后续操作前先在测试环境验证，确认无误后再在生产环境执行。",
    "已为您开通所需权限，功能使用指南已发送。如有操作疑问可预约一对一远程指导。",
    "经与研发确认，该问题是已知Bug，优先级已提升至P0，预计24小时内发布hotfix。给您带来不便深表歉意。",
    "退款申请已提交财务审核，预计3-5个工作日到账。审核进度可在"售后记录"中查看。",
    "问题已定位并修复，原因是数据库连接池配置过小导致高峰期排队。已将连接池从10扩至50，后续会持续监控。",
    "培训已安排在下周三（7月22日）下午2:00-4:00，线上腾讯会议，会议链接已发送至您的邮箱。",
    "已为您批量导入了所有员工账号，初始密码已分别发送至各员工邮箱，请提醒他们首次登录后修改密码。",
]


async def generate_tickets():
    async with async_session_factory() as db:
        # Verify users exist
        for uid in [ENTERPRISE_USER_ID, CS_STAFF_ID, ADMIN_ID]:
            result = await db.execute(select(User).where(User.id == uid))
            if not result.scalar_one_or_none():
                print(f"ERROR: User {uid} not found!")
                return

        tickets_created = []
        for i, tmpl in enumerate(TICKET_TEMPLATES):
            created_at = random_time_in_week()

            ticket = CustomerServiceTicket(
                id=str(uuid.uuid4()),
                user_id=ENTERPRISE_USER_ID,
                assigned_to=random.choice([CS_STAFF_ID, CS_STAFF_ID, CS_STAFF_ID, None]),  # 75% assigned
                subject=tmpl["subject"],
                description=tmpl["description"],
                problem_category=tmpl["category"],
                priority=tmpl["priority"],
                status=TicketStatus.OPEN,  # start open, will resolve some later
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(ticket)
            await db.flush()

            # Add initial customer message
            msg = TicketMessage(
                ticket_id=ticket.id,
                sender_id=ENTERPRISE_USER_ID,
                message_type=TicketMessageType.CUSTOMER,
                content=tmpl["description"],
                created_at=created_at + timedelta(seconds=10),
            )
            db.add(msg)
            await db.flush()

            tickets_created.append(ticket)
            print(f"  ✓ [{i+1:02d}] {tmpl['subject'][:30]}... | {tmpl['priority'].value} | {created_at.strftime('%m/%d %H:%M')}")

        await db.commit()
        print(f"\nCreated {len(tickets_created)} tickets for Week 29 (July 12-18, 2026)")

        # ── Randomly resolve ~65% of tickets ──
        random.shuffle(tickets_created)
        resolve_count = int(len(tickets_created) * 0.65)
        to_resolve = tickets_created[:resolve_count]

        resolved = 0
        for ticket in to_resolve:
            # Re-fetch to attach to current session
            result = await db.execute(
                select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket.id)
            )
            t = result.scalar_one_or_none()
            if not t:
                continue

            # Resolve at a time after creation
            resolve_time = t.created_at + timedelta(
                hours=random.randint(1, 48),
                minutes=random.randint(0, 59),
            )
            # Ensure resolve_time is not after week end
            if resolve_time > WEEK_END:
                resolve_time = WEEK_END - timedelta(minutes=random.randint(10, 120))

            t.status = TicketStatus.RESOLVED
            t.resolved_at = resolve_time
            t.final_reply = random.choice(RESOLUTION_REPLIES)
            t.updated_at = resolve_time

            # Add resolution system message
            sys_msg = TicketMessage(
                ticket_id=t.id,
                sender_id=random.choice([CS_STAFF_ID, ADMIN_ID]),
                message_type=TicketMessageType.SYSTEM,
                content=f"工单已解决: {t.final_reply}",
                created_at=resolve_time,
            )
            db.add(sys_msg)

            # Also add a CS agent reply before resolution for realism
            agent_msg = TicketMessage(
                ticket_id=t.id,
                sender_id=random.choice([CS_STAFF_ID, ADMIN_ID]),
                message_type=TicketMessageType.AGENT,
                content=random.choice([
                    "收到您的反馈，我们正在排查处理中，请稍候。",
                    "感谢您的反馈，已转交相关技术人员处理。",
                    "问题已复现，正在定位原因。",
                    "已了解您的问题，将在2小时内给您答复。",
                ]),
                created_at=t.created_at + timedelta(hours=random.randint(1, 6)),
            )
            db.add(agent_msg)

            resolved += 1

        await db.commit()
        print(f"Resolved {resolved}/{len(tickets_created)} tickets (~65%)")

        # ── Summary ──
        from sqlalchemy import func
        total_q = select(func.count(CustomerServiceTicket.id)).where(
            CustomerServiceTicket.created_at >= WEEK_START,
            CustomerServiceTicket.created_at <= WEEK_END,
        )
        total = (await db.execute(total_q)).scalar()

        resolved_q = select(func.count(CustomerServiceTicket.id)).where(
            CustomerServiceTicket.created_at >= WEEK_START,
            CustomerServiceTicket.created_at <= WEEK_END,
            CustomerServiceTicket.status == TicketStatus.RESOLVED,
        )
        resolved_total = (await db.execute(resolved_q)).scalar()

        print(f"\n{'='*50}")
        print(f"Week 29 (July 12-18, 2026) Summary:")
        print(f"  Total tickets: {total}")
        print(f"  Resolved: {resolved_total}")
        print(f"  Open/In Progress: {total - resolved_total}")
        print(f"  Resolution rate: {resolved_total/total*100:.1f}%")
        print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(generate_tickets())
