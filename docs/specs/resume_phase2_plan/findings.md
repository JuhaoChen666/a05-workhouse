# P2 基线核实 — Refs #1

- 已读取 GitHub Issue #1：P2 包括五类 CRUD、分页/类型/标签/关键词筛选、归档、排序、批量导入及 PDF→AI 草稿→用户确认；唯一 owner 依据为服务端认证身份。
- 远端 master 当前为 d24f5a38552af0b72ab20cd7676290ab6f7f0a08，提交说明合并 PR #3；git 祖先检查确认包含指定 P1 HEAD。
- 原本本地 master 是 aff3e2f8，origin/master 缓存是 b7bf53f；已 fetch 后从最新 origin/master 创建 P2 分支，未修改本地 master 或原 P1 分支。
- P1 mapper 有创建/读取/完整列表/完整替换编辑/归档和 CAS；缺删除、分页和组合筛选，归档只支持设为 true。应补齐数据库方法，不能把全量 list 包装为分页。
- P1 历史快照是深拷贝内容；P2 操作不能重写快照。
- Spring 使用 Bearer JWT，验证后取 id/username/roleId；新增 FastAPI 认证需验证兼容签名和期限，从环境获取必要密钥，文档/代码不复制凭据。
- FastAPI main 导入多个旧路由，lifespan 初始化面试模型；PDF 工具吞异常返回 None；旧 AI 对象在模块导入时构造。P2 应采用可测试适配器，控制副作用。
- P1 私有文件清理保护经历、历史文档和活跃生成任务；新增持久草稿需要扩展来源保护。
- 工作区开始时仅有未跟踪 docs/specs/resume_phase2_ai_handoff_prompt.md；保留原文件及现有 P1 根目录计划文件。
- 方案详细内容见同目录 task_plan.md；所有尚未实施内容均为拟定设计。

- 按用户后续指示，本地 master 已快进至 d24f5a3，随后开发切回 P2 分支；计划前述本地 master 未更新是方案初次核实时点的历史信息。
- localhost:3306 TCP 已确认可连接，但工具进程缺少 RESUME_TEST_MYSQL_URL；未读取业务配置中的密码或猜测认证，已请求本机安全提供测试连接。
- 第一轮 JWT/PDF/P1 单元检查 74 passed，1.43s。实际 ASGI 请求经过真实认证 dependency；外部 AI 尚未调用。
- P2 新增两表，P1 全量 head 迁移表数从含版本表的 5 变为 7；原迁移回归改为断言精确九表（含旧两表和版本表），不减少校验。

- 最终当前可用全套回归 84 passed、52 skipped、4.62s（P1 单元 47 + P2 单元 37；P1 MySQL 31 + P2 MySQL 21 均等待测试连接）。定向 compileall、离线迁移检查及 staged diff check 通过。
- 实际关键词契约明确为所有字段 utf8mb4_bin 区分大小写/重音；JSON_SEARCH 参数和 title 都显式指定 collation，标签为 JSON 字符串精确 all-of。该 SQL 行为仍待真实 MySQL 验证。
- 本地阶段提交 5334893 和 aad9703 已完成，无 push/PR/合并/部署。
