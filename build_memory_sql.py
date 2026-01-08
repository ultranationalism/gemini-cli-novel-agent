import os
import json
import hashlib
from pathlib import Path
from tqdm import tqdm
from txtai.embeddings import Embeddings
import logging

# 配置信息
INDEX_PATH = "memory"

# 1. 初始化 txtai (配置 OpenRouter)
embeddings = Embeddings({
    # 1. 显式指定使用 litellm 方法，绕过路径自动推断逻辑
    "method": "litellm", 
    
    # 2. 路径前缀建议加上提供商，帮助 LiteLLM 路由（虽然非强制，但更清晰）
    "path": "openai/openai/text-embedding-3-small",
    
    # 3. API 核心参数必须放在 vectors 字典内，
    # 因为源码中是通过 **self.config.get("vectors", {}) 传递给 litellm.embedding 的
    "vectors": {
        "api_base": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "custom_llm_provider": "openai",
        "encoding_format": "float"
    },
    
    "content": True,
    "writable": True
})

def process_incremental():
    embeddings.save(INDEX_PATH)



if __name__ == "__main__":
    process_incremental()