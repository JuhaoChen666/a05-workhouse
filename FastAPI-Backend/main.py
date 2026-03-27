from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import interview_routes

app = FastAPI(title="智能面试系统API", version="1.0.0")

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
    print("📍 访问地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("🔧 按 Ctrl+C 停止服务")
    print("-" * 50)

    # ✅ 修改这里：传递字符串而不是app对象
    uvicorn.run(
        "main:app",  # 改为字符串格式
        host="0.0.0.0",
        port=8000,
        reload=True
    )