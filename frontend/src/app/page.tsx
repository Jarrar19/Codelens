"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { QueryPane } from "@/components/QueryPane";
import { CodeViewerPane } from "@/components/CodeViewerPane";
import { RepoModal } from "@/components/RepoModal";
import { BenchmarkModal } from "@/components/inspectors/BenchmarkModal";
import { GraphModal } from "@/components/inspectors/GraphModal";
import { VivaModal } from "@/components/inspectors/VivaModal";
import { ToastContainer, ToastMessage } from "@/components/Toast";
import { StatusResponse, QueryResponse, PresetQuery } from "@/lib/types";
import { api } from "@/lib/api";

export default function CodeLensDashboard() {
  // Application State
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [allFiles, setAllFiles] = useState<string[]>([]);
  const [activeFile, setActiveFile] = useState<string>("");
  const [highlightRange, setHighlightRange] = useState<{ start: number; end: number } | null>(null);
  const [referencedFiles, setReferencedFiles] = useState<string[]>([]);
  const [presetQueries, setPresetQueries] = useState<PresetQuery[]>([]);

  // Query & Ingestion Loading States
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [isQuerying, setIsQuerying] = useState<boolean>(false);
  const [isIngesting, setIsIngesting] = useState<boolean>(false);

  // Modals
  const [isRepoModalOpen, setIsRepoModalOpen] = useState<boolean>(false);
  const [isBenchmarkModalOpen, setIsBenchmarkModalOpen] = useState<boolean>(false);
  const [isVivaModalOpen, setIsVivaModalOpen] = useState<boolean>(false);
  const [isGraphModalOpen, setIsGraphModalOpen] = useState<boolean>(false);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((message: string, type: "success" | "error" | "info" = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Fetch initial state & presets on startup
  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
      if (data?.stats?.files && data.stats.files.length > 0) {
        setAllFiles(data.stats.files);
        // Default active file
        if (!activeFile) {
          setActiveFile(data.stats.files[0]);
        }
      }
    } catch (err: any) {
      console.warn("Could not load status from FastAPI:", err);
      addToast("FastAPI backend not responding on port 8000. Ensure server is running.", "error");
    }
  }, [activeFile, addToast]);

  useEffect(() => {
    fetchStatus();

    api
      .getPresetQueries()
      .then((res) => setPresetQueries(res.showcase_queries || []))
      .catch((e) => console.warn("Preset queries load error:", e));
  }, [fetchStatus]);

  // Execute Codebase Query
  const handleRunQuery = async (queryText: string) => {
    setIsQuerying(true);
    setHighlightRange(null);

    try {
      const result = await api.query(queryText, 5, 25);
      setQueryResult(result);

      // Extract unique referenced files from citations & evidence
      const filesFromCitations = Array.from(
        new Set([
          ...(result.citations || []).map((c) => c.file_path),
          ...(result.evidence || []).map((e) => e.file_path),
        ])
      ).filter(Boolean);

      setReferencedFiles(filesFromCitations);

      // Auto-load first cited file and highlight line
      if (result.citations && result.citations.length > 0) {
        const firstCitation = result.citations[0];
        setActiveFile(firstCitation.file_path);
        setHighlightRange({
          start: firstCitation.start_line,
          end: firstCitation.end_line,
        });
      } else if (filesFromCitations.length > 0) {
        setActiveFile(filesFromCitations[0]);
      }

      addToast(`Grounded answer ready with ${result.citation_count} verified citations!`, "success");
    } catch (err: any) {
      console.error("Query execution error:", err);
      addToast(err.message || "Failed to execute query", "error");
    } finally {
      setIsQuerying(false);
    }
  };

  // Handle citation click -> scroll & highlight in CodeViewerPane
  const handleCitationClick = (file: string, start: number, end: number) => {
    setActiveFile(file);
    setHighlightRange({ start, end });
  };

  // Ingest repository (clone or local directory)
  const handleIngest = async (path: string) => {
    setIsIngesting(true);
    try {
      const res = await api.ingestRepository(path);
      if (res.success) {
        await fetchStatus();
        setQueryResult(null);
        setHighlightRange(null);
        addToast(`Repository '${res.stats.repository_name}' ready: ${res.stats.total_chunks} chunks indexed!`, "success");
      }
    } catch (err: any) {
      addToast(err.message || "Repository ingestion failed", "error");
      throw err;
    } finally {
      setIsIngesting(false);
    }
  };

  const handleReindex = async () => {
    if (!status?.repository_path) return;
    await handleIngest(status.repository_path);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Header Bar */}
      <Header
        stats={status?.stats || null}
        onOpenRepoModal={() => setIsRepoModalOpen(true)}
        onOpenBenchmarkModal={() => setIsBenchmarkModalOpen(true)}
        onOpenVivaModal={() => setIsVivaModalOpen(true)}
        onOpenGraphModal={() => setIsGraphModalOpen(true)}
        onReindex={handleReindex}
        isReindexing={isIngesting}
      />

      {/* Main Split-Pane Workspace */}
      <main className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
        {/* Left Pane: Query & Grounded Explanation (50%) */}
        <section className="w-full md:w-1/2 h-1/2 md:h-full flex flex-col min-h-0">
          <QueryPane
            onRunQuery={handleRunQuery}
            isLoading={isQuerying}
            queryResult={queryResult}
            onCitationClick={handleCitationClick}
            presetQueries={presetQueries}
          />
        </section>

        {/* Right Pane: Persistent Code Viewer (50%) */}
        <section className="w-full md:w-1/2 h-1/2 md:h-full flex flex-col min-h-0">
          <CodeViewerPane
            activeFile={activeFile}
            highlightRange={highlightRange}
            onSelectFile={(f) => {
              setActiveFile(f);
              setHighlightRange(null);
            }}
            allFiles={allFiles}
            referencedFiles={referencedFiles}
          />
        </section>
      </main>

      {/* Modals & Overlays */}
      <RepoModal
        isOpen={isRepoModalOpen}
        onClose={() => setIsRepoModalOpen(false)}
        onIngest={handleIngest}
        isIngesting={isIngesting}
        activePath={status?.repository_path || ""}
      />

      <BenchmarkModal
        isOpen={isBenchmarkModalOpen}
        onClose={() => setIsBenchmarkModalOpen(false)}
      />

      <GraphModal
        isOpen={isGraphModalOpen}
        onClose={() => setIsGraphModalOpen(false)}
      />

      <VivaModal
        isOpen={isVivaModalOpen}
        onClose={() => setIsVivaModalOpen(false)}
      />

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
