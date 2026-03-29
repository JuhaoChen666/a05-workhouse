# Emo2Vec-Agent - AI 模拟面试与能力提升系统

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangChain-0.3+-3776AB?style=flat-square" alt="LangChain">
  <img src="https://img.shields.io/badge/DeepSeek-AI-FF6B6B?style=flat-square" alt="DeepSeek">
  <img src="https://img.shields.io/badge/ModelScope-1.20+-1677FF?style=flat-square" alt="ModelScope">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python" alt="Python">
</p>

## 项目简介

Emo2Vec-Agent 是一款基于 **FastAPI + LangChain + DeepSeek + ModelScope** 技术栈构建的 AI 模拟面试与能力提升系统。系统通过大语言模型和多模态技术，为计算机专业学生提供沉浸式的模拟面试体验，并给出多维度的能力评估和提升建议。

## 核心功能

### 1. 岗位化题库与知识库

系统支持多种计算机专业岗位的模拟面试：

| 岗位 | 技术栈覆盖 | 题库类型 |
|------|-----------|---------|
| **Java 后端开发** | Spring Boot、MySQL、Redis、MQ、微服务 | 技术知识、项目深挖、场景设计、行为面试 |
| **Web 前端开发** | Vue/React、HTML5/CSS3、JavaScript/TypeScript、前端工程化 | 技术知识、项目深挖、场景设计、行为面试 |
| **Python 算法工程师** | Python、机器学习、深度学习、数据处理 | 技术知识、项目深挖、算法题、行为面试 |

**知识库特性：**
- 核心技术栈文档与最佳实践
- 高频面试考点整理
- 优秀回答范例库
- RAG 检索增强生成支持

### 2. 多模态交互式面试

- **语音输入**：集成 ModelScope 语音识别（ASR），支持自然语音对话
- **文字输入**：支持文字消息交互
- **AI 面试官**：基于 DeepSeek 大模型，具备多轮对话和智能追问能力
- **面试节奏控制**：自动管理面试流程和时长

### 3. 多维度面试分析

#### 内容分析
- 技术正确性评估
- 知识深度分析
- 逻辑严谨性评分
- 岗位匹配度计算

#### 表达分析（ModelScope 情感分析）
- 语速评估
- 表达清晰度
- 自信度分析
- 情感状态识别

#### 综合报告
- 结构化评估报告
- 各维度雷达图
- 亮点与不足分析
- 针对性改进建议

### 4. 能力提升反馈

- **个性化推荐**：基于评估结果推荐学习资源
- **练习计划**：生成定制化的能力提升计划
- **历史记录**：记录每次面试表现
- **成长曲线**：可视化展示能力发展趋势

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   REST API  │  │  WebSocket  │  │   CORS Middleware   │  │
│  │   (FastAPI) │  │  (Streaming)│  │   Rate Limiting     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        Agent Core                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   LangGraph 工作流                       │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │ │
│  │  │  面试流程   │  │  智能追问   │  │   节奏控制      │ │ │
│  │  │   管理     │  │   引擎     │  │   模块         │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        Model Layer                           │
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │   DeepSeek LLM      │  │      ModelScope Models      │   │
│  │   (对话/评估/报告)   │  │  情感分析 · 语音识别 · TTS   │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        Data Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  ChromaDB   │  │   Redis     │  │   PostgreSQL        │  │
│  │  (向量库)   │  │   (缓存)    │  │   (结构化数据)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python >= 3.10
- Redis（可选，用于缓存）
- PostgreSQL（可选，用于数据持久化）

### 安装

```bash
# 克隆项目
git clone https://gitee.com/yourusername/emo2vec-agent.git
cd emo2vec-agent

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 配置

1. 复制环境变量模板：
```bash
cp .env .env
```

2. 编辑 `.env` 文件，配置以下关键参数：
```env
# DeepSeek API 配置（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# ModelScope 配置
MODELSCOPE_CACHE_DIR=./cache/modelscope
EMOTION_MODEL=damo/nlp_structbert_emotion-classification_chinese-base
ASR_MODEL=damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch

# 数据库配置（开发环境可使用 SQLite）
DATABASE_URL=sqlite+aiosqlite:///./data/emo2vec.db

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0
```

### 启动服务

```bash
# 开发模式
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

访问 http://localhost:8000/docs 查看 API 文档。

## API 接口

### 面试相关

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/chat/completions` | POST | 文本对话面试 |
| `/api/v1/chat/completions/stream` | POST | 流式对话面试 |
| `/api/v1/agent/execute` | POST | 执行模拟面试会话 |

### 分析相关

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/chat/analyze-emotion` | POST | 分析语音/文本情感 |
| `/api/v1/agent/tools/execute` | POST | 执行特定工具（如语音识别） |

### 系统相关

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/system/health` | GET | 系统健康检查 |
| `/api/v1/system/info` | GET | 系统信息 |
| `/api/v1/agent/tools` | GET | 获取可用工具列表 |

## 使用示例

### 开始模拟面试

```python
import requests

# 开始面试会话
response = requests.post("http://localhost:8000/api/v1/agent/execute", json={
    "input": "我想面试 Java 后端开发岗位",
    "config": {
        "name": "java-backend-interview",
        "system_prompt": "你是一位经验丰富的 Java 后端开发面试官...",
        "tools": ["emotion_analysis"],
        "temperature": 0.7
    }
})

result = response.json()
print(result["data"]["output"])
```

### 情感分析

```python
# 分析面试回答的情感状态
response = requests.post("http://localhost:8000/api/v1/chat/analyze-emotion", params={
    "text": "我对 Spring Boot 的自动配置原理比较熟悉..."
})

emotion_result = response.json()
print(f"主导情感: {emotion_result['data']['dominant_emotion']}")
```

## 项目结构

```
emo2vec-agent/
├── app/
│   ├── api/v1/endpoints/     # API 路由
│   ├── agent/                # LangChain Agent 核心
│   │   ├── graph/            # LangGraph 工作流
│   │   ├── tools/            # 工具注册
│   │   └── prompts/          # 提示词管理
│   ├── llm/                  # LLM 模型层
│   │   ├── deepseek.py       # DeepSeek 集成
│   │   ├── modelscope.py     # ModelScope 集成
│   │   └── router.py         # 模型路由
│   ├── services/             # 业务逻辑层
│   ├── models/               # 数据模型
│   ├── infrastructure/       # 基础设施
│   └── core/                 # 核心配置
├── main.py                   # 应用入口
├── pyproject.toml            # 项目配置
└── .env.example              # 环境变量示例
```

## 技术栈

- **Web 框架**: FastAPI 0.115+
- **Agent 框架**: LangChain 0.3+ / LangGraph 0.2+
- **主 LLM**: DeepSeek API
- **辅助模型**: ModelScope（情感分析、语音识别）
- **向量数据库**: ChromaDB / Milvus
- **缓存**: Redis
- **数据库**: PostgreSQL / SQLite
- **部署**: Docker / Kubernetes

## 开发计划

- [x] 基础架构搭建
- [x] DeepSeek LLM 集成
- [x] ModelScope 多模态集成
- [x] LangGraph Agent 框架
- [ ] 岗位题库构建
- [ ] 知识库 RAG 实现
- [ ] 前端界面开发
- [ ] 面试报告生成
- [ ] 能力成长曲线可视化

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- 项目主页: https://gitee.com/yourusername/emo2vec-agent
- 问题反馈: https://gitee.com/yourusername/emo2vec-agent/issues

---

<p align="center">
   Made with ❤️ for Computer Science Students
</p>
