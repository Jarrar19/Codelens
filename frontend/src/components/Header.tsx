"use client";

import React from "react";
import { RepoStats } from "@/lib/types";
import { 
  Terminal, 
  GitBranch, 
  Layers, 
  Share2, 
  Activity, 
  BarChart3, 
  BookOpen, 
  FolderGit2,
  RefreshCw
} from "lucide-react";

interface HeaderProps {
  stats: RepoStats | null;
  onOpenRepoModal: () => void;
  onOpenBenchmarkModal: () => void;
  onOpenVivaModal: () => void;
  onOpenGraphModal: () => void;
  onReindex: () => void;
  isReindexing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  stats,
  onOpenRepoModal,
  onOpenBenchmarkModal,
  onOpenVivaModal,
  onOpenGraphModal,
  onReindex,
  isReindexing,
}) => {
  const repoName = stats?.repository_name || "benchmark_project";
  const repoType = stats?.repo_type === "git_clone" ? "GIT REPO" : "LOCAL";

  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950 px-4 flex items-center justify-between select-none z-30 sticky top-0">
      {/* Brand & Active Repo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 font-semibold text-zinc-100 tracking-tight">
          <div className="w-7 h-7 rounded-md bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
            <Terminal className="w-4 h-4" />
          </div>
          <span className="text-sm font-bold tracking-wider text-white">CODELENS</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono border border-zinc-700">
            v1.0 AST ENGINE
          </span>
        </div>

        <div className="h-4 w-px bg-zinc-800 mx-1" />

        {/* Active Repo Pill */}
        <div className="flex items-center gap-2">
          <button
            onClick={onOpenRepoModal}
            className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-850 transition text-xs font-mono text-zinc-300 group"
            title="Click to switch or clone repository"
          >
            <FolderGit2 className="w-3.5 h-3.5 text-zinc-400 group-hover:text-blue-400 transition" />
            <span className="font-medium text-white max-w-[180px] truncate">{repoName}</span>
            <span className="text-[9px] px-1 py-0.2 rounded bg-zinc-800 text-zinc-400 uppercase font-semibold">
              {repoType}
            </span>
          </button>

          <button
            onClick={onReindex}
            disabled={isReindexing}
            className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-white transition disabled:opacity-50"
            title="Re-index current repository"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isReindexing ? "animate-spin text-blue-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* Center Telemetry Counter Pills */}
      <div className="hidden md:flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900/80 border border-zinc-800/80 text-xs text-zinc-400 font-mono">
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          <span>CHUNKS:</span>
          <span className="font-semibold text-zinc-200">{stats?.total_chunks || 0}</span>
        </div>

        <div 
          onClick={onOpenGraphModal}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900/80 border border-zinc-800/80 hover:border-zinc-700 text-xs text-zinc-400 font-mono cursor-pointer transition group"
          title="Click to inspect AST call graph"
        >
          <GitBranch className="w-3.5 h-3.5 text-indigo-400 group-hover:text-indigo-300" />
          <span>NODES:</span>
          <span className="font-semibold text-zinc-200">{stats?.graph_nodes || 0}</span>
          <span className="text-zinc-600">•</span>
          <span>EDGES:</span>
          <span className="font-semibold text-zinc-200">{stats?.graph_edges || 0}</span>
        </div>
      </div>

      {/* Right Action Modals */}
      <div className="flex items-center gap-2">
        <button
          onClick={onOpenGraphModal}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 hover:bg-zinc-850 hover:border-zinc-700 text-xs font-medium text-zinc-300 transition"
        >
          <Share2 className="w-3.5 h-3.5 text-cyan-400" />
          <span>Graph</span>
        </button>

        <button
          onClick={onOpenBenchmarkModal}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 hover:bg-zinc-850 hover:border-zinc-700 text-xs font-medium text-zinc-300 transition"
        >
          <BarChart3 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Benchmarks</span>
        </button>

        <button
          onClick={onOpenVivaModal}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-blue-600/10 border border-blue-500/30 hover:bg-blue-600/20 text-xs font-medium text-blue-400 transition"
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Viva Guide</span>
        </button>
      </div>
    </header>
  );
};
