import os
import json
import hashlib
from pathlib import Path
from tqdm import tqdm
from txtai.embeddings import Embeddings
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取 LiteLLM 的日志对象
litellm_logger = logging.getLogger('LiteLLM')
# 将其设为 WARNING 或更高，这样 INFO 级别的 "Completed Call" 就不会出现了
litellm_logger.setLevel(logging.WARNING)
# 配置信息
INDEX_PATH = "novel_kb_index"
STATE_FILE = "indexing_state.json"  # 断点与增量的状态记录文件
ROOT_DIR = "./my_novels"

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
        "api_key": os.getenv("OPENAI_API_KEY"),
        "custom_llm_provider": "openai",
        "encoding_format": "float"
    },
    
    "content": True,
    "writable": True
})
print("Starting incremental indexing process...")

# 如果索引已存在，则加载它
if os.path.exists(INDEX_PATH):
    embeddings.load(INDEX_PATH)

def get_file_hash(file_path):
    """计算文件 MD5，用于判断文件内容是否变动"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def process_incremental():
    state = load_state()
    new_state = state.copy()
    documents = []
    
    # 收集所有txt文件
    files_to_process = []
    for root, _, files in os.walk(ROOT_DIR):
        for file in files:
            if file.endswith(".txt"):
                files_to_process.append(str(Path(root) / file))
    
    # 遍历文件夹
    for file_path in tqdm(files_to_process, desc="Processing files"):
        current_hash = get_file_hash(file_path)
        author = os.path.basename(os.path.dirname(file_path))

        # 获取当前文件的状态
        file_state = new_state.get(file_path, {"hash": None, "processed_chunks": 0})
        
        # 兼容旧状态格式（如果是字符串，则转换为dict）
        if isinstance(file_state, str):
            file_state = {"hash": file_state, "processed_chunks": 0}
        
        # 如果哈希没变，说明该文件已完全入库且未被修改，直接跳过
        if file_state["hash"] == current_hash:
            continue
        
        print(f"检测到新文件或已修改文件: {file_path}")
        
        # 重置processed_chunks，因为文件变了
        file_state["hash"] = current_hash
        file_state["processed_chunks"] = 0
        new_state[file_path] = file_state
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 1K 字段落切分
            chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
        
        # 从已处理的chunk开始
        for i in range(file_state["processed_chunks"], len(chunks)):
            chunk = chunks[i]
            doc_id = f"{file_path}_{i}"
            doc = {
                "id": doc_id,
                "text": chunk,
                "author": author,
                "path": file_path
            }
            
            # 逐个chunk upsert并落盘
            embeddings.upsert([doc])
            embeddings.save(INDEX_PATH)
            
            # 更新状态
            file_state["processed_chunks"] = i + 1
            new_state[file_path] = file_state
            save_state(new_state)
        
        print(f"文件 {file_path} 处理完成，共 {len(chunks)} 个chunks。")

    print("增量更新完成。")

if __name__ == "__main__":
    process_incremental()