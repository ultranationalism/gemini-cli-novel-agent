FROM mem0/openmemory-mcp:latest

LABEL org.opencontainers.image.name="local/openmemory-mcp"

# Minimal wrapper — 仅在镜像层预装向量存储客户端（增量、与 openmemory/run.sh 行为一致）
# 不复制源码/默认不更改启动命令；可选地在构建时把本地修补文件复制进镜像以覆盖 upstream 的错误实现。

ARG VECTOR_STORE=milvus
ARG APPLY_LOCAL_CATEGORIZATION_PATCH=true
ARG APPLY_LOCAL_MEMORY_PATCH=true

RUN set -eux; \
    if [ "${VECTOR_STORE}" = "milvus" ]; then \
      pip install --no-cache-dir "pymilvus>=2.4.0,<2.6.0"; \
    elif [ "${VECTOR_STORE}" = "qdrant" ]; then \
      pip install --no-cache-dir "qdrant-client>=1.9.1"; \
    elif [ "${VECTOR_STORE}" = "chroma" ]; then \
      pip install --no-cache-dir "chromadb>=0.4.24"; \
    fi

# If enabled, copy the locally fixed categorization implementation into the upstream image.
# Prefer the file placed in docker/openmemory-mcp/ (survives removal of openmemory/ reference).
# This is implemented as: COPY -> conditional MOVE to keep Docker cache-friendly and toggleable.
COPY docker/openmemory-mcp/categorization.py /tmp/_local_categorization.py
RUN if [ "${APPLY_LOCAL_CATEGORIZATION_PATCH}" = "true" ]; then \
      mkdir -p /usr/src/openmemory/app/utils && mv /tmp/_local_categorization.py /usr/src/openmemory/app/utils/categorization.py; \
    else \
      rm -f /tmp/_local_categorization.py; \
    fi

# If enabled, copy the locally fixed memory.py with full vector store detection into the upstream image.
# This patch adds proper environment variable detection for Milvus and other vector stores.
COPY docker/openmemory-mcp/memory.py /tmp/_local_memory.py
RUN if [ "${APPLY_LOCAL_MEMORY_PATCH}" = "true" ]; then \
      mkdir -p /usr/src/openmemory/app/utils && mv /tmp/_local_memory.py /usr/src/openmemory/app/utils/memory.py; \
    else \
      rm -f /tmp/_local_memory.py; \
    fi

# If enabled, copy the locally fixed mcp_server.py with generic vector store API support.
# This patch replaces Qdrant-specific query_points with universal vector_store.search() API.
COPY docker/openmemory-mcp/mcp_server.py /tmp/_local_mcp_server.py
RUN if [ "${APPLY_LOCAL_MEMORY_PATCH}" = "true" ]; then \
      mkdir -p /usr/src/openmemory/app && mv /tmp/_local_mcp_server.py /usr/src/openmemory/app/mcp_server.py; \
    else \
      rm -f /tmp/_local_mcp_server.py; \
    fi

# 不修改容器的 CMD/ENTRYPOINT — 保持上游行为不变。