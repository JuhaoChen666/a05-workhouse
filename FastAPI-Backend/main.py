from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.api import interview_routes, resume_routes, resume_optimize_routes, resume_template_routes, resume_generation_routes
from app.RAG.interview_service import InterviewService
from app.api.experience_app import register_experience_routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ 在启动时初始化面试服务（这里会加载模型）
    print("⏳ 正在初始化面试系统（加载 AI 模型）...")
    app.state.interview_service = InterviewService()
    print("✅ 面试系统初始化完成！")
    yield
    # 可以在这里做清理工作

app = FastAPI(
    title="智能面试系统API", 
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(interview_routes.router)
app.include_router(resume_routes.router)
app.include_router(resume_optimize_routes.router)
app.include_router(resume_template_routes.router)
app.include_router(resume_generation_routes.router)
register_experience_routes(app)

# 挂载静态文件目录，允许访问简历 PDF
UPLOAD_DIR = "data/resumes"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/data/resumes", StaticFiles(directory=UPLOAD_DIR), name="resumes")


@app.get("/")
async def root():
    return {
        "message": "智能面试系统API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    print("🚀 启动智能面试系统...")
    print("📍 访问地址: http://0.0.0.0:8000")
    print("📚 API文档: http://0.0.0.0:8000/docs")
    print("🔧 按 Ctrl+C 停止服务")
    print("-" * 50)


    uvicorn.run(
        app, 
        host="0.0.0.0",
        port=8000,
        reload=False
    )
