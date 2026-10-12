"use client";

import React, { useEffect, useRef, useState } from "react";
import { FileContentResponse } from "@/lib/types";
import { api } from "@/lib/api";
import { FileCode, Hash, ListFilter, Copy, Check, ChevronDown } from "lucide-react";

interface CodeViewerPaneProps {
  activeFile: string;
  highlightRange: { start: number; end: number } | null;
  onSelectFile: (file: string) => void;
  allFiles: string[];
  referencedFiles: string[];
}

export const CodeViewerPane: React.FC<CodeViewerPaneProps> = ({
  activeFile,
  highlightRange,
  onSelectFile,
  allFiles,
  referencedFiles,
}) => {
  const [fileData, setFileData] = useState<FileContentResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const lineRefs = useRef<{ [key: number]: HTMLDivElement | null }>({});
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Load file content whenever activeFile changes
  useEffect(() => {
    if (!activeFile) return;

    let isMounted = true;
    setIsLoading(true);

    api
      .getFileContent(activeFile)
      .then((data) => {
        if (isMounted) {
          setFileData(data);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to load file:", err);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [activeFile]);

  // Auto-scroll to highlighted range
  useEffect(() => {
    if (!highlightRange || !fileData) return;

    const timer = setTimeout(() => {
      const targetEl = lineRefs.current[highlightRange.start];
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 120);

    return () => clearTimeout(timer);
  }, [highlightRange, fileData]);

  const handleCopyCode = () => {
    if (!fileData) return;
    navigator.clipboard.writeText(fileData.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = fileData ? fileData.content.split("\n") : [];

  return (
    <div className="flex flex-col h-full bg-zinc-950 border-l border-zinc-800 text-zinc-200 select-text overflow-hidden">
      {/* Top File Switcher Bar */}
      <div className="h-11 border-b border-zinc-800 bg-zinc-900/60 flex items-center justify-between px-3 gap-2 flex-shrink-0">
        <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
          {referencedFiles.length > 0 ? (
            referencedFiles.map((file) => (
              <button
                key={file}
                onClick={() => onSelectFile(file)}
                className={`px-2.5 py-1 text-xs font-mono rounded border transition flex items-center gap-1.5 whitespace-nowrap ${
                  activeFile === file
                    ? "bg-zinc-800 text-blue-400 border-zinc-700 font-semibold shadow-xs"
                    : "bg-zinc-950/60 text-zinc-400 border-zinc-800/80 hover:text-zinc-200 hover:border-zinc-700"
                }`}
              >
                <FileCode className="w-3 h-3" />
                <span>{file.split("/").pop()}</span>
              </button>
            ))
          ) : (
            <div className="text-xs text-zinc-500 font-mono flex items-center gap-1">
              <FileCode className="w-3.5 h-3.5" />
              <span>Source Code Viewer</span>
            </div>
          )}

          {/* All Files Dropdown */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="px-2 py-1 text-xs font-mono rounded border border-zinc-800 bg-zinc-950/80 hover:border-zinc-700 text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
              title="Browse all repository files"
            >
              <ListFilter className="w-3 h-3" />
              <span>Files</span>
              <ChevronDown className="w-3 h-3" />
            </button>

            {dropdownOpen && (
              <div className="absolute left-0 top-full mt-1 w-64 max-h-60 overflow-y-auto bg-zinc-900 border border-zinc-700 rounded-md shadow-2xl z-50 py-1">
                <div className="px-2 py-1 text-[10px] text-zinc-400 font-bold uppercase tracking-wider border-b border-zinc-800">
                  Repository Files ({allFiles.length})
                </div>
                {allFiles.map((f) => (
                  <button
                    key={f}
                    onClick={() => {
                      onSelectFile(f);
                      setDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs font-mono truncate hover:bg-zinc-800 flex items-center gap-2 ${
                      f === activeFile ? "text-blue-400 font-bold bg-zinc-850" : "text-zinc-300"
                    }`}
                  >
                    <FileCode className="w-3.5 h-3.5 flex-shrink-0 text-zinc-500" />
                    <span className="truncate">{f}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Info: Line Count & Copy */}
        <div className="flex items-center gap-2 flex-shrink-0 text-xs text-zinc-400 font-mono">
          {highlightRange && (
            <span className="px-2 py-0.5 rounded bg-blue-950/80 border border-blue-800/80 text-blue-300 text-[11px] font-semibold">
              Lines {highlightRange.start}–{highlightRange.end}
            </span>
          )}
          {fileData && (
            <span className="hidden sm:inline text-zinc-500">
              {fileData.total_lines} lines
            </span>
          )}
          <button
            onClick={handleCopyCode}
            disabled={!fileData}
            className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white transition disabled:opacity-40"
            title="Copy entire file"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Code Editor Body */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto font-mono text-[12.5px] leading-relaxed relative bg-[#09090b]"
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-xs text-zinc-500">
            <div className="flex items-center gap-2">
              <div className="w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span>Loading source lines for {activeFile}...</span>
            </div>
          </div>
        ) : !fileData ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-6 text-zinc-500">
            <FileCode className="w-10 h-10 mb-3 text-zinc-700" />
            <p className="text-sm text-zinc-400 font-sans font-medium mb-1">Source Code Viewer</p>
            <p className="text-xs max-w-sm text-zinc-500 font-sans">
              Click any citation pill on the left (e.g. <span className="font-mono text-emerald-400">[file.py:L10]</span>) or select a file to inspect its exact source lines.
            </p>
          </div>
        ) : (
          <div className="py-2 min-w-full inline-block">
            {lines.map((lineText, idx) => {
              const lineNum = idx + 1;
              const isHighlighted =
                highlightRange &&
                lineNum >= highlightRange.start &&
                lineNum <= highlightRange.end;

              return (
                <div
                  key={lineNum}
                  ref={(el) => {
                    lineRefs.current[lineNum] = el;
                  }}
                  className={`flex items-start px-2 py-0.5 hover:bg-zinc-900/60 transition-colors ${
                    isHighlighted ? "code-line-highlight" : ""
                  }`}
                >
                  {/* Line Number Gutter */}
                  <span
                    className={`w-10 select-none text-right pr-4 flex-shrink-0 text-xs font-mono ${
                      isHighlighted ? "text-blue-400 font-bold" : "text-zinc-600"
                    }`}
                  >
                    {lineNum}
                  </span>

                  {/* Code Line Content */}
                  <span className="whitespace-pre flex-1 text-zinc-200">
                    {lineText || " "}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
