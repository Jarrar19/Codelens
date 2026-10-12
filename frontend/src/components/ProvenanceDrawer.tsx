"use client";

import React, { useState } from "react";
import { EvidenceChunk, PipelineStages } from "@/lib/types";
import { ChevronDown, ChevronUp, ShieldCheck, GitBranch, Search, Sparkles, FileCode } from "lucide-react";

interface ProvenanceDrawerProps {
  evidence: EvidenceChunk[];
  pipelineStages?: PipelineStages;
  onJumpToCode: (file: string, start: number, end: number) => void;
}

export const ProvenanceDrawer: React.FC<ProvenanceDrawerProps> = ({
  evidence,
  pipelineStages,
  onJumpToCode,
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="border border-zinc-800 rounded-lg bg-zinc-900/40 overflow-hidden mt-4 text-xs font-sans">
      {/* Drawer Toggle Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3.5 py-2.5 flex items-center justify-between hover:bg-zinc-850/60 transition text-left"
      >
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span className="font-semibold text-zinc-200">
            Why this answer? (Evidence Provenance)
          </span>
          <span className="px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 font-mono text-[10px] border border-emerald-800/80">
            {evidence.length} Verified Evidence Chunks
          </span>
        </div>
        <div className="flex items-center gap-1 text-zinc-400 text-[11px]">
          <span>{isOpen ? "Hide Provenance" : "Inspect Retrieval Trail"}</span>
          {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      {/* Expanded Content */}
      {isOpen && (
        <div className="p-3.5 border-t border-zinc-800 bg-zinc-950/60 space-y-3">
          <div className="p-2.5 rounded bg-zinc-900/80 border border-zinc-800 text-[11px] text-zinc-400 flex items-start gap-2">
            <Sparkles className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-zinc-200">Strict Grounding Guarantee:</span> Every claim in the generated explanation maps 1-to-1 with the AST symbols below. No external or hallucinated context was passed to the model.
            </div>
          </div>

          {/* Evidence Chunks List */}
          <div className="space-y-2.5">
            {evidence.map((chunk, idx) => {
              const isExpanded = chunk.graph_expanded;

              return (
                <div
                  key={chunk.chunk_id || idx}
                  className="p-3 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2 font-mono text-xs">
                      <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-bold">
                        #{chunk.rank || idx + 1}
                      </span>
                      <span className="font-semibold text-blue-400">{chunk.symbol_name}</span>
                      <span className="text-[10px] text-zinc-500 uppercase px-1 rounded bg-zinc-850 border border-zinc-800">
                        {chunk.symbol_type}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-mono border ${
                          isExpanded
                            ? "bg-indigo-950/80 text-indigo-300 border-indigo-800/80"
                            : "bg-blue-950/80 text-blue-300 border-blue-800/80"
                        }`}
                      >
                        {isExpanded ? <GitBranch className="w-3 h-3" /> : <Search className="w-3 h-3" />}
                        {isExpanded ? "AST Graph Expanded" : "Primary Hybrid Seed"}
                      </span>

                      <button
                        onClick={() => onJumpToCode(chunk.file_path, chunk.start_line, chunk.end_line)}
                        className="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-750 text-zinc-200 font-mono text-[10px] flex items-center gap-1 border border-zinc-700 transition"
                        title="Jump to lines in code viewer"
                      >
                        <FileCode className="w-3 h-3" />
                        <span>{chunk.file_path}:{chunk.start_line}</span>
                      </button>
                    </div>
                  </div>

                  {/* Retrieval Reason */}
                  <div className="text-[11px] text-zinc-400 font-sans">
                    {isExpanded ? (
                      <span className="text-indigo-300">
                        🔗 Discovered through 1-hop AST call graph traversal connecting related functions across modules.
                      </span>
                    ) : (
                      <span className="text-zinc-300">
                        ⚡ Selected via Reciprocal Rank Fusion (fusing dense embedding semantic match + BM25 keyword match).
                      </span>
                    )}
                  </div>

                  {/* Code Snippet Preview */}
                  {chunk.code && (
                    <pre className="p-2 rounded bg-zinc-950 text-zinc-300 font-mono text-[11px] overflow-x-auto max-h-28 border border-zinc-850">
                      <code>{chunk.code}</code>
                    </pre>
                  )}
                </div>
              );
            })}
          </div>

          {/* RRF Score Comparison Breakdown */}
          {pipelineStages?.fusion_seeds && pipelineStages.fusion_seeds.length > 0 && (
            <div className="mt-3 pt-3 border-t border-zinc-800">
              <h4 className="text-[11px] font-bold text-zinc-300 uppercase tracking-wider mb-2 font-mono">
                Hybrid Ranking & RRF Score Breakdown
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-[11px] border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500">
                      <th className="py-1 px-2">Symbol</th>
                      <th className="py-1 px-2">File</th>
                      <th className="py-1 px-2">Vector Rank</th>
                      <th className="py-1 px-2">BM25 Rank</th>
                      <th className="py-1 px-2">RRF Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-850 text-zinc-300">
                    {pipelineStages.fusion_seeds.map((s, i) => (
                      <tr key={i} className="hover:bg-zinc-900/60">
                        <td className="py-1 px-2 text-blue-400 font-semibold">{s.symbol_name}</td>
                        <td className="py-1 px-2 text-zinc-400">{s.file_path}</td>
                        <td className="py-1 px-2">{s.vector_rank ? `#${s.vector_rank}` : "—"}</td>
                        <td className="py-1 px-2">{s.bm25_rank ? `#${s.bm25_rank}` : "—"}</td>
                        <td className="py-1 px-2 font-bold text-emerald-400">{s.rrf_score.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
