# 东软智慧商务AI助手平台 — API 接口文档

> Base URL: `http://localhost:8000/api/v1`

---

## 认证

所有接口（除登录注册外）需在 Header 携带 JWT Token：

```
Authorization: Bearer <access_token>
```

### POST /auth/login
登录获取 Token

| 参数 | 类型 | 必填 |
|------|------|------|
| username | string | ✅ |
| password | string | ✅ |

### POST /auth/register
注册新用户

| 参数 | 类型 | 必填 |
|------|------|------|
| username | string | ✅ |
| password | string | ✅ |
| email | string | ✅ |
| full_name | string | ✅ |
| role | string | ✅ (enterprise/customer_service/decision_maker) |

---

## AI 对话

### POST /conversations
创建新对话

### GET /conversations
获取对话列表（分页）

### POST /conversations/{id}/messages
发送消息，SSE 流式返回 AI 回复

### GET /conversations/{id}/messages
获取对话消息记录

---

## 工单管理

### POST /tickets
创建工单（自动触发 AI 分类）

| 参数 | 类型 | 必填 |
|------|------|------|
| subject | string | ✅ |
| description | string | ✅ |
| priority | string | low/medium/high/urgent |

### GET /tickets
工单列表（支持筛选/搜索/排序）

参数：`page`, `page_size`, `status`, `priority`, `category`, `search`, `sort_by`, `sort_order`

### GET /tickets/{id}
工单详情

### PUT /tickets/{id}
更新工单（管理员/客服）

### POST /tickets/{id}/messages
添加工单消息

### GET /tickets/{id}/messages
获取工单对话

### POST /tickets/{id}/classify
手动触发 AI 分类（管理员/客服）

### POST /tickets/{id}/suggest-reply
AI 建议回复 — 按分类匹配差异化模板（管理员/客服）

### POST /tickets/{id}/resolve
解决并关闭工单（管理员/客服）

| 参数 | 类型 | 必填 |
|------|------|------|
| final_reply | string | ✅ |
| satisfaction_rating | int | 1-5 |
| satisfaction_comment | string | 选填 |

### POST /tickets/{id}/rate
客户评价已解决工单（工单所属用户）

| 参数 | 类型 | 必填 |
|------|------|------|
| rating | int | ✅ 1-5 |
| comment | string | 选填 |

---

## 回复模板

### GET /templates
模板列表（支持 `category` 筛选、`include_inactive` 查看已禁用）

### POST /templates
创建模板

### PUT /templates/{id}
更新模板

### POST /templates/{id}/use
使用模板（usage_count +1）

### GET /templates/{id}/render?ticket_id=xxx
渲染模板变量（根据工单上下文替换 `{customer_name}` 等占位符）

---

## 知识库

### POST /knowledge/documents/upload
上传文档（PDF/Word/TXT/Markdown/CSV），自动分段 + 向量化索引

### GET /knowledge/documents
文档列表

### GET /knowledge/query?q=xxx
知识库问答（RAG 检索增强）

### POST /knowledge/faqs
创建 FAQ

### GET /knowledge/faqs
FAQ 列表

### PUT /knowledge/faqs/{id}
更新 FAQ

### DELETE /knowledge/faqs/{id}
删除 FAQ

---

## 语音

### POST /voice/speech-to-text
上传音频文件，返回识别文本（multipart/form-data）

### POST /voice/text-to-speech
文字转语音，返回音频流

| 参数 | 类型 | 必填 |
|------|------|------|
| text | string | ✅ |
| voice | string | 选填 |
| rate | string | 选填 |

---

## 数据大屏

### GET /dashboard/overview
概览统计（咨询量/工单数/解决率/满意度）

### GET /dashboard/categories
问题分类分布（从工单表实时统计）

### GET /dashboard/satisfaction?days=7
满意度趋势（从真实评分统计）

### GET /dashboard/volume?days=7
咨询量/工单量趋势

### GET /dashboard/insights
AI 智能洞察卡片

### GET /dashboard/hot-topics
热门问题分类

### GET /dashboard/realtime
实时指标（活跃用户/待处理工单/AI 响应率）

---

## 管理员

### GET /admin/users
用户列表

### POST /admin/users
创建用户

### PUT /admin/users/{id}
更新用户

### POST /admin/users/{id}/reset-password
重置密码

### GET /admin/conversations
查看所有对话记录

### POST /admin/reports/generate
生成 AI 分析报告

### GET /admin/ai/configs
AI 配置

---

## Agent 智能体

### POST /agent/single/chat
单 Agent 对话（真实 token 流式）

### POST /agent/multi/analyze
多 Agent 分析（分类→检索→回复→质检）
