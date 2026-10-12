"use client";

import React, { useEffect, useRef, useState } from "react";
import { GraphDataResponse } from "@/lib/types";
import { api } from "@/lib/api";
import { X, GitBranch, Share2 } from "lucide-react";

interface GraphModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const GraphModal: React.FC<GraphModalProps> = ({ isOpen, onClose }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [graphData, setGraphData] = useState<GraphDataResponse | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    api.getGraphData().then(setGraphData).catch(console.error);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !graphData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Handle high DPI
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    canvas.width = width * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Clear
    ctx.fillStyle = "#09090b";
    ctx.fillRect(0, 0, width, height);

    const nodes = graphData.nodes || [];
    const edges = graphData.edges || [];
    const numNodes = nodes.length;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.38;

    const nodePositions: { [key: string]: { x: number; y: number; node: any } } = {};

    nodes.forEach((node, i) => {
      const angle = (i / numNodes) * 2 * Math.PI;
      nodePositions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        node: node,
      };
    });

    // Draw Edges
    ctx.lineWidth = 1;
    edges.forEach((e) => {
      const p1 = nodePositions[e.source];
      const p2 = nodePositions[e.target];
      if (p1 && p2) {
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        if (e.relation === "CALLS") {
          ctx.strokeStyle = "rgba(6, 182, 212, 0.5)"; // cyan
        } else if (e.relation === "IMPORTS") {
          ctx.strokeStyle = "rgba(245, 158, 11, 0.5)"; // amber
        } else {
          ctx.strokeStyle = "rgba(113, 113, 122, 0.25)"; // slate
        }
        ctx.stroke();
      }
    });

    // Draw Nodes
    nodes.forEach((node) => {
      const pos = nodePositions[node.id];
      if (!pos) return;

      ctx.beginPath();
      ctx.arc(pos.x, pos.y, node.type === "file" ? 5 : 4, 0, 2 * Math.PI);

      if (node.type === "file") {
        ctx.fillStyle = "#a855f7"; // purple
      } else {
        ctx.fillStyle = "#3b82f6"; // blue
      }
      ctx.fill();

      // Labels
      if (node.type === "file" || numNodes < 40) {
        ctx.fillStyle = "#a1a1aa";
        ctx.font = "10px ui-monospace, SFMono-Regular, monospace";
        ctx.fillText(node.label || node.id, pos.x + 7, pos.y + 3);
      }
    });
  }, [isOpen, graphData]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 select-none animate-in fade-in duration-150">
      <div className="w-full max-w-4xl max-h-[88vh] rounded-xl bg-zinc-900 border border-zinc-800 shadow-2xl overflow-hidden flex flex-col font-sans">
        {/* Header */}
        <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Share2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                <span>AST Dependency Graph Inspector</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono border border-zinc-700">
                  NetworkX Multi-Hop
                </span>
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Functions, classes, and cross-file CALLS and IMPORTS edges.
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

        {/* Telemetry Bar & Legend */}
        <div className="px-5 py-2.5 border-b border-zinc-800 bg-zinc-950/60 flex items-center justify-between text-xs font-mono text-zinc-400 flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <span>
              <strong className="text-white">{graphData?.nodes?.length || 0}</strong> Nodes
            </span>
            <span>•</span>
            <span>
              <strong className="text-white">{graphData?.edges?.length || 0}</strong> Edges
            </span>
            <span>•</span>
            <span>
              <strong className="text-cyan-400">{graphData?.stats?.call_edges || 0}</strong> Calls
            </span>
            <span>•</span>
            <span>
              <strong className="text-amber-400">{graphData?.stats?.import_edges || 0}</strong> Imports
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px]">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500 inline-block" /> File Node
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" /> Symbol Node
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-cyan-400 inline-block" /> CALLS Edge
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-amber-400 inline-block" /> IMPORTS Edge
            </span>
          </div>
        </div>

        {/* Canvas Container */}
        <div className="flex-1 w-full h-[500px] relative bg-[#09090b]">
          <canvas ref={canvasRef} className="w-full h-full block" />
        </div>
      </div>
    </div>
  );
};
