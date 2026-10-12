# CodeLens: Viva & Project Defense Guide

This comprehensive guide prepares you for any technical, architectural, or algorithmic question an evaluator or professor might ask during a project viva, presentation, or code defense.

---

## 1. High-Level Concept & Motivation

### Q1: What is the core problem CodeLens solves?
**Answer:**
Standard Retrieval-Augmented Generation (RAG) models are designed for unstructured prose (like Wikipedia or support tickets), where information is self-contained in paragraphs. In contrast, software codebases are **relational, modular, and multi-hop**. When a developer asks *"How is a payment processed?"*, the logic spans across `app.py` (HTTP handler) $\rightarrow$ `payments.py` (business logic) $\rightarrow$ `utils.py` (transaction UUID generator) $\rightarrow$ `database.py` (user record lookup).
Standard semantic search finds only the handler because the helper functions do not contain the word *"payment"*. CodeLens integrates **AST parsing, Hybrid Search (Dense + BM25 RRF), and Graph Expansion** to automatically retrieve the entire multi-hop call chain.

### Q2: Why does Naive RAG achieve only 84.9% coverage while CodeLens achieves 100.0%?
**Answer:**
Naive RAG relies solely on embedding cosine similarity. For multi-hop dependencies (such as `generate_transaction_id` or `find_user_by_id`), their vector embeddings have low cosine similarity to the query *"How is payment processed?"*. Thus, they fall outside the top-$k$ cutoff.
CodeLens uses the top hybrid matches as **Seeds** and traverses the **AST Dependency Graph (NetworkX)** to expand 1-hop and 2-hop callers/callees, recovering 100% of all required dependencies.

---

## 2. Parsing & Code Representation

### Q3: Why use Tree-sitter AST parsing instead of fixed-size text chunking (e.g. 500 characters)?
**Answer:**
Fixed-character chunking arbitrarily cuts code across function boundaries, breaking syntactic coherence and separating docstrings, signatures, and variable scopes.
Tree-sitter builds an Abstract Syntax Tree (AST), enabling CodeLens to extract **syntactically complete symbol units** (functions, classes) along with their exact physical line ranges (`start_line`, `end_line`), import declarations, and internal function calls.

### Q4: What information is stored in a `CodeChunk`?
**Answer:**
1. `symbol_name`: Function or class name (e.g. `process_payment`).
2. `symbol_type`: `function`, `class`, or `module`.
3. `file_path`: Relative path (e.g. `payments.py`).
4. `start_line` / `end_line`: 1-indexed source code line coordinates.
5. `code`: The complete raw code block.
6. `imports`: List of modules and imported symbols.
7. `calls`: List of functions invoked inside the block.

---

## 3. Hybrid Retrieval & RRF

### Q5: What is Reciprocal Rank Fusion (RRF) and why is $k=60$ used?
**Answer:**
Dense vector search returns cosine similarity scores (typically $0.0 \dots 1.0$), while BM25 returns unbounded TF-IDF scores (e.g. $0.0 \dots 35.0$). Directly adding or weighting these raw scores is unstable.
RRF converts scores into relative ranks:
$$\text{RRF}(d) = \sum_{m \in \{\text{Vector}, \text{BM25}\}} \frac{1}{k + \text{Rank}_m(d)}$$
The smoothing constant $k=60$ (standardized by Cormack et al.) prevents very high ranks from dominating the score while penalizing items ranked low across both retrievers.

### Q6: How does the Exact-Symbol and Cross-Module Boost work?
**Answer:**
- **Exact Symbol Boost:** If a query contains an exact identifier matching a function name (e.g. query mentions `login_user`), a $+0.005$ boost is added.
- **Cross-Module Call Bridge Boost:** When a query asks about cross-module communication (e.g. *"auth communicating with database"*), CodeLens inspects the AST call list of candidate chunks. A function in `auth.py` that calls `find_user` in `database.py` receives a $+0.020$ boost, elevating it into the primary seed set.

---

## 4. Dependency Graph & Traversal

### Q7: How is the Dependency Graph constructed?
**Answer:**
The graph is a directed multigraph $G = (V, E)$ constructed in NetworkX:
- **Nodes $V$:** File nodes (`file::path`) and Symbol nodes (`symbol::path::name`).
- **Edges $E$:**
  - `CONTAINS`: File $\rightarrow$ Function/Class
  - `IMPORTS`: File $\rightarrow$ Imported Module
  - `CALLS`: Function $A$ $\rightarrow$ Function $B$ (extracted via AST call visitors and mapped to the symbol index).

### Q8: How does graph expansion prevent context explosion?
**Answer:**
Uncontrolled graph traversal could pull the entire repository into context. CodeLens applies strict budget controls:
1. Expansion is restricted to 1-hop neighbors (`CALLS` and `IMPORTS` edges) of the top-$k$ hybrid seeds.
2. The context builder enforces a character limit (16,000 characters) and deduplicates chunks while maintaining rank priority.

---

## 5. Grounding, Citations & LLM Synthesis

### Q9: How does CodeLens prevent Gemini hallucinations?
**Answer:**
1. **System Prompt Constraint:** Gemini is strictly instructed to answer using **only** the provided repository evidence context.
2. **Mandatory Citations:** Gemini must attach exact line-level citations in the format `[filename:start_line-end_line]`.
3. **Automated Verification:** The evaluation pipeline extracts all citation line ranges and validates that the file exists and that the cited line coordinates match the parsed AST chunks. Our benchmark achieved **97.2% Citation Accuracy** and **100% Groundedness**.

### Q10: What happens if the query asks about something not in the codebase?
**Answer:**
The system instruction explicitly mandates: *"If the repository evidence is insufficient to answer the question, state 'The available repository evidence is insufficient to answer this.'"* This guarantees zero fabricated code or fake API assumptions.

---

## 6. Evaluation & Benchmark Results

### Q11: Walk through the key benchmark numbers.
**Answer:**
- **Evidence Coverage:** Naive RAG = **84.9%** vs CodeLens Expanded = **100.0%** ($+15.1\%$ gain).
- **Hit@5:** **100.0%** (all 12 queries retrieve expected seeds in top 5).
- **MRR (Mean Reciprocal Rank):** **0.878** for CodeLens vs **0.917** for Naive RAG (Naive RAG ranks direct lexical matches higher, but CodeLens retrieves complete dependency graphs).
- **Answer Symbol Coverage:** **100.0%** (Gemini explains all cross-file caller/callee symbols).
- **Citation Accuracy:** **97.2%** line-level precision.
- **Grounded Responses:** **100.0%** (zero hallucination or false insufficiency claims).

### Q12: Why is the research insight about MRR vs Coverage important?
**Answer:**
*"Naive RAG ranks direct semantic matches slightly higher on isolated files, but CodeLens retrieves substantially more complete dependency evidence (100% vs 84.9%)."*
This proves that high MRR alone in standard RAG is deceptive for software engineering tasks: a system that accurately finds 1 function but misses its 3 helpers fails to explain how the code actually executes.

---

## 7. Web Application & Engineering

### Q13: What is the stack of the Web Application?
**Answer:**
- **Backend:** FastAPI, Uvicorn, Python 3.12 (REST endpoints: `/api/ingest`, `/api/query`, `/api/file_content`, `/api/graph_data`, `/api/benchmarks`).
- **State Management:** In-memory indexed pipeline persistence (`RepositoryState`) allowing instant multi-turn queries without re-indexing.
- **Frontend:** Vanilla HTML5, CSS3 (Modern dark glassmorphic design system), Vanilla JS (Zero bundler overhead, instant load times).
- **Interactive Features:** Clickable citation pills jumping straight to highlighted code viewer lines, 5-stage pipeline visualizer, 2D dependency graph canvas, live benchmark comparison dashboard.
