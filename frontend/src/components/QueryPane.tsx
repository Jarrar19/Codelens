"use client";

import React, { useState } from "react";
import { QueryResponse, PresetQuery } from "@/lib/types";
import { ProvenanceDrawer } from "./ProvenanceDrawer";
import { 
  Search, 
  Sparkles, 
  MapPin, 
  Clock, 
  CheckCircle2, 
  Copy, 
  Check, 
  CornerDownLeft, 
  Layers, 
  HelpCircle,
  Lightbulb
} from "lucide-react";

interface QueryPaneProps {
  onRunQuery: (queryText: string) => Promise<void>;
  isLoading: boolean;
  queryResult: QueryResponse | null;
  onCitationClick: (file: string, start: number, end: number) => void;
  presetQueries: PresetQuery[];
}

export const QueryPane: React.FC<QueryPaneProps> = ({
  onRunQuery,
  isLoading,
  queryResult,
  onCitationClick,
  presetQueries,
}) => {
  const [queryInput, setQueryInput] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryInput.trim() || isLoading) return;
    onRunQuery(queryInput.trim());
  };

  const handleSelectPreset = (questionText: string) => {
    setQueryInput(questionText);
    onRunQuery(questionText);
  };

  const handleCopyAnswer = () => {
    if (!queryResult) return;
    navigator.clipboard.writeText(queryResult.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  /**
   * Helper to format text with clickable citation badges
   * Turns [file.py:start-end] into interactive badge components
   */
  const renderFormattedAnswer = (text: string) => {
    const citationRegex = /\[([a-zA-Z0-9_\-./]+):(\d+)(?:-(\d+))?\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      const matchIndex = match.index;
      if (matchIndex > lastIndex) {
        parts.push(text.substring(lastIndex, matchIndex));
      }

      const file = match[1];
      const start = parseInt(match[2], 10);
      const end = match[3] ? parseInt(match[3], 10) : start;
      const fullCitation = match[0];

      parts.push(
        <button
          key={`${file}-${start}-${end}-${matchIndex}`}
          onClick={() => onCitationClick(file, start, end)}
          className="citation-badge inline-flex items-center gap-1 mx-1 font-mono text-[11px] font-semibold text-emerald-400 bg-emerald-950/80 border border-emerald-700/80 rounded px-1.5 py-0.5 hover:bg-emerald-900 transition"
          title={`Click to view ${file} lines ${start}–${end} in code viewer`}
        >
          <MapPin className="w-2.5 h-2.5 text-emerald-400" />
          <span>{file.split("/").pop()}:{start}{end !== start ? `-${end}` : ""}</span>
        </button>
      );

      lastIndex = matchIndex + fullCitation.length;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts;
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 text-zinc-200 overflow-y-auto p-4 sm:p-5">
      {/* Search Input Bar */}
      <form onSubmit={handleSubmit} className="relative flex flex-col gap-2 mb-4 flex-shrink-0">
        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
          <input
            type="text"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            placeholder="Ask anything about this codebase... (e.g. 'How does user login work?')"
            className="w-full pl-9 pr-24 py-2.5 bg-zinc-900 border border-zinc-800 focus:border-blue-500 rounded-lg text-xs sm:text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none transition shadow-inner font-sans"
          />
          <div className="absolute right-2 flex items-center gap-1.5">
            <button
              type="submit"
              disabled={isLoading || !queryInput.trim()}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-semibold flex items-center gap-1 transition disabled:opacity-50 cursor-pointer"
            >
              {isLoading ? (
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <span>Search</span>
                  <CornerDownLeft className="w-3 h-3 text-blue-200" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* 1-Click Starter Question Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
          <div className="flex items-center gap-1 text-[11px] text-zinc-500 font-medium flex-shrink-0 mr-1">
            <Lightbulb className="w-3 h-3 text-amber-400" />
            <span>Try:</span>
          </div>
          {presetQueries.slice(0, 4).map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handleSelectPreset(preset.question)}
              className="px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-850 text-zinc-400 hover:text-zinc-200 text-xs font-sans whitespace-nowrap transition cursor-pointer"
            >
              {preset.question}
            </button>
          ))}
        </div>
      </form>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-0">
        {isLoading ? (
          <div className="p-6 rounded-lg border border-zinc-800 bg-zinc-900/40 flex flex-col items-center justify-center text-center my-auto">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
            <h4 className="text-sm font-semibold text-zinc-200 mb-1">
              Analyzing Codebase Evidence...
            </h4>
            <div className="space-y-1.5 text-xs text-zinc-400 font-sans max-w-sm">
              <p className="flex items-center justify-center gap-1.5">
                <Search className="w-3 h-3 text-blue-400" /> Searching Dense Vector & BM25 indices
              </p>
              <p className="flex items-center justify-center gap-1.5">
                <Layers className="w-3 h-3 text-indigo-400" /> Traversing NetworkX AST dependency graph
              </p>
              <p className="flex items-center justify-center gap-1.5">
                <Sparkles className="w-3 h-3 text-emerald-400" /> Synthesizing grounded answer with line citations
              </p>
            </div>
          </div>
        ) : !queryResult ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border border-dashed border-zinc-800/80 rounded-lg text-zinc-500 my-auto">
            <div className="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-3 text-zinc-400">
              <Sparkles className="w-5 h-5 text-blue-400" />
            </div>
            <h3 className="text-sm font-semibold text-zinc-300 mb-1">
              Grounded Codebase Explanation
            </h3>
            <p className="text-xs text-zinc-500 max-w-md mb-4 font-sans leading-relaxed">
              Ask any natural language question about the active repository. CodeLens retrieves exact AST chunks, expands multi-hop caller/callee connections, and provides verified line-cited answers.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg text-left">
              {presetQueries.slice(0, 4).map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleSelectPreset(p.question)}
                  className="p-2.5 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-850 text-left transition group"
                >
                  <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block mb-0.5">
                    {p.category}
                  </span>
                  <span className="text-xs text-zinc-300 group-hover:text-blue-400 font-medium line-clamp-1">
                    {p.question}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {/* Header Telemetry Bar */}
            <div className="flex items-center justify-between gap-2 p-2.5 rounded-md bg-zinc-900/60 border border-zinc-800 flex-wrap text-xs">
              <div className="flex items-center gap-3 font-mono text-zinc-400">
                <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{queryResult.citation_count} Verified Citations</span>
                </span>
                <span className="flex items-center gap-1 text-zinc-500">
                  <Clock className="w-3 h-3" />
                  <span>{queryResult.duration_sec}s</span>
                </span>
                <span className="hidden sm:inline text-zinc-500">
                  {queryResult.llm_model}
                </span>
              </div>

              <button
                onClick={handleCopyAnswer}
                className="px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-750 text-zinc-300 hover:text-white flex items-center gap-1 font-mono text-xs transition"
                title="Copy answer markdown"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? "Copied!" : "Copy"}</span>
              </button>
            </div>

            {/* Quick Citations Carousel */}
            {queryResult.citations && queryResult.citations.length > 0 && (
              <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
                <span className="text-[11px] font-mono text-zinc-500 flex items-center gap-1 flex-shrink-0">
                  <MapPin className="w-3 h-3 text-emerald-400" />
                  <span>Citations:</span>
                </span>
                {queryResult.citations.map((c, i) => (
                  <button
                    key={i}
                    onClick={() => onCitationClick(c.file_path, c.start_line, c.end_line)}
                    className="px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800/80 hover:border-emerald-600 text-emerald-300 font-mono text-xs flex items-center gap-1 whitespace-nowrap transition cursor-pointer"
                    title={`Jump to ${c.file_path}:${c.start_line}-${c.end_line} in code viewer`}
                  >
                    <span>{c.file_path.split("/").pop()}:{c.start_line}{c.end_line !== c.start_line ? `-${c.end_line}` : ""}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Grounded Explanation Answer Card */}
            <div className="p-4 rounded-lg bg-zinc-900 border border-zinc-800 shadow-sm leading-relaxed text-zinc-150 text-xs sm:text-sm font-sans space-y-3">
              <div className="whitespace-pre-wrap">
                {renderFormattedAnswer(queryResult.answer)}
              </div>
            </div>

            {/* Why this answer? (Evidence Provenance) */}
            <ProvenanceDrawer
              evidence={queryResult.evidence}
              pipelineStages={queryResult.pipeline_stages}
              onJumpToCode={onCitationClick}
            />
          </div>
        )}
      </div>
    </div>
  );
};
