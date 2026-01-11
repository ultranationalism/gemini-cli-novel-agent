from fastapi import FastAPI, Request, Response
import httpx
import uvicorn
from datetime import datetime
import logging

app = FastAPI()

# 记录日志，方便观察 Milvus 到底发了什么
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    return response

# 核心代理逻辑：支持所有以 /v1 开头或直接 /embeddings 的路径
@app.api_route("/{path:path}", methods=["POST"])
async def proxy(request: Request, path: str):
    # 1. 构造转发目标 URL
    # 如果路径里没带 embeddings，我们根据 OpenAI 规范补全它
    target_path = path if "embeddings" in path else f"{path.rstrip('/')}/embeddings"
    target_url = f"https://openrouter.ai/api/{target_path.lstrip('/')}"
    

    # 2. 获取原始数据和 Token
    body = await request.json()
    auth_header = request.headers.get("Authorization")

    # 3. 补全 OpenRouter 强制要求的 Header (这是解决 < 报错的关键)
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:19530", # 规避 Cloudflare 拦截
        "X-Title": "Milvus-Sidecar-Proxy",
    }

    # 4. 转发请求
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                target_url,
                json=body,
                headers=headers,
                timeout=30.0
            )
            # 将 OpenRouter 的响应原样返回给 Milvus
            return Response(
                content=resp.content, 
                status_code=resp.status_code, 
                media_type="application/json"
            )
        except Exception as e:
            return Response(content=f'{{"error": "{str(e)}"}}', status_code=500)

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s: %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}

if __name__ == "__main__":
    # 建议换个端口，比如 8080，避免冲突
    uvicorn.run(app, host="0.0.0.0", port=8888, log_config=log_config)