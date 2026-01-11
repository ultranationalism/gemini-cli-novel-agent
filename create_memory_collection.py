import os
import logging
from pymilvus import MilvusClient, DataType, Function, FunctionType
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MemoryCollection')

# --- 配置信息 ---
COLLECTION_NAME = "memory_qwen_with_func"
DIMENSION = 4096  # Qwen3-Embedding-8b 维度
MODEL_NAME = "qwen/qwen3-embedding-8b"
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["MILVUS_OPENAI_API_KEY"] = OPENROUTER_API_KEY  # Function 需要的环境变量

# 初始化 MilvusClient
client = MilvusClient(uri="http://localhost:19530")

def create_memory_collection():
    """创建带 Function 的 agent 记忆集合，自动生成向量"""
    
    # 检查集合是否已存在
    if client.has_collection(COLLECTION_NAME):
        logger.warning(f"Collection {COLLECTION_NAME} already exists. Dropping it...")
        client.drop_collection(COLLECTION_NAME)
    
    # 定义 Schema
    schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
    
    # 添加字段
    schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=500)
    schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)  # 记忆内容
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=DIMENSION)
    schema.add_field(field_name="user_id", datatype=DataType.VARCHAR, max_length=200)  # 用户ID
    schema.add_field(field_name="agent_id", datatype=DataType.VARCHAR, max_length=200)  # Agent ID
    schema.add_field(field_name="session_id", datatype=DataType.VARCHAR, max_length=200)  # 会话ID
    schema.add_field(field_name="timestamp", datatype=DataType.INT64)  # 时间戳
    schema.add_field(field_name="memory_type", datatype=DataType.VARCHAR, max_length=100)  # 记忆类型

    # 添加 Function 对象（自动向量化）
    emb_function = Function(
        name="qwen_embedding_func",
        function_type=FunctionType.TEXTEMBEDDING,
        input_field_names=["content"],  # 对 content 字段自动生成向量
        output_field_names=["vector"],
        params={
            "provider": "openai",
            "model_name": MODEL_NAME,
        }
    )
    schema.add_function(emb_function)

    # 配置索引
    index_params = client.prepare_index_params()
    
    # 向量索引
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200}
    )
    
    # 为常用查询字段添加标量索引
    index_params.add_index(
        field_name="user_id",
        index_type="INVERTED"
    )
    
    index_params.add_index(
        field_name="agent_id",
        index_type="INVERTED"
    )
    
    index_params.add_index(
        field_name="session_id",
        index_type="INVERTED"
    )
    
    index_params.add_index(
        field_name="timestamp",
        index_type="STL_SORT"  # 时间戳使用排序索引
    )

    # 创建集合
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params
    )
    
    logger.info(f"✓ Collection '{COLLECTION_NAME}' created successfully with auto-embedding function.")
    logger.info(f"  - Dimension: {DIMENSION}")
    logger.info(f"  - Model: {MODEL_NAME}")
    logger.info(f"  - Fields: id, content, vector, user_id, agent_id, session_id, timestamp, memory_type")
    logger.info(f"  - Dynamic fields enabled for metadata")

if __name__ == "__main__":
    try:
        create_memory_collection()
        logger.info("Memory collection setup complete!")
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise
