/**
 * TypeScript Data Models for CodeLens
 */

export interface RepoStats {
  repository_name: string;
  repository_path: string;
  total_files: number;
  total_chunks: number;
  graph_nodes: number;
  graph_edges: number;
  symbol_nodes?: number;
  file_nodes?: number;
  call_edges?: number;
  calls_edges?: number;
  import_edges?: number;
  imports_edges?: number;
  contains_edges?: number;
  ingestion_time_sec?: number;
  repo_type?: "local" | "git_clone";
  files?: string[];
}

export interface StatusResponse {
  is_ingested: boolean;
  display_name: string;
  repository_path: string;
  stats: RepoStats;
}

export interface Citation {
  citation: string;
  file_path: string;
  start_line: number;
  end_line: number;
  is_valid: boolean;
}

export interface EvidenceChunk {
  rank: number;
  chunk_id: string;
  file_path: string;
  symbol_name: string;
  symbol_type: string;
  start_line: number;
  end_line: number;
  code: string;
  graph_expanded: boolean;
  imports?: string[];
}

export interface CandidateItem {
  chunk_id: string;
  symbol_name: string;
  file_path: string;
  score: number;
}

export interface FusionSeedItem {
  chunk_id: string;
  symbol_name: string;
  file_path: string;
  rrf_score: number;
  vector_rank: number | null;
  bm25_rank: number | null;
  symbol_type: string;
}

export interface GraphExpandedItem {
  node: string;
  symbol_name: string;
  file_path: string;
  symbol_type: string;
  start_line: number;
  end_line: number;
  is_seed: boolean;
}

export interface PipelineStages {
  vector_candidates: CandidateItem[];
  bm25_candidates: CandidateItem[];
  fusion_seeds: FusionSeedItem[];
  graph_expansion: GraphExpandedItem[];
  final_results: Array<{
    chunk_id: string;
    symbol_name: string;
    file_path: string;
    graph_expanded?: boolean;
  }>;
}

export interface QueryResponse {
  answer: string;
  evidence: EvidenceChunk[];
  citations: Citation[];
  duration_sec: number;
  llm_model: string;
  citation_count: number;
  evidence_count: number;
  pipeline_stages?: PipelineStages;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "file" | "symbol";
  file_path?: string;
  symbol_name?: string;
  symbol_type?: string;
  start_line?: number;
  end_line?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: "CONTAINS" | "CALLS" | "IMPORTS";
}

export interface GraphDataResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats?: {
    total_nodes: number;
    total_edges: number;
    file_nodes: number;
    symbol_nodes: number;
    call_edges: number;
    import_edges: number;
    contains_edges: number;
  };
}

export interface FileContentResponse {
  file_path: string;
  content: string;
  total_lines: number;
  symbols: Array<{
    name: string;
    type: string;
    start_line: number;
    end_line: number;
  }>;
}

export interface PresetQuery {
  id: number;
  question: string;
  category: string;
  expected_symbols: string[];
}

export interface PresetQueriesResponse {
  showcase_queries: PresetQuery[];
}

export interface BenchmarkMetricItem {
  metric: string;
  naive_rag: number;
  codelens_seeds?: number;
  codelens_expanded?: number;
  codelens?: number;
  description?: string;
  difference?: string;
}

export interface QuestionBreakdownItem {
  id: number;
  question: string;
  expected_symbols: string[];
  naive_rag_coverage: number;
  codelens_coverage: number;
  expansion_recovered: string[];
}

export interface BenchmarkResponse {
  retrieval_benchmark: {
    title: string;
    total_questions: number;
    metrics: BenchmarkMetricItem[];
    questions_breakdown?: QuestionBreakdownItem[];
  };
  answer_benchmark: {
    title: string;
    metrics: BenchmarkMetricItem[];
  };
  key_takeaway: string;
}

export interface BenchmarkRunResponse {
  success: boolean;
  message: string;
  metrics: {
    "hit@1": number;
    "hit@3": number;
    "hit@5": number;
    mrr: number;
    coverage: number;
  };
  detailed_results: Array<{
    id: number;
    question: string;
    metrics: {
      "hit@1": number;
      "hit@3": number;
      "hit@5": number;
      mrr: number;
      coverage: number;
    };
  }>;
}
