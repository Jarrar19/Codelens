"use client";

import React from "react";
import { X, BookOpen, CheckCircle, HelpCircle } from "lucide-react";

interface VivaModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const VivaModal: React.FC<VivaModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const faqs = [
    {
      q: "Why does standard Naive RAG fail on codebases?",
      a: "Naive RAG splits files by arbitrary line counts or character chunks (e.g. 500 characters). This splits function definitions across chunk boundaries, misses multi-hop cross-file function calls, and achieves only ~84.9% evidence coverage.",
    },
    {
      q: "How does Tree-sitter AST chunking work?",
      a: "Tree-sitter generates a concrete syntax tree (CST). CodeLens extracts function_definition, class_definition, and logical procedural module sections as discrete semantic symbols with exact 1-indexed line coordinates.",
    },
    {
      q: "What is Reciprocal Rank Fusion (RRF) and why is it used?",
      a: "Dense embeddings (all-MiniLM-L6-v2) excel at semantic concepts ('verify credentials'), while BM25 excels at exact keyword tokens ('login_user'). RRF mathematically fuses their rank positions (1 / (60 + rank)) with a 1.5x boost for exact symbol matches, outperforming either method alone.",
    },
    {
      q: "How does AST Graph Expansion achieve 100% evidence coverage?",
      a: "CodeLens builds a directed NetworkX graph with CALLS and IMPORTS edges. For every top-5 hybrid seed, it traverses 1-hop outgoing callees and incoming callers via BFS, discovering dependent functions across different files that vector search missed.",
    },
    {
      q: "How are hallucinations prevented in the generated answers?",
      a: "Gemini 2.5 Flash is strictly prompted with an evidence envelope containing only the retrieved AST code chunks. Every assertion must cite the exact file and line range [file.py:L1-L2]. An AST validator verifies each cited line before returning the response.",
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 select-none animate-in fade-in duration-150">
      <div className="w-full max-w-3xl max-h-[88vh] rounded-xl bg-zinc-900 border border-zinc-800 shadow-2xl overflow-hidden flex flex-col font-sans">
        {/* Header */}
        <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide">
                CodeLens Architecture & Defense Guide
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Key technical explanations and viva defense questions.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs text-zinc-300 leading-relaxed">
          {faqs.map((faq, idx) => (
            <div key={idx} className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 space-y-2">
              <div className="flex items-start gap-2 text-zinc-100 font-semibold text-sm">
                <HelpCircle className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                <span>{faq.q}</span>
              </div>
              <p className="text-zinc-400 text-xs pl-6">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
