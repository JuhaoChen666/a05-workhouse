# Phase 2 本地实现及待验收交接 — Refs #1

## 当前结论

P2 业务实现已在 `feat/resume-phase2-experience-api` 完成，基于 master `d24f5a38552af0b72ab20cd7676290ab6f7f0a08`（合并 PR #3/P1）。**真实 MySQL 集成验收尚未执行，不能认定 P2 已完成完整验收。** 不关闭整个 Issue #1。

当前项目为 `H:\Code\program\2026外包\a05_plus`。只修改任务相关后端、迁移、测试和文档，保留用户未跟踪的 P2 交接提示词及 P1 根目录计划文件。原 P1 分支/master 保留，无强制回退、清理或生产数据变更。

## 交付实现

- 真实 Spring-compatible Bearer JWT 校验 dependency；显式数据库配置；可信 owner 贯穿经历、草稿、源文件和确认。
- 五类经历 CRUD、数据库分页/分类/标签/关键词/归档组合筛选、完整替换编辑、归档/解除归档、单项和批量排序、revision 冲突及条件删除。
- 手工结构化批量入库，严格五类输入，全批事务与字段定位错误；来源不能由客户端伪造。
- 上传文本型 PDF 或选择同 owner 旧 PDF，逐页提取、明确区分图片/无文本、加密、损坏/解析失败，保留来源。
- 独立 PDF AI HTTP 适配器，合法草稿/缺字段问题/页码和原文片段校验，未复用 Markdown 优化业务；真实 AI 请求尚未执行。
- 持久批次/条目、修正/删除、显式确认、确认请求摘要及不可变业务回执、整批创建、重复/并发确认协调、失败重试及中断恢复。
- 7 天草稿过期、取消、来源引用保护、默认 dry-run 的有界文件维护入口；P1 文档清理纳入持久批次保护。未启动生产维护调度。
- 同一套 P2 路由已注册到原 main.py，并提供无需面试模型初始化的独立 P2 app。真实 ASGI 单元验证使用该生产路由组件，未运行原 main.py 的完整面试/旧 AI 生命周期。

详细 [接口/筛选/错误/状态及幂等说明](resume_phase2_api_contracts.md)。

## 文件与运行接入

| 位置 | 用途 |
| --- | --- |
| app/api/experience_dependencies.py | JWT、延迟 DB/文件/AI dependencies |
| app/api/experience_routes.py / experience_import_routes.py | 经历管理与 PDF 草稿 API |
| app/api/experience_http.py / experience_body_limit.py | 路由局部错误转换与 P2 请求大小限制 |
| app/api/experience_app.py / main.py | 共同路由注册及轻量 P2 app |
| app/models/experience_api_contracts.py | 严格公开请求/分页契约 |
| app/models/experience_import_schema.py / experience_import_models.py | 同 Base 两表定义与模型 |
| app/infrastructure/mapper/experience_mapper.py | SQL 分页/JSON 筛选及 CAS 操作扩展 |
| app/services/pdf_experience_extractor.py | pypdf、AI HTTP 适配器及来源/草稿验证 |
| app/services/experience_import_service.py | 持久状态、用户修正和确认事务 |
| app/infrastructure/experience_import_cleanup.py / private_resume_assets.py | 有界来源维护和 P1 引用保护 |
| alembic/versions/phase2_experience_001.py | 冻结的 P2 增量迁移 |
| tests/test_phase2_boundaries.py / test_phase2_mysql.py | 实际认证/PDF/适配器及待执行 MySQL/ASGI 验收 |
| scripts/run_phase2_checks.py | 使用环境或本机掩码凭据的随机 schema 回归入口 |

环境最低配置：运行时显式 DATABASE_URL、RESUME_JWT_SECRET、固定签名算法；PDF 抽取实际 AI 需要 DEEPSEEK_API_KEY。可选 RESUME_PRIVATE_ASSET_ROOT/RESUME_AI_BASE_URL/RESUME_AI_MODEL。不会把 .env 的旧数据库默认值作为 P2 未配置回退方案。

`requirements-phase2.txt` 使用存储依赖和最小 FastAPI/httpx/JWT/PDF/运行依赖，测试额外使用 reportlab 生成真实 PDF 样本；只安装到项目 .venv，没有重装全量音视频/模型依赖。

## 增量迁移与回退影响

head 为 `phase2_experience_001`，down_revision 为 P1 的 `phase1_storage_002`，复用版本表 `resume_phase1_alembic_version`。只新增 `experience_import_batches`/`experience_import_drafts`，含 owner 约束、组合 FK、JSON/status/receipt CHECK 与列表/维护索引；source_resume_id 在线反射旧 BIGINT 类型，保留 unsigned 兼容。

001/002 原样保留；P2 迁移包含冻结自身 schema，不导入可变业务 ORM。Alembic env 纳入两张 P2 表的元数据范围。未对用户任何现有 schema 执行在线迁移。

下面仅说明授权环境中的迁移入口，没有在业务数据库实际执行：

```powershell
# 在 FastAPI-Backend；RESUME_DATABASE_URL 必须安全指向明确授权环境。
python -m alembic -c alembic.ini upgrade head --sql
python -m alembic -c alembic.ini upgrade head
python -m alembic -c alembic.ini current
```

离线 SQL 默认按 signed BIGINT 输出，执行前需按真实旧 resumes.id 的 signedness 核对；在线迁移负责反射实际定义。MySQL DDL 隐式提交，部分失败需核对表/版本状态，不能自动 DROP 重试。

降级到 P1 会 DROP 两张 P2 表，丢失草稿和确认幂等回执；不删正式 experience_items、P1 快照或文件。正式经历可能保留 source_locator.import_id 等不可再查询的历史关联。生产回退需单独授权并核实备份，先停用 P2 写入口并保留来源/回执，再考虑应用和 schema 回退；没有实际执行在线降级，也没有创建或宣称任何备份。

## 本轮验证

已通过真实认证/ASGI 边界、真实文本/图片/损坏/加密 PDF、非法/未知 AI 输出、来源片段校验、缺字段保留、AI HTTP 适配器确定性传输及 P1 单元/离线迁移边界。

最终完整当前可用回归：**84 passed、52 skipped、4.62s**，包括 P1 47 项单元和 P2 37 项认证/PDF/HTTP 适配器边界。跳过为 P1 31 项 + P2 21 项实际 MySQL 测试，全部因为缺少显式 RESUME_TEST_MYSQL_URL。历史 P1 的 78 passed/0 skipped 不计为本轮通过。

定向 compileall、P1/P2 离线迁移 SQL 检查、git diff --check 通过。P1 001/002 与基线 diff 为空。P1 表数回归保留并扩展为精确九表名单，未删除测试或减少必要校验。

**真实业务 HTTP/MySQL 21 项测试已编写、成功收集，但尚未运行**，内容包括五类完整 CRUD、JSON 分页组合查询、批量/排序/确认的数据库失败回滚、修正前无正式入库、重复/并发确认、跨 owner/跨批次隔离、来源编辑保留、旧 PDF FK 拒绝删除、取消/失效/中断恢复、P1 文档清理保护及部分文件失败重试、历史快照不变和增量迁移。

数据库服务 localhost3306 TCP 可连，但进程/User/Machine 环境均无测试连接。不读取业务密码或猜测凭据；等待本机环境或掩码交互配置。外部 AI 使用确定性替身，未验证实际 DeepSeek 模型质量或 API 可用性。

## 继续真实验收

用户可以从项目根目录在本机终端运行（用户名和密码只在终端掩码输入，不要粘贴到聊天）：

```powershell
.\.venv\Scripts\python.exe FastAPI-Backend/scripts/run_phase2_checks.py --mysql
```

已安全提供 RESUME_TEST_MYSQL_URL 时可直接运行同脚本（不加 --mysql）。脚本只将凭据放进测试子进程环境，不写凭据文件/日志/命令行。夹具 CREATE 随机 `resume_p1_restart_test_<16hex>` schema，并只 DROP 自己刚创建的 schema；连接 URL 原来的库不迁移/清空。测试临时路径是每次 UUID 命名的项目 .phase2-local 子目录。

需要实际运行全部 P1/P2 数据库测试，修复真实发现的问题，再补齐结果和本地提交。不能把跳过测试、仅代码检查或确定性 AI 替身称为完整生产验收。

## 后续范围及外部操作

没有 OCR、经历库前端页面、模板启用/编译校验、JD 改写/LaTeX 渲染编译、下载/历史迁移或生产发布。原模板和旧 Markdown 业务保持。

本轮没有 push、创建 PR、合并/自动合并或部署。新分支创建时跟踪 origin/master；后续推送需显式指向经用户授权的参与者 fork，不能直接 push origin 或绕过原仓库权限。提交使用 Refs #1；将来 PR 使用 Part of #1。

已建立本地阶段提交：5334893（认证/五类 API）和 aad9703（PDF 持久草稿/原子确认/来源保护）。测试与文档提交随后建立，完整日志以 git log 为准。
