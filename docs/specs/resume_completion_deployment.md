# 简历闭环开发与部署说明

关联 [Issue #1](https://github.com/JuhaoChen666/a05-workhouse/issues/1)。本轮仅准备代码、迁移和本地验证，没有推送、PR、合并或生产部署。

## 配置与启动

API、生成 worker、模板初始化和保留期维护均使用显式 `DATABASE_URL=mysql+aiomysql://.../目标数据库`。不得依赖旧面试模块的默认数据库。迁移兼容原 `RESUME_DATABASE_URL`；若它与 `DATABASE_URL` 同时存在，必须指向同一数据库，否则拒绝执行。生产配置和密码由运行环境注入，不放入仓库或命令行日志。

必需配置：

| 变量 | 作用 |
| --- | --- |
| `DATABASE_URL` | API/worker/初始化/维护共享的显式 MySQL 数据库 |
| `RESUME_PRIVATE_ASSET_ROOT` | 共享的绝对私有文件根目录；不得放入公开静态目录 |
| `RESUME_JWT_SECRET` / `RESUME_JWT_ALGORITHM` | 与 Spring 登录签名兼容的认证配置，沿用 P2 校验 |
| `RESUME_FRONTEND_ORIGINS` | 简历专用 API 允许的前端来源，逗号分隔；例如开发来源 `http://127.0.0.1:5173` |
| `RESUME_LATEX_IMAGE` | 已审查并预先安装的不可变镜像 ID `sha256:…` 或 `仓库@sha256:…` |
| `RESUME_COMPILE_WORK_ROOT` | worker 所在主机上已准备好的绝对临时编译目录；拒绝根目录及重解析链接 |
| `LATEX_COMPILE_CONCURRENCY` | 同数据库 worker 全局执行上限，1–16，默认 2；各 worker 必须保持一致 |

AI 使用 `DEEPSEEK_API_KEY`、`RESUME_AI_BASE_URL`（默认 DeepSeek 官方接口）、`RESUME_AI_MODEL`（默认 `deepseek-chat`）。PDF/Markdown 抽取与 JD 规划使用同一配置。无 Key 时导入批次明确失败并可重试；AI 生成明确标记 `DEGRADED`，按关键词选择并保留原文。手工生成完全不调用 AI。

前端 `VITE_INTERVIEW_API_ORIGIN` 指向上述 API，`VITE_API_ORIGIN` 保持现有登录和岗位服务配置。岗位 ID 由 `JOB_SOURCE_BASE_URL` 对应的岗位详情服务解析；无该服务时可以粘贴 JD。

在后端工作目录执行以下入口；这些是部署操作说明，本轮没有在业务数据库执行它们：

```text
python -m alembic upgrade head
python -m app.infrastructure.resume_template_store --version 1.2.0
python -m uvicorn app.api.resume_app:app --host 127.0.0.1 --port 8000
python -m app.services.resume_worker
```

`app.api.resume_app` 是无需初始化旧面试 AI/RAG 的简历专用入口。完整 `main:app` 也注册新文档接口，但其既有面试依赖和启动条件另行保留。API 只提交持久 `PENDING` 任务，不在 `BackgroundTasks` 中编译，必须部署 worker 才会推进任务。`python -m app.services.resume_worker --once` 适合受控单轮运行。

已有数据库只初始化新 1.2.0 版本，避免不同平台的旧模板换行字节导致不可变版本冲突；全新数据库可省略 `--version` 初始化所有版本。新版本通过 scoped `.gitattributes -text` 保持跨平台原始字节，未规范化或覆盖旧版本。发现相同版本内容不同仍拒绝写入。

后端轻量依赖见 `requirements-phase2.txt`，新增 Jinja2。本轮依赖安装只涉及项目 `.venv` 与前端 `node_modules`。前端可在审查安装入口后使用 `npm ci --ignore-scripts --no-audit --no-fund`；现有 `@vue-office/pdf` 必须选择 Vue 3 入口。本轮检查了它的 `lib/script/postinstall.js` 和 `utils.js`，仅复制新安装包内部文件，再执行 `node node_modules/@vue-office/pdf/lib/script/postinstall.js`，随后 `npm run build`。不执行未检查的其它安装钩子。

## 隔离编译前置条件

构建上下文为 `FastAPI-Backend/deploy/latex`，提供 XeLaTeX、Noto CJK 字体和固定 `compile_resume.py`。由运维审查、构建并预装镜像后，将不可变 ID 注入 worker。worker 不自动拉取镜像，不接受用户指定可执行命令。

目标是 Linux worker 与能访问同一临时文件系统的 Linux Docker daemon。Windows 仅可完成开发和接口测试；使用 Docker Desktop Linux 容器及目录映射时仍须实测。直接指向远程 Linux daemon 不能自动访问 Windows 的 `H:`/临时路径；应将 worker 部署在该 Linux 主机。不得为了调通而关闭防火墙、沙箱、seccomp 或放宽系统权限。

启动前检查 daemon 报告的内存、swap、CPU quota、PID 限制、cgroup driver 和 seccomp；缺少能力即 `SANDBOX_UNAVAILABLE`。容器非 root、只读根文件系统、无网络、移除所有 capabilities、禁止新增权限；仅挂载本任务只读输入 JSON，工作目录与 `/tmp` 使用受限 tmpfs，内存 512 MiB、1 CPU、32 PID。编译进程只得到固定最小环境，不继承数据库密码和 AI Key。上述 Docker 限制的参数依据 [Docker run 文档](https://docs.docker.com/engine/containers/run/)；rootless 的资源控制能力仍取决于目标主机，见 [rootless 文档](https://docs.docker.com/engine/security/rootless/#limiting-resources)。参数和能力检查不能替代真实目标环境验收。

编译子进程 30 秒超时，宿主 Docker 调用 40 秒超时，输入源码最大 2 MiB、资源总量最大 32 MiB、PDF 最大 12 MiB、返回流最大 18 MiB。超时仅清理 cidfile 指向且标签匹配本任务的容器，标签不匹配拒绝删除。仅返回编译错误类型和行号，不返回完整编译日志或私有内容。无隔离环境时不会回退宿主 XeLaTeX。

## 业务和兼容语义

- 目标页数表示 PDF 页数上限。成功编译后用 pypdf 读取真实 PDF；超过上限为 `PAGE_LIMIT_EXCEEDED`，不保存成功文档，建议减少经历、提高上限或更换模板。
- 语言控制规划请求与模板标题；事实正文保留来源语言，避免未验证翻译改变事实。界面明确显示该策略。
- AI 只能选择冻结的允许经历；原始 bullet 必须逐字存在于相应经历。伪造 ID、原文、重复来源和新增数字拒绝。所有无法验证的语义改写保留原文，并记录数量和策略，不以来源 ID 代替事实校验。
- 新增 `billryan-classic`、`modern-twocol` **1.2.0 / 协议 1.1**，实现模块顺序和中英标题。原 1.0/1.1 模板文件未改写。历史 1.1 支持原语言和固定顺序；不支持的选项明确拒绝，已有 PDF/源码读取不受影响。
- 草稿修正保存后才可确认；服务端保存来源信息、revision 和确认回执。重复相同确认不重复入库，不同确认/版本冲突明确返回错误。图像 PDF 明确拒绝 OCR。
- 文档命名、复制、删除、快照和下载使用 **document_id**。复制可共享生成任务和输出文件，删除原文档不会使有效副本丢失文件。
- 再次编辑使用原冻结 JD、经历、模板、个人/教育信息和选项，允许调整 JD、个人/教育信息及原快照内的经历选择，创建新任务/文档。它不替换原经历事实；需要修订经历事实时在经历库修改后新建生成任务。
- 历史 Markdown 显式标识 `format=markdown`，按 owner 只读。主动重新生成先复制原文到私有导入批次，经抽取、修正、确认后写入 `MARKDOWN_IMPORT` 经历，再选择 JD/模板生成。不会把 Markdown 当作新排版中间层，也不会覆盖原历史记录。

## 迁移、恢复和回退

新增迁移 `resume_runtime_001`，基于 `phase2_experience_001`，增加任务执行 token/结果 metadata、批次历史 Markdown 来源标识和导入观测计数，并扩展经历来源约束。原 P1/P2 迁移文件未改写，不改动旧 resumes/优化正文。仅在明确目标数据库由运维执行迁移；本轮真实数据库验证均使用随机测试 schema。

每个执行由独立 MySQL 连接持有任务锁和全局容量锁。不同 worker 无法重复领取同一任务；最终写入再次检查 token/状态，输出与文档同一私有文件事务提交。worker 崩溃释放连接锁，后续 worker 将遗留 `PROCESSING` 标成 `WORKER_INTERRUPTED`，用户明确重试；不会将中断任务假装成功，也不会读取变化后的经历替换冻结输入。

保留期维护默认 dry-run：

```text
python -m app.infrastructure.resume_maintenance --owner 71 --max-pages 10
```

这只报告候选计数。`--apply` 会删除符合保留期、未被经历/活跃文档/任务/导入批次引用的私有文件，必须由维护者按具体环境授权后执行；本轮没有在业务文件目录执行。每页 100 条，最多 100 页，使用 keyset 推进。

回退优先停止本部署的 worker 后回退应用代码，保留新增列和私有数据；旧应用不会理解新 Markdown 来源，须先限制相关写入入口。数据库降级会丢失新增运行结果与计数，存在 `MARKDOWN_IMPORT` 经历或历史导入批次时主动拒绝降级，避免丢失来源；不提供绕过保护的 SQL。历史文档/PDF/源码继续保留。本轮未建立或核实生产备份，因此不声称生产回退已实测或可自动恢复。

MySQL DDL 不是整体事务：生产迁移中断时须暂停写入，核对新增列、约束和版本表后再由维护者处理，不能对业务库盲目重复或清空重建。回退到 PR #6 旧代码前也须暂停旧生成/编译写入口，不能重新启用宿主编译作为降级方案。

## 监控和待验收

`GET /api/resume-generation/metrics` 需要真实 Bearer 身份，只返回当前用户的状态计数、完成任务平均耗时/失败率、失败错误类型、AI 成功/降级状态、生成重试总数、队列深度、最长未完成时长，以及导入 AI 调用/失败率和导入重试总数。worker INFO 日志记录任务 ID、耗时、状态、错误码、AI 状态和重试数，不记录 Key、连接 URL、完整经历或编译日志。

建议监控持续队列积压、长时间未完成任务、`SANDBOX_UNAVAILABLE`、`WORKER_INTERRUPTED`、编译超时和 AI 降级比例；阈值应由目标环境吞吐量实测后确定。本轮未部署监控平台。

真实 Docker 测试入口：设置可信镜像、临时目录和 `RUN_RESUME_DOCKER_INTEGRATION=1`，运行 `tests/test_resume_isolation_integration.py`。包含正常 PDF、绝对路径读取拒绝和超时；还需在目标主机补做内存/PID、网络、并发、清理和中文字体的运行时验收。

真实 AI 当前没有环境；真实 Linux Docker/XeLaTeX 当前未提供；浏览器连接工具返回连接失败。故真实中文 PDF、版面视觉、资源/网络隔离和浏览器完整端到端均为发布前阻塞项，不能用替身测试或此前 PR 的人工成功记录替代。
