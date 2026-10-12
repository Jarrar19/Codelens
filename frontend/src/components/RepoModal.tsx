"use client";

import React, { useState } from "react";
import { X, GitBranch, Folder, Play, CheckCircle2, AlertCircle } from "lucide-react";

interface RepoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onIngest: (path: string) => Promise<void>;
  isIngesting: boolean;
  activePath: string;
}

export const RepoModal: React.FC<RepoModalProps> = ({
  isOpen,
  onClose,
  onIngest,
  isIngesting,
  activePath,
}) => {
  const [activeTab, setActiveTab] = useState<"git" | "local">("git");
  const [gitUrl, setGitUrl] = useState<string>("https://github.com/pallets/flask");
  const [localPath, setLocalPath] = useState<string>("data/test_repositories/benchmark_project");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGitSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gitUrl.trim()) {
      setErrorMsg("Please enter a valid Git repository URL.");
      return;
    }
    setErrorMsg(null);
    try {
      await onIngest(gitUrl.trim());
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to clone and ingest repository");
    }
  };

  const handleLocalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localPath.trim()) {
      setErrorMsg("Please enter a local repository path.");
      return;
    }
    setErrorMsg(null);
    try {
      await onIngest(localPath.trim());
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to index local directory");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 select-none animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-xl bg-zinc-900 border border-zinc-800 shadow-2xl overflow-hidden flex flex-col font-sans">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Repository Manager
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Switch or clone repositories to analyze with CodeLens.
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isIngesting}
            className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Tabs */}
        <div className="flex border-b border-zinc-800 bg-zinc-950/40 text-xs font-medium">
          <button
            onClick={() => setActiveTab("git")}
            className={`flex-1 py-2.5 px-4 text-center flex items-center justify-center gap-2 transition border-b-2 ${
              activeTab === "git"
                ? "border-blue-500 text-blue-400 bg-zinc-900/80 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>Clone from GitHub</span>
          </button>
          <button
            onClick={() => setActiveTab("local")}
            className={`flex-1 py-2.5 px-4 text-center flex items-center justify-center gap-2 transition border-b-2 ${
              activeTab === "local"
                ? "border-blue-500 text-blue-400 bg-zinc-900/80 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Folder className="w-3.5 h-3.5" />
            <span>Local Directory</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-5 space-y-4">
          {errorMsg && (
            <div className="p-3 rounded-md bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {activeTab === "git" ? (
            <form onSubmit={handleGitSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
                  GitHub Repository URL
                </label>
                <input
                  type="text"
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  placeholder="https://github.com/user/repository"
                  disabled={isIngesting}
                  className="w-full px-3 py-2 rounded-md bg-zinc-950 border border-zinc-800 focus:border-blue-500 text-xs font-mono text-zinc-200 placeholder-zinc-500 focus:outline-none transition disabled:opacity-50"
                />
              </div>

              {/* Sample Git Chips */}
              <div>
                <label className="block text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-1.5">
                  Sample Repositories (1-Click)
                </label>
                <div className="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => setGitUrl("https://github.com/pallets/flask")}
                    className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-750 text-zinc-300 hover:text-white text-xs font-mono border border-zinc-700 transition"
                  >
                    pallets/flask
                  </button>
                  <button
                    type="button"
                    onClick={() => setGitUrl("https://github.com/encode/starlette")}
                    className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-750 text-zinc-300 hover:text-white text-xs font-mono border border-zinc-700 transition"
                  >
                    encode/starlette
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isIngesting || !gitUrl.trim()}
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50 cursor-pointer"
              >
                {isIngesting ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current" />
                )}
                <span>{isIngesting ? "Cloning & Indexing Repository..." : "Clone & Ingest"}</span>
              </button>
            </form>
          ) : (
            <form onSubmit={handleLocalSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
                  Local Directory Path
                </label>
                <input
                  type="text"
                  value={localPath}
                  onChange={(e) => setLocalPath(e.target.value)}
                  placeholder="data/test_repositories/benchmark_project"
                  disabled={isIngesting}
                  className="w-full px-3 py-2 rounded-md bg-zinc-950 border border-zinc-800 focus:border-blue-500 text-xs font-mono text-zinc-200 placeholder-zinc-500 focus:outline-none transition disabled:opacity-50"
                />
              </div>

              {/* Local Presets */}
              <div>
                <label className="block text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-1.5">
                  Available Presets
                </label>
                <div className="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => setLocalPath("data/test_repositories/benchmark_project")}
                    className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-750 text-zinc-300 hover:text-white text-xs font-mono border border-zinc-700 transition"
                  >
                    data/test_repositories/benchmark_project
                  </button>
                  <button
                    type="button"
                    onClick={() => setLocalPath("data/test_repositories/sample_project")}
                    className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-750 text-zinc-300 hover:text-white text-xs font-mono border border-zinc-700 transition"
                  >
                    data/test_repositories/sample_project
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isIngesting || !localPath.trim()}
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50 cursor-pointer"
              >
                {isIngesting ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current" />
                )}
                <span>{isIngesting ? "Indexing Local Codebase..." : "Index Directory"}</span>
              </button>
            </form>
          )}

          {/* Stepper Progress Feedback during Ingestion */}
          {isIngesting && (
            <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 text-xs space-y-2 mt-4">
              <div className="font-semibold text-zinc-300 flex items-center gap-2">
                <div className="w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span>Processing Pipeline Stages:</span>
              </div>
              <div className="space-y-1 text-zinc-400 font-mono text-[11px] pl-5">
                <p>1. Discovering & filtering source files</p>
                <p>2. Tree-sitter AST symbol & module extraction</p>
                <p>3. Dense embeddings & BM25 sparse indexing</p>
                <p>4. Constructing NetworkX dependency graph</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
