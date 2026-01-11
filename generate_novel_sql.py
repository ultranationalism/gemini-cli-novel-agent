import os
import json
import hashlib
from pathlib import Path
from tqdm import tqdm
import logging
from pymilvus import MilvusClient, DataType, Function, FunctionType
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NovelSync')

# --- 配置信息 ---
ROOT_DIR = "./my_novels"
STATE_FILE = "indexing_state_milvus_qwen.json"
COLLECTION_NAME = "novel_ref_qwen_with_func"  # 使用带 Function 的新集合
DIMENSION = 4096  # Qwen3-Embedding-8b 维度
MODEL_NAME = "qwen/qwen3-embedding-8b"
CHUNK_SIZE = 4000  # 4k 字段落切分
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["MILVUS_OPENAI_API_KEY"] = OPENROUTER_API_KEY  # Function 需要的环境变量

# 初始化 MilvusClient
client = MilvusClient(uri="http://localhost:19530")

def init_milvus():
    """初始化带 Function 的集合，自动生成向量"""
    if client.has_collection(COLLECTION_NAME):
        logger.info(f"Collection {COLLECTION_NAME} already exists.")
        return
    
    # 定义 Schema
    schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
    
    # 添加字段
    schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=500)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=DIMENSION)
    schema.add_field(field_name="author", datatype=DataType.VARCHAR, max_length=200)
    schema.add_field(field_name="path", datatype=DataType.VARCHAR, max_length=500)

    # 添加 Function 对象（自动向量化）
    emb_function = Function(
        name="qwen_embedding_func",
        function_type=FunctionType.TEXTEMBEDDING,
        input_field_names=["text"],
        output_field_names=["vector"],
        params={
            "provider": "openai",
            "model_name": MODEL_NAME,
        }
    )
    schema.add_function(emb_function)

    # 配置索引
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200}
    )

    # 创建集合
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params
    )
    logger.info(f"Collection {COLLECTION_NAME} created with auto-embedding function.")

def get_file_hash(file_path):
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

def process():
    init_milvus()
    client.load_collection(collection_name=COLLECTION_NAME)
    
    state = load_state()
    new_state = state.copy()
    
    files_to_process = []
    for root, _, files in os.walk(ROOT_DIR):
        for file in files:
            if file.endswith(".txt"):
                files_to_process.append(str(Path(root) / file))
    
    for file_path in tqdm(files_to_process, desc="Syncing Novels"):
        current_hash = get_file_hash(file_path)
        author = os.path.basename(os.path.dirname(file_path))
        file_state = new_state.get(file_path, {"hash": None, "processed_chunks": 0})

        if file_state["hash"] == current_hash:
            continue
            
        logger.info(f"Processing: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 4k 字段落切分
            chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
            
        # 增量插入（不需要手动生成 vector，Function 会自动处理）
        for i in range(file_state["processed_chunks"], len(chunks)):
            chunk_text = chunks[i]
            doc_id = f"{hashlib.md5(file_path.encode()).hexdigest()}_{i}"
            
            # 只传入 text 等字段，vector 由 Function 自动生成
            data = {
                "id": doc_id,
                "text": chunk_text,
                "author": author,
                "path": file_path
            }
            
            client.insert(collection_name=COLLECTION_NAME, data=[data])
            
            file_state["processed_chunks"] = i + 1
            new_state[file_path] = file_state
            save_state(new_state)  # 实时保存状态，防止崩溃
            
        file_state["hash"] = current_hash
        save_state(new_state)

    logger.info("Rebuild and Incremental Sync Complete.")

if __name__ == "__main__":
    process()