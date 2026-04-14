# 🌟 智能面试平台企业级系统架构指引 (Intelligent Interview System)

欢迎来到 **智能面试与评估系统平台**。本项目采用前沿微服务化全栈架构设计，致力于打破传统的应聘形式，深度融合了大预言模型 (LLMs)、文档自动解析解析与向量检索大成技术（Retrieval-Augmented Generation, RAG）。为候选人和人力资源部门提供无缝隙的、真实的“人-机”流式对弈模拟器和数据度量分析。

系统高度解耦，共划分为三大核心域：
- [X] **Vue 3 沉浸式前端服务 (Frontend)**：打造极致的流式打字对话与可视化图表展示。
- [X] **Spring Boot 用户引擎模块 (Springboot-backend)**：支撑企业级高并发要求的用户鉴权、数据管理的基础底座。
- [X] **FastAPI 大模型 AI 网关 (FastAPI-Backend)**：直接面向 DeepSeek、LangChain 生态体系，进行复杂的 AI 推理、对话切分与难度计算。

---

## 🏗️ 整体业务架构蓝图与交互流 (System Architecture Flow)

在这个完整的闭环中，多服务的交互如下流转：
1. **统一鉴权网关**：用户从前端发起的所有行为需首先经历 Spring Boot 分发 JWT (Json Web Token) Token 和权限认证拦截，确立用户级沙盒。
2. **AI RAG 对接**：当用户进入“上传简历”功能区域时，简历二进制流上传服务器后将被 FastAPI 服务所捕获，其内部会自动运用工具读取 PDF 文本，进行 Chunk 切片处理并利用 Embedding 引擎存储进内存级的向量数据库 ChromaDB（或 Milvus）中备用。
3. **沉浸式模拟面试**：前端发起的对话事件使用 Server-Sent Events (SSE) 直通 FastAPI。框架会快速读取 Chroma 中的履历，匹配用户应聘的岗位，调令 LangChain 进行上下文思考与出题限制后，在秒级以流式协议返回文本切片。前端随之进行打字机特效渲染。
4. **后评估图表展示**：面试结束，模型会自动分析出用户的长处劣势输出维度分数，存储到落盘系统后由 Spring Boot 及 Echarts 呈现出精准的雷达数据结构。

---

## 🟢 模块一：沉浸式前端服务 (Frontend)

基于当前最优的泛用型框架搭建，该前端强调响应速度、状态管控及图表渲染能力。

### 📌 领域技术栈矩阵
| 技术分类 | 名称版本 | 职责说明 |
| :--- | :--- | :--- |
| **基础框架** | Vue 3 (Composition API) | 全局生命周期控制和声明式绑定 |
| **构建链路** | Vite 7.x | 毫秒级热更新，生产模块打包 |
| **状态中心** | Pinia 3.x | 树形状态管理（承接用户/Auth及偏好设置） |
| **路由编排** | Vue Router 5.x | 与权限路由联动，实施白名单、登录态强行拦截 |
| **组件资产** | Element Plus 2.x | 提供业务骨架、交互抽屉、弹窗警告等高质量组件 |
| **特效呈现** | ECharts 5.x & vue-office | 绘制分析界面的雷达图图表，预览和还原在线简历文件 |

### 📌 亮点解构
- **解耦式请求模型**：所有请求统一包装于 `src/api/request.ts`。具备拦截器机制，自动挂载与刷新 Token、实现请求重试机制防网络闪断。
- **SSE 全双工呈现**：彻底消除使用 `http polling` 带来的卡顿和高负载，长连接单向实时推送极大增强由于等待大模型响应时间带来的割裂感。
- **页面路由组织**：涵盖主页落地 (Landing) 、简历投递聚合页 (JobSearch)、后台管理 (Admin) 及核心在线面试工作台 (Interview)。

---

## 🔵 模块二：数据引擎与微服务后端 (Springboot-backend)

Spring Boot 在本系统中扮演着 **“基石服务（Foundation Services）”** 的角色，以其出色的稳定性为所有用户中心系统提供坚实保障。

### 📌 领域技术栈矩阵
| 技术分类 | 名称版本 | 职责说明 |
| :--- | :--- | :--- |
| **应用容器** | Spring Boot 3.4 & Java 17 | JDK 17 新特性为服务提供高性能且安全运行环境 |
| **ORM持久层**| MyBatis-Plus 3.5.6 | 极大减少重复的简单 SQL 编写，快速支持分页、乐观锁配置 |
| **缓存/连接池**| Redis 6/7 & Druid | 支持海量字典配置缓存以及会话超时机制，池化技术减少重建连接消耗 |
| **安全加密** | Spring Security & JWT 0.12.x | 定义拦截链，无状态高安全接口验签授权 |
| **其他特性** | Hutool & Spring Mail | Java常用底层工具封装与邮件提醒集成 |

### 📌 亮点解构
- **安全第一**：针对用户态的 API （如修改信息、上传头像及获取面试历史），严格经过 Spring Security 拦截链检查 Token 并配合 RBAC 角色过滤。
- **规范的接口通讯**：应用强制 Restful 风格设计。接口统一封装至标准 `Result` 模型对象泛型传出，拥有全局异常处理器兜底处理（无需编写烦人的 `try-catch` 满天飞）。
- **图片处理层**：涵盖大小限定、防恶意篡改过滤机制的文件直接存储链路能力。

---

## 🟣 模块三：大脑中枢 AI 算法与引擎网关 (FastAPI-Backend)

此服务是整套产品皇冠上的明珠，直接对接云端模型能力与端侧数据的协同处理。为了解决 Java 的水土不服，我们专辟了基于 Python 极宽生态的此独立通道。

### 📌 领域技术栈矩阵
| 技术分类 | 名称 | 职责说明 |
| :--- | :--- | :--- |
| **API 服务层**| FastAPI (>= 3.10) | 基于 Starlette 带来的非阻塞异步并发支持，适合漫长的 LLM 请求任务 |
| **AI 大模型** | DeepSeek / OpenAI 代理 | 主要的语义分析与推理引擎，作为全能 Agent 的处理枢纽 |
| **编排核心** | LangChain / LangGraph | 使大型操作管道化、链条化的顶级 AI 工具套件 |
| **向量/数据** | ChromaDB & AIOSqlite | 提供海量文本段（简历内容）的高效向量索引以及高速内存读取 |
| **多模态引擎**| ModelScope (达摩院) | 用于特殊声学检测 (ASR)、情感分类 (Emo2Vec) 特质捕捉 |

### 📌 亮点解构
- **真正的动态博弈算法 (Dynamic Difficulty System)**：
    - **Easy / Normal 难度**：按常识引导并挖掘知识。
    - **Hard 难度限制**：首发“二振出局”严格淘汰模型，如果在特定的高要求环节连续两次偏题或拒绝回答指令（或给出质量极低的答案）会触发终止预警，中止面试流！
- **基于简历的一键重造润色流水线 (LCEL Pipeline Optimization)**：不仅负责问答，平台更提供简历增益。底层用 LCEL 实现了异步作业流，实时监听优化队列；将求职者原本青涩的文字针对当前应聘职位 JD，重构成完美的话术再导回 PDF 文档提供下载。
- **评分打磨机制**：抛弃虚假的评价，通过预设五大维度权重分层评价公式，将每一次有效对话转化为可度量分析结果。

---

## 🚀 DevOps 整体级部署起步指南 (Installation & Setup)

请注意，本平台为多进程联合架构，在调试或上线时请确保宿主机满足以下环境底线：
- **基础设施：** MySQL >= 8.0, Redis >= 6

**步骤 ①：启动基础 Java 后端服务**
```bash
cd Springboot-backend/
# 请确保将 src/main/resources/application.properties 里面的 jdbc 等信息填好
# 基于内建 maven 包装器启动 (无需提前配置环境变量)
./mvnw clean install
./mvnw spring-boot:run
```
*> 服务将监听 `8080` 端口*

**步骤 ②：启动 AI 引擎代理层**
由于含有大量机器学习组件包，**强烈建议使用 Conda 创建出专门的隔离态环境**。
```bash
cd FastAPI-Backend/
# 推荐基于 Python >=3.10
conda create -n ai-interview python=3.11
conda activate ai-interview

# 写入你的 .env 配置信息（如：DEEPSEEK_API_KEY）
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*> 服务将监听 `8000` 端口并提供 `/docs` 界面*

**步骤 ③：启动超现代视图层**
```bash
cd frontend/
npm install      # 若网络质量不佳可使用 pnpm 或 cnpm
npm run dev      # 启动热重载开发机
```
*> 成功后，Vue Vite 将提供默认网页承载，浏览器即刻享用。*

---

## 🗂️ 全局工程架构检索雷达图

为了帮助开发者快速定位至需要的代码进行排障或功能开发，下面提供主视图树索引：

```text
ProjectRoot/
├── frontend/                     # Vue 3 原生大视窗前端工程
│   ├── src/
│   │   ├── api/                  # 与 FastApi & Springboot 汇合通讯的集散中心接口群
│   │   ├── pages/                # 各类独立界面的 Vue 执行体 
│   │   └── store/                # 跨页级强一致性的状态维护管家
├── Springboot-backend/           # 传统基础数据防波堤网关
│   ├── src/main/java.../
│   │   ├── service/              # 表单鉴权和数据强清洗逻辑层落脚点
│   │   ├── mapper/               # 与 MyBatis xml对接层
│   │   └── utils/                # 加密盐处理、文件散列处理集结地
│   └── src/main/resources/
│       ├── mapper/               # 定制化 XML CRUD SQL 存储处
│       └── application.properties# 灵魂数据映射与端口生命环境配置
├── FastAPI-Backend/              # AI 神经网络心脏处理服务群
│   ├── app/
│   │   ├── RAG/                  # RAG 模式库：包含了最复杂的 AI Pipeline 链路和切片引擎
│   │   ├── api/                  # Python 的对外微服务网关控制区
│   │   └── models/               # 数据模型 Pydantic & Sqlalchemy 骨架定义
│   ├── chroma_db/                # 本地向量库运行期落地存放目录（自动生成不必理会）
│   ├── data/                     # 源简历文档 (纯文本/PDF/Docx) 中转地存储
│   └── pyproject.toml            # Python 大局管理器配置单
├── API_TEST_GUIDE.md             # 你会用到的 FastAPI 常用请求文档指导册
└── FRONTEND_PROJECT_GUIDE.md     # 前端如何定制二次开发的行动准则
```

---

> _**维护声明**：本核心级组件要求开发人员保持严格的分支隔离规定，后端通讯接口如果发生参数变更必须同步涉及三个大仓的类型重构！在上线前请复核 `.env` 关键密钥是否已被安全清理_。
