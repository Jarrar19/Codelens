/**
 * CodeLens Typed API Client
 */

import {
  StatusResponse,
  QueryResponse,
  GraphDataResponse,
  FileContentResponse,
  PresetQueriesResponse,
  BenchmarkResponse,
  BenchmarkRunResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  // System & Status
  async getStatus(): Promise<StatusResponse> {
    return request<StatusResponse>("/api/status");
  },

  // Repository Ingestion
  async ingestRepository(repositoryPath: string): Promise<{ success: boolean; message: string; stats: any }> {
    return request("/api/ingest", {
      method: "POST",
      body: JSON.stringify({ repository_path: repositoryPath }),
    });
  },

  async getAvailableRepositories(): Promise<{
    active_path: string;
    local_presets: string[];
    cloned_repositories: string[];
  }> {
    return request("/api/available_repositories");
  },

  // Codebase Querying
  async query(
    queryText: string,
    topK = 5,
    retrievalK = 25
  ): Promise<QueryResponse> {
    return request<QueryResponse>("/api/query", {
      method: "POST",
      body: JSON.stringify({
        query: queryText,
        top_k: topK,
        retrieval_k: retrievalK,
      }),
    });
  },

  // File Content
  async getFileContent(filePath: string): Promise<FileContentResponse> {
    return request<FileContentResponse>(
      `/api/file_content?file_path=${encodeURIComponent(filePath)}`
    );
  },

  // Graph Data
  async getGraphData(): Promise<GraphDataResponse> {
    return request<GraphDataResponse>("/api/graph_data");
  },

  // Presets & Showcase
  async getPresetQueries(): Promise<PresetQueriesResponse> {
    return request<PresetQueriesResponse>("/api/preset_queries");
  },

  // Dynamic Benchmarks
  async getBenchmarks(): Promise<BenchmarkResponse> {
    return request<BenchmarkResponse>("/api/benchmarks");
  },

  async runBenchmarks(): Promise<BenchmarkRunResponse> {
    return request<BenchmarkRunResponse>("/api/benchmark/run", {
      method: "POST",
    });
  },
};
