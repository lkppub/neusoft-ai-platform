"""Add reply templates directly to existing DB."""
import asyncio
import sys
sys.path.insert(0, 'backend')

from app.core.database import async_session_factory
from app.models.ticket import ReplyTemplate
from app.models.user import User
from sqlalchemy import select, func

EXTRA_TEMPLATES = [
    ("账户", "密码重置指引", "尊敬的{customer_name}，您好！关于您反馈的密码问题，请按以下步骤操作：\n1. 访问登录页面，点击忘记密码\n2. 输入您的注册邮箱\n3. 查收重置邮件（如未收到，请检查垃圾邮件箱）\n4. 点击邮件中的链接设置新密码\n\n如仍无法解决，请回复此消息，我们将协助您手动重置。", ["customer_name"]),
    ("账户", "账户异常通知", "尊敬的{customer_name}，您好！我们检测到您的账户存在异常登录活动，已暂时限制部分功能。请尽快联系客服热线 400-xxx-xxxx 进行身份验证，以恢复账户正常使用。给您带来不便，敬请谅解。", ["customer_name"]),
    ("退款", "退款进度查询", "尊敬的{customer_name}，您好！关于您咨询的退款进度，当前状态如下：\n\n退款申请：已收到\n处理状态：审核中（预计1-2个工作日）\n到账时间：审核通过后3-5个工作日原路返回\n\n如需加急处理，请提供订单号，我们将优先为您处理。", ["customer_name"]),
    ("产品", "试用申请回复", "尊敬的{customer_name}，您好！感谢您对{issue_summary}的关注。我们提供以下试用方案：\n\n免费试用：14天全功能试用，无需绑定支付方式\n专属演示：我们的产品顾问可为您安排30分钟线上演示\n定制方案：根据您的业务需求提供个性化配置建议\n\n如需开通试用或预约演示，请回复告知您的偏好。", ["customer_name", "issue_summary"]),
    ("通用", "问题升级通知", "尊敬的{customer_name}，您好！关于您反馈的{issue_summary}问题，由于涉及更深层次的技术排查，我们已将此问题升级至高级技术团队处理。预计24小时内会有专人联系您，请您保持通讯畅通。感谢您的耐心等待！", ["customer_name", "issue_summary"]),
    ("通用", "工单关闭确认", "尊敬的{customer_name}，您好！关于{issue_summary}的工单，我们确认您的问题已得到解决。如无其他疑问，此工单将在48小时后自动关闭。如有任何后续问题，欢迎随时联系我们。感谢您选择东软服务！", ["customer_name", "issue_summary"]),
    ("技术", "系统维护通知", "尊敬的{customer_name}，您好！为提升服务质量，我们计划于近期进行系统维护升级。\n\n维护时间：凌晨 2:00 - 6:00\n影响范围：{issue_summary}相关功能可能暂时不可用\n建议：请您提前保存重要数据\n\n维护完成后服务将自动恢复。如有紧急需求，请联系技术支持热线。", ["customer_name", "issue_summary"]),
    ("通用", "补充信息请求", "尊敬的{customer_name}，您好！感谢您提供的信息。为进一步排查{issue_summary}问题，我们还需要确认以下几点：\n1. 问题发生的具体时间和频率\n2. 您使用的设备和浏览器版本\n3. 是否有相关的截图或错误提示\n\n请尽可能提供以上信息，这将帮助我们更快地为您解决问题。", ["customer_name", "issue_summary"]),
]

async def main():
    async with async_session_factory() as db:
        # Get cs_staff user
        result = await db.execute(select(User).where(User.username == "cs_staff"))
        cs = result.scalar_one_or_none()
        if not cs:
            print("ERROR: cs_staff not found - run seed first!")
            return

        # Check existing templates to avoid duplicates
        result = await db.execute(select(ReplyTemplate.title))
        existing = set(r[0] for r in result.all())

        added = 0
        skipped = 0
        for cat, title, content, vars_ in EXTRA_TEMPLATES:
            if title in existing:
                skipped += 1
                continue
            db.add(ReplyTemplate(
                category=cat, title=title, content=content,
                variables=vars_, created_by=cs.id
            ))
            added += 1
            print(f"  [+] {title} [{cat}]")

        await db.commit()
        print(f"\nResult: {added} added, {skipped} skipped (already exist)")

        # Show all templates
        result = await db.execute(
            select(ReplyTemplate).order_by(ReplyTemplate.category, ReplyTemplate.title)
        )
        all_tpls = result.scalars().all()
        print(f"\nAll templates ({len(all_tpls)}):")
        for t in all_tpls:
            vars_ = ", ".join(t.variables) if t.variables else "none"
            print(f"  [{t.category}] {t.title}  vars=({vars_})  used={t.usage_count}x")

asyncio.run(main())
