from fastapi import FastAPI, Request, Response
import httpx

app = FastAPI()

@app.post("/v1/embeddings")
async def proxy_embeddings(request: Request):
    # 1. 获取 Milvus 发来的原始数据
    body = await request.json()
    auth_header = request.headers.get("Authorization")

    # 2. 补全 OpenRouter 强制要求的 Header
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:19530", # 随便填，避开拦截
        "X-Title": "Milvus-Connector"
    }

    # 3. 转发给 OpenRouter
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            json=body,
            headers=headers,
            timeout=60.0
        )
        return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)