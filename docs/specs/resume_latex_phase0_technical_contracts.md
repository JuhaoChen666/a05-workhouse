# Phase 0：个人经历库与基于 LaTeX 的 JD 定制简历系统技术契约规范

> **关联 Issue**: [#1 feat: 建立个人经历库并重构为基于 LaTeX 的 JD 定制简历](https://github.com/JuhaoChen666/a05-workhouse/issues/1)  
> **所属阶段**: Phase 0（需求与技术契约）  
> **状态**: Accepted / Specification Frozen (Updated with 5 Experience Types)  
> **编写时间**: 2026-09-17  

---

## 1. 架构总览与背景

当前系统的简历优化链路主要依赖：
$$\text{PDF} \longrightarrow \text{文本提取} \longrightarrow \text{AI 输出 Markdown} \longrightarrow \text{Markdown 转 HTML/PDF}$$

此链路存在三大瓶颈：
1. **无法结构化复用**：不同岗位共用同一份扁平简历，过往证书、竞赛奖项、项目、工作经历以及专业技能无法原子化沉淀与按需编排；
2. **缺乏事实溯源**：AI 直接生成大段 Markdown，难以校验是否虚构内容，无法建立与用户原始经历条目的版本追溯关系；
3. **排版脆弱与分页不可控**：Markdown 转 HTML/PDF 容易出现跨页空白、段落割裂及中文版式不统一问题。

为彻底解决上述问题，系统升级为**以个人经历库为原子数据源、以 LaTeX 作为统一生成和排版中间层**的工业级流水线：

```
+----------------+      +---------------------+      +----------------+
|  原始简历 PDF  | ---> | 文本/结构化经历解析 | ---> |  用户确认入库  |
+----------------+      +---------------------+      +-------+--------+
                                                             |
                                                             v
+----------------+      +---------------------+      +----------------+
|  目标岗位 JD   | ---> | AI 结构化选择与改写 | <--- |   个人经历库   |
+----------------+      +----------+----------+      +----------------+
                                   |
                                   v
                        +---------------------+
                        |  确定性 LaTeX 渲染  | (Jinja2 模板 + 特殊字符转义)
                        +----------+----------+
                                   |
                                   v
                        +---------------------+
                        |  XeLaTeX 隔离编译   | (沙箱限制、超时控制、中文适配)
                        +----------+----------+
                                   |
                                   v
                        +---------------------+
                        | PDF 预览与源码导出  | (保存快照至简历库)
                        +---------------------+
```

---

## 2. 五类经历字段规范 (Experience Schemas)

经历按固定枚举分类扩展为五大类别：`CERTIFICATE`、`COMPETITION_AWARD`、`PROJECT`、`WORK`、`SKILL`。不同用户数据严格按认证身份 `user_id` 物理/逻辑隔离。

### 2.1 公共基础字段 (BaseExperienceItem)

所有经历条目均包含以下元数据：

| 字段名 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `id` | `VARCHAR(36)` | 是 | UUID 唯一标识 |
| `user_id` | `VARCHAR(64)` | 是 | 所属用户 ID（服务端鉴权注入，绝不信任前端传入） |
| `type` | `ENUM` | 是 | `CERTIFICATE` \| `COMPETITION_AWARD` \| `PROJECT` \| `WORK` \| `SKILL` |
| `title` | `VARCHAR(200)` | 是 | 经历主标题（如项目名、公司名、比赛名、证书名、技能分类名） |
| `start_date` | `VARCHAR(10)` | 否 | 开始日期，格式 `YYYY-MM` |
| `end_date` | `VARCHAR(10)` | 否 | 结束日期，格式 `YYYY-MM`，为空或 `"present"` 表示至今 |
| `tags` | `JSON / List[str]` | 否 | 技术标签 / 关键词列表（如 `["Go", "Kubernetes", "分布式"]`） |
| `is_archived`| `BOOLEAN` | 是 | 是否归档，默认 `false` |
| `created_at` | `TIMESTAMP` | 是 | 创建时间 |
| `updated_at` | `TIMESTAMP` | 是 | 更新时间 |

---

### 2.2 证书与知识产权 (CERTIFICATE)

用于沉淀软考、大厂认证、外语水平、专利与软件著作权。

```json
{
  "type": "CERTIFICATE",
  "title": "全国计算机技术与软件专业技术资格（系统架构设计师）",
  "authority": "人力资源和社会保障部、工业和信息化部",
  "issue_date": "2024-11",
  "certificate_no": "2024XXXXXXXX",
  "category": "职业资格",
  "description": "国家高级资格认证，具备大规模软件架构与分布式设计专业能力。"
}
```

- **扩展字段**：
  - `authority` (`VARCHAR(150)`, 可选)：颁发机构；
  - `issue_date` (`VARCHAR(10)`, 必填)：获得年月 `YYYY-MM`；
  - `certificate_no` (`VARCHAR(100)`, 可选)：证书编号或登记号；
  - `category` (`VARCHAR(50)`, 可选)：分类（如：资格认证、外语能力、发明专利、软著）。

---

### 2.3 比赛获奖与荣誉 (COMPETITION_AWARD)

用于沉淀国家级/省级高校学科竞赛、创新创业大赛、企业黑客松等。

```json
{
  "type": "COMPETITION_AWARD",
  "title": "第十六届全国大学生服务外包创新创业大赛",
  "award_level": "国家一等奖",
  "award_date": "2025-08",
  "organization": "中华人民共和国教育部、商务部",
  "rank": "全国第 3 名 (队长)",
  "description": "基于 AI Agent 的企业级智能工作台研发，负责后端微服务架构与分布式调度引擎。"
}
```

- **扩展字段**：
  - `award_level` (`VARCHAR(100)`, 必填)：奖项等级（如国家一等奖、省级金奖、优胜奖）；
  - `award_date` (`VARCHAR(10)`, 必填)：获奖年月 `YYYY-MM`；
  - `organization` (`VARCHAR(150)`, 可选)：主办单位；
  - `rank` (`VARCHAR(50)`, 可选)：具体名次或团队角色（如队长、核心开发者）。

---

### 2.4 项目经历 (PROJECT)

用于沉淀开源项目、商业落地项目、校企合作科研项目。

```json
{
  "type": "PROJECT",
  "title": "A05-Workhouse 智能求职工作台",
  "role": "后端架构与 AI 研发负责人",
  "start_date": "2025-03",
  "end_date": "present",
  "project_url": "https://github.com/JuhaoChen666/a05-workhouse",
  "tech_stack": ["FastAPI", "Spring Boot", "XeLaTeX", "Vue 3", "Redis"],
  "description": "基于大模型与 LaTeX 的多端协同简历智能生成与模拟面试系统。",
  "bullets": [
    "设计基于 XeLaTeX 的确定性简历编译沙箱，实现代码级转义与秒级异步 PDF 编译。",
    "实现针对岗位 JD 的经历自适应选择与改写机制，匹配准确率提升 60%。"
  ]
}
```

- **扩展字段**：
  - `role` (`VARCHAR(100)`, 必填)：担任角色；
  - `project_url` (`VARCHAR(255)`, 可选)：开源地址或演示地址；
  - `tech_stack` (`JSON / List[str]`, 可选)：使用的技术栈列表；
  - `bullets` (`JSON / List[str]`, 必填)：项目核心亮点与成果点（STAR 原则结构）。

---

### 2.5 工作与实习经历 (WORK)

用于沉淀企业实习、全职工作、课题组实验室工作。

```json
{
  "type": "WORK",
  "title": "某云计算互联网大厂",
  "department": "云原生基础架构部",
  "role": "云原生研发实习生",
  "city": "杭州",
  "start_date": "2024-06",
  "end_date": "2024-12",
  "bullets": [
    "参与 Kubernetes Operator 调度控制器开发，优化 Pod 冷启动拓扑亲和性，调度时延降低 25%。",
    "编写 Prometheus 告警规则与 Grafana 监控大盘，覆盖 300+ 节点集群的核心性能指标。"
  ]
}
```

- **扩展字段**：
  - `department` (`VARCHAR(100)`, 可选)：所在部门/业务线；
  - `role` (`VARCHAR(100)`, 必填)：职位角色；
  - `city` (`VARCHAR(50)`, 可选)：工作城市；
  - `bullets` (`JSON / List[str]`, 必填)：岗位核心产出与职责。

---

### 2.6 专业技能 (SKILL)

用于结构化归档技术人员在不同技术领域的专业技术栈清单与熟练度。例如：后端开发、前端工程、云原生与基础架构、数据分析与算法等。

```json
{
  "type": "SKILL",
  "title": "后端开发",
  "category": "后端技术栈",
  "skills": ["Go", "Python", "FastAPI", "Spring Boot", "MySQL", "Redis", "Kafka"],
  "proficiency": "精通",
  "description": "精通高并发服务治理、微服务RPC与分布式存储设计，拥有丰富海量数据处理经验。"
}
```

- **扩展字段**：
  - `category` (`VARCHAR(100)`, 必填)：技能方向名称（如：后端开发、前端工程、分布式中间件、AI/算法）；
  - `skills` (`JSON / List[str]`, 必填)：该技能方向包含的具体技术栈列表（如 `["Go", "Python", "Docker", "Redis"]`）；
  - `proficiency` (`VARCHAR(50)`, 可选)：掌握熟练度（如：精通、熟练、掌握、了解）；
  - `description` (`TEXT`, 可选)：补充说明或落地经验总结。

---

## 3. LaTeX 模板系统与模块占位符协议

系统强制使用 **Jinja2 模板引擎** + **确定性 LaTeX 转义过滤器**，支持将用户经历库中选中的专业技能原子渲染为 LaTeX 的技能清单或技能胶囊。

### 3.1 模板元数据规范 (Template Metadata)

每个内置或上传的 LaTeX 模板必须附带 `template.json` 清单：

```json
{
  "id": "tpl-billryan-classic",
  "name": "billryan-resume 中文经典单栏",
  "version": "1.0.0",
  "engine": "xelatex",
  "cjk_package": "xeCJK",
  "recommended_pages": [1],
  "supports_avatar": true,
  "default_avatar_style": "tikz_overlay_top_right",
  "supported_sections": [
    "basic_info",
    "education",
    "skills",
    "work",
    "projects",
    "certificates",
    "competitions"
  ],
  "entry_file": "resume.tex.j2"
}
```

### 3.2 模块占位符协议 (含专业技能渲染)

```jinja2
% ==================== 专业技能模块 ====================
{% if skills %}
\section{专业技能}
\begin{itemize}[parsep=0.4ex]
  {% for s in skills %}
  \item \textbf{ {{ s.category | latex_escape }} }: {{ s.items | latex_escape }}
  {% endfor %}
\end{itemize}
{% endif %}
```

---

## 4. JD 输入机制与简历生成参数契约

### 4.1 生成任务请求契约 (ResumeGenerationRequest)

```json
{
  "jd_source_type": "TEXT",
  "jd_text": "招聘高级后端开发工程师，要求熟练掌握 Python/FastAPI 与分布式中间件，有高并发性能调优经验...",
  "job_id": null,
  "template_id": "tpl-billryan-classic",
  "target_pages": 1,
  "language": "zh",
  "show_avatar": true,
  "selected_item_ids": [
    "uuid-skill-1",
    "uuid-work-1",
    "uuid-project-2",
    "uuid-cert-1"
  ],
  "ai_recommendation_mode": "JD_AUTO_SELECT_AND_TAILOR"
}
```

- **专业技能自动匹配**：AI 根据 JD 关键词自动从用户的 `SKILL` 条目中筛选最相关的技术项并前置高亮（如目标 JD 是后端开发，则优先挑选并重排后端相关技术栈）。

---

## 5. 验收核对清单 (Phase 0 Definition of Done)

- [x] 五类经历（CERTIFICATE, COMPETITION_AWARD, PROJECT, WORK, SKILL）字段规范明确并形成数据定义。
- [x] 模板模块协议与 Jinja2 + TikZ 照片插槽方案确定。
- [x] 特殊字符转义策略与沙箱安全机制（超时、内存、禁止 shell-escape）明确。
- [x] XeLaTeX/CTeX 编译引擎与跨平台中文字体回退链确立。
- [x] MVP 模板选型锁定（单栏经典 + 现代高密度）。
- [x] 旧 Markdown 数据向下兼容方案与经历提取入库策略就绪。
- [x] 经历 ID 溯源与防幻觉架构明确。
