/// <reference types="node" />
import { tool } from "@opencode-ai/plugin";

/**
 * Mem0 Extensions - 为 OpenCode 深度定制的记忆管理增强工具
 * 默认 BASE_URL 指向本地，可通过环境变量 MEM0_API_URL 覆盖
 */
const BASE_URL = process.env.MEM0_API_URL || "http://localhost:8765";
const DEFAULT_USER_ID = "worker";

export default tool({
  description: "Mem0 记忆系统增强插件：支持按时间回溯、高级过滤、语义关联、状态控制及访问溯源。",
  args: {
    action: tool.schema.enum([
      "get_recent",   // 获取最近记忆 (时间倒序)
      "filter",       // 高级联合筛选
      "update",       // 修正/更新特定记忆
      "related",      // 获取语义关联记忆
      "archive",      // 归档记忆
      "pause",        // 暂停/恢复记忆访问
      "access_log",   // 查看访问历史
      "stats"         // 用户画像与统计
    ]).describe("执行的动作类型"),
      params: tool.schema.record(tool.schema.string(), tool.schema.any()).optional().describe("动作对应的参数对象"),
  },
  async execute({ action, params = {} }) {
    const userId = params.user_id || DEFAULT_USER_ID;

    try {
      switch (action) {
        case "get_recent": {
          // 使用 filter 端点代替 GET /memories/，避免分页验证问题
          return await apiRequest(`/api/v1/memories/filter`, "POST", {
            user_id: userId,
            page: 1,
            page_size: params.limit || 10,
            sort_by: "created_at",
            sort_direction: "desc",
            ...(params.app_id && { app_id: params.app_id }),
            ...(params.categories && { categories: params.categories }),
          });
        }

        case "filter": {
          // 高级过滤模式
          return await apiRequest(`/api/v1/memories/filter`, "POST", {
            user_id: userId,
            ...params
          });
        }

        case "update": {
          // 更新记忆内容
          if (!params.memory_id || !params.memory_content) throw new Error("Missing memory_id or content");
          return await apiRequest(`/api/v1/memories/${params.memory_id}`, "PUT", {
            user_id: userId,
            memory_content: params.memory_content
          });
        }

        case "related": {
          // 语义关联查询 (强制 size 为 5)
          if (!params.memory_id) throw new Error("Missing memory_id");
          const query = new URLSearchParams({ user_id: userId, size: "5" });
          return await apiRequest(`/api/v1/memories/${params.memory_id}/related?${query}`, "GET");
        }

        case "archive": {
          // 归档操作
          if (!params.memory_ids) throw new Error("Missing memory_ids list");
          return await apiRequest(`/api/v1/memories/actions/archive?user_id=${userId}`, "POST", {
            memory_ids: params.memory_ids
          });
        }

        case "pause": {
          // 细粒度访问控制
          return await apiRequest(`/api/v1/memories/actions/pause`, "POST", {
            user_id: userId,
            ...params
          });
        }

        case "access_log": {
          // 查看溯源日志
          if (!params.memory_id) throw new Error("Missing memory_id");
          const query = new URLSearchParams({ 
            page: (params.page || 1).toString(),
            page_size: (params.size || 20).toString() 
          });
          return await apiRequest(`/api/v1/memories/${params.memory_id}/access-log?${query}`, "GET");
        }

        case "stats": {
          // 全局统计
          return await apiRequest(`/api/v1/stats/?user_id=${userId}`, "GET");
        }

        default:
          return `Unknown action: ${action}`;
      }
    } catch (error) {
      return `Mem0 Extension Error: ${error instanceof Error ? error.message : String(error)}`;
    }
  },
});

/**
 * 通用请求封装
 */
async function apiRequest(path: string, method: string, body?: object) {
  const url = `${BASE_URL}${path}`;
  const options: RequestInit = {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  };

  const response = await fetch(url, options);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
  return await response.json();
}