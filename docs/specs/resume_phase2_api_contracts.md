# Phase 2 个人经历库后端接口 — Refs #1

本文对应 `feat/resume-phase2-experience-api`，基于已合并 P1 的 master `d24f5a3`。
实现范围是 Issue #1 的 P2；数据库验收状态以交接报告为准，不把设计或测试收集成功当作业务验收通过。

## 认证与基础规则

所有 P2 接口要求 `Authorization: Bearer <Spring-compatible JWT>`。服务端验证签名、有效期、issued-at 和 id/username/roleId；id 必须为正整数。`RESUME_JWT_SECRET` 使用 Spring 签名密钥的相同 UTF-8 字节，`RESUME_JWT_ALGORITHM` 固定 HS256（默认），或由服务器显式配置 HS384/HS512；不能由 token 指定算法。

密钥只通过服务器环境提供，不写入本说明、源码或日志。不存在/过短/不支持的算法配置返回 503。运行时必须显式设置 `DATABASE_URL=mysql+aiomysql://.../<database>`；缺少配置不会回退到旧业务库。迁移变量为 `RESUME_DATABASE_URL`，测试变量为 `RESUME_TEST_MYSQL_URL`，三者用途独立。

body 中 `user_id`/ID/时间戳等服务器字段会被严格输入契约拒绝。query 中 `user_id` 和 `X-User-ID` 不决定 owner。跨 owner 和不存在资源均为 404。公开内容只支持手工来源，不能指定 PDF_IMPORT 或来源定位；只有 PDF 确认流程能绑定 PDF 来源。

接口采用 snake_case，创建/编辑输入仍为分类专属字段扁平结构；经历响应专属字段位于 `attributes`。所有返回时间为 UTC-naive ISO 时间。年月为 YYYY-MM，只有 end_date 可用 present，null 表示未提供。

## 经历接口

| 方法及路径 | 输入 | 结果 |
| --- | --- | --- |
| POST /api/experiences | 一条五类严格内容 | 201，完整经历，初始 revision=1 |
| GET /api/experiences/{id} | UUID | 200，经历详情 |
| GET /api/experiences | 见筛选规则 | 200，items/page/page_size/total |
| PUT /api/experiences/{id} | expected_revision + item | 200，完整替换后经历；分类不可变，已有 PDF 来源由服务器保留 |
| PATCH /api/experiences/{id}/archive | expected_revision + is_archived | 200，归档或解除归档后经历 |
| PATCH /api/experiences/{id}/order | expected_revision + sort_order | 200，排序后经历 |
| DELETE /api/experiences/{id} | query expected_revision | 204，删除当前库记录；不删除历史快照或来源文件 |
| POST /api/experiences/batch | items（1–100 条手工内容） | 201，全部新经历列表；整批事务 |
| PUT /api/experiences/order | items（1–100 条 id/expected_revision/sort_order） | 200，按请求顺序返回新经历；整批事务，拒绝重复 ID |

编辑使用 PUT 完整替换公共及分类内容，没有通用 PATCH 字段合并。调用方需提交完整所需字段（包括归档/排序等）；来源元数据不属于可编辑内容。每次成功编辑/归档/排序都比较并递增 revision；即使目标状态相同也递增。删除比较 revision 后删除记录，旧版本写操作返回 409。

手工创建示例：

```json
{"type":"SKILL","title":"后端开发","category":"后端开发","skills":["Python","FastAPI"],"tags":["Python"]}
```

编辑示例：

```json
{"expected_revision":1,"item":{"type":"SKILL","title":"后端开发","category":"后端开发","skills":["Python","FastAPI","MySQL"],"tags":["Python"]}}
```

## 分页和组合筛选

- page 默认 1，范围 1–1000000；page_size 默认 20，范围 1–100。
- type 是 CERTIFICATE/COMPETITION_AWARD/PROJECT/WORK/SKILL 之一，精确匹配。
- archive 为 active（默认，仅未归档）/archived/all。
- tag 可重复，例如 `tag=Python&tag=SQL`，必须全部匹配（AND），按 JSON 字符串精确匹配、区分大小写。首尾空白去除、重复去除；最多 50 个，每个 1–100 字符。
- keyword 最多 200 字符，首尾空白去除，空关键词不增加过滤；按字面子串匹配，%/_/! 均转义，不成为客户端通配符。
- 关键词字段：title、tags，以及 authority/certificate_no/category/description/award_level/organization/rank/role/project_url/tech_stack/bullets/department/city/skills/proficiency 的文本值。不会搜索 owner/ID/日期/来源元数据。
- 关键词统一使用 utf8mb4_bin 比较，区分大小写/重音；title 和 JSON_SEARCH 搜索参数均显式指定该 collation。真实 MySQL 验收尚未完成，不宣称已实测。
- 各维度组合为 AND；关键词在其字段范围内为 OR。count 和分页均在数据库执行；稳定顺序 sort_order ASC、id ASC。
- 超出末页返回空 items，total 保持真实总数。人工标签写入同样去空白/去重，丢弃空标签；标签筛选的空值视为 422。

## PDF 草稿接口

| 方法及路径 | 输入 | 结果 |
| --- | --- | --- |
| POST /api/experience-imports/upload | multipart file，.pdf | 201，持久草稿批次；处理失败返回错误及 import_id |
| POST /api/experience-imports/existing | source_resume_id | 201，同 owner 旧 PDF 的草稿批次 |
| GET /api/experience-imports/{id} | UUID | 批次状态、问题、条目、来源摘要、过期时间、确认结果 |
| PUT /api/experience-imports/{id}/items/{draft_id} | expected_revision + content | 修正后的条目和问题；允许保持待修正，不入正式库 |
| DELETE /api/experience-imports/{id}/items/{draft_id} | query expected_revision | 204，删除不需要的草稿条目 |
| POST /api/experience-imports/{id}/confirm | items：id + expected_revision | 确认回执，包含生成经历 ID |
| POST /api/experience-imports/{id}/retry | 无 body | 重试未过期 FAILED 批次的 PDF/AI 提取 |
| POST /api/experience-imports/{id}/cancel | 无 body | CANCELLED 状态；清除草稿和提取文本，文件由独立维护核对 |

支持新 PDF 上传和同 owner 旧 PDF。旧 PDF 必须位于受控 `FastAPI-Backend/data/resumes` 路径中，不允许数据库路径指向任意外部文件，不沿符号链接/联接读取。旧 PDF 复制为私有来源文件，批次保留旧 resume 引用，外键保护旧删除接口。

请求体最多 17 MiB（包括 multipart 元数据），PDF 本体最多 16 MiB、50 页、100000 字符；单页内容流最多 8 MiB。草稿最多 100 条，单条内容序列化最多 32000 字符。pypdf 在线程中提取文本，AI 调用在数据库事务之外，HTTP/总体 AI 调用有超时且响应读取限制 1 MiB。

PDF 独立错误码：PDF_SIZE/PDF_PAGE_LIMIT/PDF_CONTENT_LIMIT/PDF_TEXT_LIMIT、PDF_DAMAGED、PDF_ENCRYPTED、PDF_EXTRACTION_FAILED、PDF_OCR_UNSUPPORTED。图片型或没有可用文本时明确提示不支持 OCR，不返回成功空草稿。加密文件要求用户提供未加密副本。

AI 输出要求 JSON items，每条包含 content/page/snippet；未知分类、非法 JSON、空条目和不属于来源页的文本片段有可解释错误。必填字段缺失或不确定日期保留原草稿和 issues，不补造事实。定位保留页码、来源文本片段、导入/条目 ID、私有文件摘要和 `unverified_ai_extraction=true`；用户确认仅表示用户确认入库，不是事实认证。

## 状态、幂等与生命周期

批次持久化为 PROCESSING→READY/FAILED；READY 可以确认或取消；未确认 7 天后失效为 EXPIRED。所有条目可在 READY 状态下修正/删除；修正递增条目 revision。GET 会提交过期/中断状态恢复，超过 5 分钟未更新的 PROCESSING 被标记为 FAILED/PROCESSING_INTERRUPTED，可显式重试。没有依赖进程全局字典或未受管控后台任务。

确认请求示例：

```json
{"items":[{"id":"<draft UUID>","expected_revision":2}]}
```

服务锁定批次，重新校验所有选中条目、其 revision、owner 和来源文件，然后在一个事务内创建全部经历并保存确认回执。缺少字段或任何写入失败整批回滚，不出现半批入库。公开来源字段不能覆盖服务器定位。

确认请求按草稿 ID 排序后对 ID/revision 生成摘要。相同选择和版本的重试（包括改变请求条目顺序）返回相同回执，不再创建经历；已确认批次的不同选择或版本返回 409。并发请求通过数据库行锁和私有资产锁协调。已确认批次不能再编辑/删除草稿、取消或重试提取。回执中的经历之后被编辑或删除，仍返回原始 ID，不重新创建。

确认回执结构：

```json
{"import_id":"<batch UUID>","status":"CONFIRMED","items":[{"draft_id":"<draft UUID>","experience_id":"<experience UUID>"}]}
```

取消清除草稿条目和提取文本，保留批次状态供核对；失败且未过期时保留源文件供重试。过期/取消/已确认批次的文件释放由 `cleanup_imports` 维护入口执行，默认 dry-run，没有生产定时任务或公开删除维护接口。维护重新检查所有经历（含归档）、存活/未到保留期文档、活跃生成任务及其他批次引用，受保护文件不删。只有实际文件释放后才提交完成标记、解除旧 PDF 引用并清除草稿文本；确认回执保持可核对。

P1 文档清理已补齐持久导入批次来源保护，取消/失败/过期批次在核对释放前也保留来源。文件删除或提交不确定保留可重试记录，未知孤儿文件不自动扫描删除。

## 错误格式

```json
{"detail":{"code":"REVISION_CONFLICT","message":"Resource has changed"}}
```

| HTTP | 语义 |
| --- | --- |
| 401 | 缺少、伪造、过期或格式无效的认证 |
| 404 | 不存在或不属于当前 owner（经历/草稿/来源相同规则） |
| 409 | revision/状态冲突、不同确认摘要、已失效、来源文件不可用 |
| 413 | 请求/PDF 大小、页数或文本限额 |
| 422 | 字段/分类/年月输入错误、待修正草稿、PDF 业务解析错误 |
| 502/504 | 外部 AI 非法结果/失败或超时 |
| 503 | 认证/数据库/AI 缺少配置，或数据库操作失败 |

INVALID_INPUT/DRAFT_NEEDS_CORRECTION 提供字段路径或 draft_id 问题列表；底层数据库 SQL、连接串或异常不直接返回客户端。数据库提交确认不确定时，应读取经历/批次状态后重试，不能把通用失败理解为数据库一定没有提交。

## 开发运行及参考

项目环境安装最小依赖 `requirements-phase2.txt`；测试额外安装 `requirements-phase2-test.txt`。在 FastAPI-Backend 目录可以运行 `python -m uvicorn app.api.experience_app:app --host 127.0.0.1 --port 8000`，这是不加载面试模型的 P2 app。原 main.py 同时注册相同 P2 路由，原有面试/Markdown 链路保持。

实现参考官方 [FastAPI JWT dependency](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)、[PyJWT API](https://pyjwt.readthedocs.io/en/stable/api.html)、[pypdf 文本提取](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)、[MySQL JSON 查询](https://dev.mysql.com/doc/refman/8.4/en/json-search-functions.html)。库行为以本轮安装版本和真实验证为准。
