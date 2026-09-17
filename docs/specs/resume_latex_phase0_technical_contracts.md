# Phase 0：个人经历库与基于 LaTeX 的 JD 定制简历系统技术契约规范

> **关联 Issue**: [#1 feat: 建立个人经历库并重构为基于 LaTeX 的 JD 定制简历](https://github.com/JuhaoChen666/a05-workhouse/issues/1)  
> **所属阶段**: Phase 0（需求与技术契约）  
> **状态**: Accepted / Specification Frozen  
> **编写时间**: 2026-09-17  

---

## 1. 架构总览与背景

当前系统的简历优化链路主要依赖：
$$\text{PDF} \longrightarrow \text{文本提取} \longrightarrow \text{AI 输出 Markdown} \longrightarrow \text{Markdown 转 HTML/PDF}$$

此链路存在三大瓶颈：
1. **无法结构化复用**：不同岗位共用同一份扁平简历，过往证书、竞赛奖项、项目与工作经历无法原子化沉淀与按需编排；
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

## 2. 四类经历字段规范 (Experience Schemas)

经历按固定枚举分类：`CERTIFICATE`、`COMPETITION_AWARD`、`PROJECT`、`WORK`。不同用户数据严格按认证身份 `user_id` 物理/逻辑隔离。

### 2.1 公共基础字段 (BaseExperienceItem)

所有经历条目均包含以下元数据：

| 字段名 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `id` | `VARCHAR(36)` | 是 | UUID 唯一标识 |
| `user_id` | `VARCHAR(64)` | 是 | 所属用户 ID（服务端鉴权注入，绝不信任前端传入） |
| `type` | `ENUM` | 是 | `CERTIFICATE` \| `COMPETITION_AWARD` \| `PROJECT` \| `WORK` |
| `title` | `VARCHAR(200)` | 是 | 经历主标题（如项目名、公司名、比赛名、证书名） |
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

## 3. LaTeX 模板系统与模块占位符协议

为杜绝脆弱的正则表达式字符串全局替换（如 `REPLACE_NAME` 容易破坏 LaTeX 转义语法或引起嵌套崩溃），系统强制使用 **Jinja2 模板引擎** + **确定性 LaTeX 转义过滤器**。

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
    "work",
    "projects",
    "certificates",
    "competitions",
    "skills"
  ],
  "entry_file": "resume.tex.j2"
}
```

### 3.2 模块占位符协议

模板文件统一采用 `.tex.j2` 格式，支持标准化块（Blocks）：

```jinja2
% ==================== 个人信息 ====================
\name{ {{ basic_info.name | latex_escape }} }
\basicContactInfo{ {{ basic_info.phone | latex_escape }} }{ {{ basic_info.email | latex_escape }} }

{% if options.show_avatar and basic_info.avatar_path %}
% ==================== 证件照插槽 (TikZ 悬浮绝对定位) ====================
\begin{tikzpicture}[remember picture, overlay]
  \node[anchor=north east, xshift=-1.8cm, yshift=-1.2cm] at (current page.north east) {
    \includegraphics[height=3.0cm]{ {{ basic_info.avatar_path }} }
  };
\end{tikzpicture}
{% endif %}

% ==================== 项目经历模块 ====================
{% if projects %}
\section{项目经历}
{% for proj in projects %}
\datedsubsection{\textbf{ {{ proj.title | latex_escape }} } \hfill {{ proj.role | latex_escape }} }{ {{ proj.date_range | latex_escape }} }
\begin{itemize}[parsep=0.5ex]
  {% for bullet in proj.bullets %}
  \item {{ bullet | latex_escape }}
  {% endfor %}
\end{itemize}
{% endfor %}
{% endif %}
```

### 3.3 证件照插槽支持机制

依据社区主流模板特征，系统在模板元数据中配置支持策略：
1. **原生支持型**（如 `Awesome-CV`、`ModernCV`、`AltaCV`）：通过 Jinja2 动态注入模板特定的宏（如 `\photo[64pt][0.4pt]{avatar.jpg}`）；
2. **绝对定位型**（如 `billryan/resume`、`Jake's Resume`、单栏 ATS 模板）：统一通过 `\begin{tikzpicture}[remember picture, overlay]` 锚定于右上角，**不占用常规排版流高度，彻底避免多占行挤出第二页的问题**；
3. **关闭照片**：当用户选择 `show_avatar = false` 时，渲染引擎不注入任何图形宏，输出纯净的 100% ATS 友好文本。

### 3.4 LaTeX 特殊字符转义策略 (LaTeX Injection Prevention)

后端必须注册专属的 Jinja2 过滤器 `latex_escape`，所有用户文本及 AI 输出文本在写入模板前**必须严格转义**：

```python
LATEX_SPECIAL_CHAR_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
```

同时严格禁止用户在文本中输入 `\input`、`\include`、`\write18` 等潜在危害指令。

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
    "uuid-work-1",
    "uuid-project-2",
    "uuid-cert-1"
  ],
  "ai_recommendation_mode": "JD_AUTO_SELECT_AND_TAILOR"
}
```

- **`jd_source_type`**：`TEXT`（用户直接粘贴岗位描述）或 `JOB_ID`（关联系统已有的爬虫/管理岗位库）；
- **`target_pages`**：`1`（强制单页极简，MVP 默认）或 `2`（双页详版）；
- **`language`**：`zh`（简体中文）或 `en`（英文）；
- **`ai_recommendation_mode`**：
  - `MANUAL_ONLY`：完全由用户在前端勾选经历，AI 仅负责排版排布；
  - `JD_AUTO_SELECT_AND_TAILOR`：AI 分析 JD 与经历库，自动筛选最具匹配度的 N 条经历并进行关键词对齐润色。

### 4.2 AI 结构化改写输出契约 (AI Generation Output Contract)

**硬性约束**：大模型**严禁直接输出可执行的原始 LaTeX 代码**，AI 只允许输出标准 JSON 结构，由后端渲染引擎做确定性组装：

```json
{
  "selected_sections": {
    "work": [
      {
        "source_item_id": "uuid-work-1",
        "tailored_bullets": [
          "基于 FastAPI 重构分布式微服务调度引擎，QPS 从 1200 提升至 3500（针对 JD 高并发要求定制）。"
        ],
        "keywords_matched": ["FastAPI", "分布式", "高并发"]
      }
    ],
    "projects": [
      {
        "source_item_id": "uuid-project-2",
        "tailored_bullets": [
          "主导 Kubernetes 弹性容器化伸缩组件开发，资源利用率提升 35%（针对 JD 容器化背景定制）。"
        ],
        "keywords_matched": ["Kubernetes", "容器化"]
      }
    ]
  },
  "omitted_item_ids": [
    {
      "source_item_id": "uuid-work-3",
      "reason": "与当前后端研发岗位关联度较低，为保证单页排版建议收起。"
    }
  ],
  "jd_match_score": 88
}
```

---

## 5. XeLaTeX 编译环境与中文字体保障方案

### 5.1 编译执行契约

- **编译命令**：
  ```bash
  xelatex -interaction=nonstopmode -halt-on-error -no-shell-escape output.tex
  ```
- **核心安全参数**：
  - `-no-shell-escape`：绝对禁止通过 `\write18` 执行系统 shell 命令；
  - `-halt-on-error`：遇到严重编译错误立即中止，防止进程无限挂起；
  - `-interaction=nonstopmode`：非交互模式，避免因缺包或宏等待终端输入。

### 5.2 资源配额与沙箱防护 (Resource Limits)

| 指标 | 约束阈值 | 超限处理 |
| :--- | :--- | :--- |
| **执行超时** | `15 秒` | 终止子进程，标记任务 `COMPILE_TIMEOUT` |
| **内存上限** | `512 MB` | Linux cgroups / ulimit 限制，超额触发 OOMKill |
| **产物大小** | `10 MB` | 限制输出 PDF 最大体积，防磁盘耗尽 |
| **工作目录隔离** | 每次生成分配独立临时目录 `job_{job_id}/` | 任务结束自动清理临时中间文件（`.aux`, `.log`, `.out`） |

### 5.3 中文字体跨平台适配策略

使用 `fontspec` / `xeCJK` 声明字体族，配置标准化字体回退链（Fallback Chain）：

```latex
\usepackage{xeCJK}

% 主字体回退设置 (优先开源思源黑体，无环境时回退系统默认)
\setCJKmainfont[
  BoldFont={Noto Sans CJK SC Bold},
  ItalicFont={Noto Sans CJK SC Light}
]{Noto Sans CJK SC}

% 针对无 Noto 字体时的兼容宏配置
\IfFontExistsTF{Noto Sans CJK SC}{}{
  \IfFontExistsTF{PingFang SC}{\setCJKmainfont{PingFang SC}}{
    \IfFontExistsTF{Microsoft YaHei}{\setCJKmainfont{Microsoft YaHei}}{
      \setCJKmainfont{SimSun}
    }
  }
}
```

- **生产环境 (Docker Linux)**：预装 `fonts-noto-cjk`、`texlive-xetex`、`texlive-lang-chinese`；
- **本地开发环境 (Windows)**：无缝回退至 `Microsoft YaHei` / `SimSun`；
- **本地开发环境 (macOS)**：无缝回退至 `PingFang SC`。

---

## 6. MVP 内置模板选型清单

系统在 Phase 3 落地时提供首批 **2 套内置模板**，兼顾极简通用与现代高信息密度：

1. **`tpl-billryan-classic` (中文经典单栏模板)**：
   - 风格基底：`billryan/resume`
   - 适配场景：国内大厂互联网校招与社招、国企、事业单位；
   - 证件照方案：右上角 TikZ 悬浮绝对定位（可选开启）；
   - 版面控制：严格 1 页。
2. **`tpl-modern-twocol` (现代两栏高信息量模板)**：
   - 风格基底：`Awesome-CV` / `Deedy-Resume-CN`
   - 适配场景：技能密集型算法/架构工程师、全栈研发、具备丰富外企投递诉求者；
   - 证件照方案：左侧栏原生插槽；
   - 版面控制：紧凑单页或拓展两页。

所有生成结果保存时均记录 `template_id` 与 `template_version` 快照，确保即使系统升级模板，历史简历也能精准复现生成。

---

## 7. 旧 Markdown 数据兼容与平滑迁移策略

现有系统中遗留的历史简历记录全部采用 Markdown 存储。升级策略遵循**零停机、向下只读兼容、平滑迁移**：

1. **存储模型区分**：
   - 新增 `format` 字段，枚举为 `MARKDOWN` 与 `LATEX`；
   - 历史记录打上 `format = 'MARKDOWN'`，保留其原有的 `content_markdown` 字段；
   - 新生成的简历打上 `format = 'LATEX'`，存储 `latex_source_path` 与 `pdf_path`。
2. **历史记录读取**：
   - 历史 Markdown 简历继续支持在前端只读预览与历史版本下载；
3. **一键结构化迁移入库 (Migration Entry)**：
   - 为历史 Markdown 简历提供“一键提取到经历库”按钮；
   - 后端使用经历提取 Agent 将旧 Markdown 按四类枚举结构化为草稿，引导用户在经历库中一键确认入库；
4. **弃用周期**：
   - LaTeX 编译链路稳定运行 2 个迭代周期后，正式关闭“Markdown 转 HTML/PDF”的优化主入口。

---

## 8. 事实可追溯性与防幻觉控制机制 (Anti-Hallucination)

1. **经历库条目强绑定**：
   - 生成的每条履历 Bullet 必须记录 `source_item_id`；
   - 前端查看生成的简历时，支持点击任一项目/工作段落，右侧高亮对应的个人经历库原始条目。
2. **AI 改写透明度校验 (Diff Tracker)**：
   - 系统保存 AI 改写前与改写后的文本 Diff；
   - 严禁 AI 引入经历库中未曾提及的技术名词或虚构数据指标（如用户从未提及 ClickHouse，AI 不得凭空编造 ClickHouse 调优经历）；
   - 在前端生成确认页以差异比对形式展示给用户复核。

---

## 9. 验收核对清单 (Phase 0 Definition of Done)

- [x] 四类经历（CERTIFICATE, COMPETITION_AWARD, PROJECT, WORK）字段规范明确并形成数据定义。
- [x] 模板模块协议与 Jinja2 + TikZ 照片插槽方案确定。
- [x] 特殊字符转义策略与沙箱安全机制（超时、内存、禁止 shell-escape）明确。
- [x] XeLaTeX/CTeX 编译引擎与跨平台中文字体回退链确立。
- [x] MVP 模板选型锁定（单栏经典 + 现代高密度）。
- [x] 旧 Markdown 数据向下兼容方案与经历提取入库策略就绪。
- [x] 经历 ID 溯源与防幻觉架构明确。
