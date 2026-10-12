import re
from pathlib import Path
from typing import List, Dict, Any

from codelens.core.models import CodeChunk
from codelens.core.vector_store import VectorStore
from codelens.core.bm25_index import BM25Index
from codelens.core.graph import DependencyGraph


class HybridRetriever:
    """
    Combines semantic vector search and BM25 keyword search
    using Reciprocal Rank Fusion (RRF).

    Vector Search:
        Understands semantic meaning.

    BM25:
        Understands exact code identifiers and keywords.

    RRF:
        Combines their rankings without comparing their
        incompatible raw scores.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        dependency_graph: DependencyGraph,
        rrf_k: int = 60,
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.dependency_graph = dependency_graph
        self.rrf_k = rrf_k

    # =========================================================
    # RRF SCORE
    # =========================================================

    def calculate_rrf_score(
        self,
        rank: int
    ) -> float:
        """
        Reciprocal Rank Fusion score.

        Formula:

            RRF(d) = 1 / (k + rank)
        """

        return 1.0 / (
            self.rrf_k + rank
        )

    # =========================================================
    # EXACT MATCH BOOST
    # =========================================================

    def calculate_exact_match_boost(
        self,
        query: str,
        chunk: Any
    ) -> float:
        """
        Give a ranking boost when the query directly
        matches a code symbol, component identifiers, or relevant module.

        This improves precision for queries such as:
        generate_token
        Where is the authentication token generated?
        How does user login work?
        How does authentication communicate with the database?
        validate_email
        """

        if hasattr(chunk, "code"):
            code_text = chunk.code
            metadata = {
                "symbol_name": chunk.symbol_name,
                "file_path": chunk.file_path,
                "imports": ", ".join(chunk.imports) if isinstance(chunk.imports, list) else str(chunk.imports),
            }
        elif isinstance(chunk, dict):
            metadata = chunk.get("metadata", chunk)
            code_text = chunk.get("document", "") or chunk.get("code", "") or metadata.get("code", "")
        else:
            metadata = {}
            code_text = ""

        query_normalized = query.strip().lower()
        symbol = str(
            metadata.get("symbol_name", "")
        ).lower()

        if not query_normalized or not symbol:
            return 0.0

        boost = 0.0

        # Exact symbol match
        if query_normalized == symbol:
            boost += 0.010

        query_words = set(re.findall(r"\w+", query_normalized))
        symbol_clean = symbol.replace(".", "_")

        # Direct identifier contained in query
        if symbol_clean in query_normalized or symbol in query_words:
            boost += 0.008
        else:
            # All significant subwords of symbol exist in query words
            symbol_tokens = [t for t in symbol_clean.split("_") if len(t) > 2]
            if symbol_tokens and all(
                token in query_words or any(token in qw for qw in query_words)
                for token in symbol_tokens
            ):
                boost += 0.005

        # Relevant file module match (e.g. "auth" for "authentication", "database" for "database")
        file_path = str(metadata.get("file_path", "")).lower()
        file_base = Path(file_path).stem.replace("_", "")
        if file_base and len(file_base) >= 4 and any(
            file_base in qw or qw in file_base for qw in query_words if len(qw) >= 4
        ):
            boost += 0.003

        # Cross-module import match (e.g. auth importing database when query mentions both)
        imports_str = str(metadata.get("imports", "")).lower()
        if imports_str:
            for qw in query_words:
                if len(qw) >= 4 and (qw in imports_str or any(qw.startswith(p) for p in imports_str.split(","))):
                    boost += 0.004
                    break

        # Cross-file function call boost: if this function calls a function in another module that matches query terms
        if hasattr(self, "dependency_graph") and self.dependency_graph and code_text:
            try:
                tree = ast.parse(code_text)
                calls = [
                    n.func.id if isinstance(n.func, ast.Name) else (n.func.attr if isinstance(n.func, ast.Attribute) else None)
                    for n in ast.walk(tree) if isinstance(n, ast.Call)
                ]
                for called in filter(None, calls):
                    target = self.dependency_graph.symbol_index.get(called)
                    if target and str(target.file_path) != str(metadata.get("file_path", "")):
                        target_file = str(target.file_path).lower()
                        for qw in query_words:
                            if len(qw) >= 4 and qw in target_file:
                                boost += 0.020
                                break
            except Exception:
                pass

        return boost

    # =========================================================
    # HYBRID SEARCH
    # =========================================================

    def _search_with_stages(
        self,
        query: str,
        top_k: int = 5,
        retrieval_k: int = 25,
    ) -> Dict[str, Any]:
        """
        Perform hybrid retrieval.

        Steps:

        1. Run vector search.
        2. Run BM25 search.
        3. Convert rankings into RRF scores.
        4. Merge results.
        5. Sort by combined RRF score.
        """

        # -----------------------------------------------------
        # Vector search
        # -----------------------------------------------------

        vector_results = self.vector_store.search(
            query=query,
            top_k=retrieval_k,
        )

        # -----------------------------------------------------
        # BM25 search
        # -----------------------------------------------------

        bm25_results = self.bm25_index.search(
            query=query,
            top_k=retrieval_k,
        )

        # -----------------------------------------------------
        # Combined result dictionary
        # -----------------------------------------------------

        combined = {}

        # -----------------------------------------------------
        # Add vector results
        # -----------------------------------------------------

        for rank, result in enumerate(
            vector_results,
            start=1
        ):

            chunk_id = result["chunk_id"]

            if chunk_id not in combined:

                combined[chunk_id] = {
                    "chunk_id": chunk_id,
                    "rrf_score": 0.0,
                    "vector_rank": None,
                    "bm25_rank": None,
                    "vector_score": None,
                    "bm25_score": None,
                    "metadata": result["metadata"],
                    "document": result["document"],
                }

            combined[chunk_id][
                "vector_rank"
            ] = rank

            combined[chunk_id][
                "vector_score"
            ] = result["distance"]

            combined[chunk_id][
                "rrf_score"
            ] += self.calculate_rrf_score(
                rank
            )

        # -----------------------------------------------------
        # Add BM25 results
        # -----------------------------------------------------

        for rank, result in enumerate(
            bm25_results,
            start=1
        ):

            chunk_id = result["chunk_id"]

            if chunk_id not in combined:

                chunk = result["chunk"]

                combined[chunk_id] = {
                    "chunk_id": chunk_id,
                    "rrf_score": 0.0,
                    "vector_rank": None,
                    "bm25_rank": None,
                    "vector_score": None,
                    "bm25_score": None,
                    "metadata": {
                        "file_path": chunk.file_path,
                        "language": chunk.language,
                        "symbol_name": chunk.symbol_name,
                        "symbol_type": chunk.symbol_type,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "imports": ", ".join(
                            chunk.imports
                        ),
                    },
                    "document": chunk.searchable_text(),
                }

            combined[chunk_id][
                "bm25_rank"
            ] = rank

            combined[chunk_id][
                "bm25_score"
            ] = result["score"]

            combined[chunk_id][
                "rrf_score"
            ] += self.calculate_rrf_score(
                rank
            )

        # -----------------------------------------------------
        # Exact symbol boost
        # -----------------------------------------------------

        for result in combined.values():

            result["exact_match_boost"] = (
                self.calculate_exact_match_boost(
                    query,
                    result
                )
            )

            result["final_score"] = (
                result["rrf_score"]
                + result["exact_match_boost"]
            )

        # -----------------------------------------------------
        # Sort by final score
        # -----------------------------------------------------

        ranked_results = sorted(
            combined.values(),
            key=lambda x: x["final_score"],
            reverse=True
        )

        # ---------------------------------------------------------
        # Select hybrid seeds
        # ---------------------------------------------------------

        seed_results = ranked_results[:top_k]

        seed_chunk_ids = [
            result["chunk_id"]
            for result in seed_results
        ]

        # ---------------------------------------------------------
        # Graph expansion
        # ---------------------------------------------------------

        graph_results = (
            self.dependency_graph.expand_context(
                seed_chunk_ids=seed_chunk_ids,
                max_hops=1,
            )
        )

        # ---------------------------------------------------------
        # Existing results lookup
        # ---------------------------------------------------------

        result_lookup = {
            result["chunk_id"]: result
            for result in seed_results
        }

        # ---------------------------------------------------------
        # Add graph context
        # ---------------------------------------------------------

        graph_context = []

        for graph_result in graph_results:

            file_path = graph_result["file_path"]
            symbol_name = graph_result["symbol_name"]

            matching_chunk = None

            for chunk in self.dependency_graph.chunks:

                relative = (
                    self.dependency_graph.relative_path(
                        chunk.file_path
                    )
                )

                if (
                    relative == file_path
                    and chunk.symbol_name == symbol_name
                ):
                    matching_chunk = chunk
                    break

            if matching_chunk is None:
                continue

            chunk_id = matching_chunk.chunk_id

            # Already present in RRF results
            if chunk_id in result_lookup:

                result_lookup[chunk_id][
                    "graph_expanded"
                ] = not graph_result["is_seed"]

                continue

            # -----------------------------------------------------
            # Graph-only context
            # -----------------------------------------------------

            graph_context.append({
                "chunk_id": chunk_id,

                "rrf_score": 0.0,

                "vector_rank": None,
                "bm25_rank": None,

                "vector_score": None,
                "bm25_score": None,

                "graph_expanded": True,

                "metadata": {
                    "file_path": file_path,
                    "language": matching_chunk.language,
                    "symbol_name": symbol_name,
                    "symbol_type": matching_chunk.symbol_type,
                    "start_line": matching_chunk.start_line,
                    "end_line": matching_chunk.end_line,
                    "imports": ", ".join(
                        matching_chunk.imports
                    ),
                },

                "document": (
                    matching_chunk.searchable_text()
                ),
            })

        # ---------------------------------------------------------
        # Final RRF results
        # ---------------------------------------------------------

        final_results = []

        for rank, result in enumerate(
            seed_results,
            start=1
        ):

            result["rank"] = rank

            if "graph_expanded" not in result:
                result["graph_expanded"] = False

            final_results.append(
                result
            )

        # ---------------------------------------------------------
        # Append graph context
        # ---------------------------------------------------------

        for graph_result in graph_context:

            graph_result["rank"] = (
                len(final_results) + 1
            )

            final_results.append(
                graph_result
            )

        return {
            "seeds": seed_results,
            "graph_context": graph_context,
            "final_results": final_results,
        }

    # =========================================================
    # PUBLIC SEARCH INTERFACES
    # =========================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        retrieval_k: int = 25,
    ) -> List[Dict[str, Any]]:
        stages = self._search_with_stages(
            query=query,
            top_k=top_k,
            retrieval_k=retrieval_k,
        )

        return stages["final_results"]

    def search_stages(
        self,
        query: str,
        top_k: int = 5,
        retrieval_k: int = 25,
    ) -> Dict[str, Any]:
        return self._search_with_stages(
            query=query,
            top_k=top_k,
            retrieval_k=retrieval_k,
        )


# =============================================================
# TEST PROGRAM
# =============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print("Usage:")
        print(
            "python -m codelens.core.hybrid_retriever "
            "<repository_path>"
        )

        sys.exit(1)

    repository_path = sys.argv[1]

    from codelens.core.scanner import (
        RepositoryScanner
    )

    from codelens.core.parser import (
        CodeParser
    )

    print("=" * 60)
    print("CODELENS HYBRID RETRIEVAL TEST")
    print("=" * 60)

    # ---------------------------------------------------------
    # Scan repository
    # ---------------------------------------------------------

    scanner = RepositoryScanner(
        repository_path
    )

    files = scanner.scan()

    print(
        f"\nFiles found: {len(files)}"
    )

    # ---------------------------------------------------------
    # Parse repository
    # ---------------------------------------------------------

    parser = CodeParser()

    chunks: List[CodeChunk] = []

    for file_path in files:

        chunks.extend(
            parser.parse_file(
                file_path
            )
        )

    print(
        f"Code chunks found: {len(chunks)}"
    )

    # ---------------------------------------------------------
    # Build vector store
    # ---------------------------------------------------------

    vector_store = VectorStore()

    vector_store.clear()

    vector_store.add_chunks(
        chunks
    )

    # ---------------------------------------------------------
    # Build BM25
    # ---------------------------------------------------------

    bm25_index = BM25Index()

    bm25_index.build(
        chunks
    )

    # ---------------------------------------------------------
    # Build Graph
    # ---------------------------------------------------------

    dependency_graph = DependencyGraph(
        repository_path
    )

    dependency_graph.build(
        chunks
    )

    # ---------------------------------------------------------
    # Create hybrid retriever
    # ---------------------------------------------------------

    retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_index=bm25_index,
        dependency_graph=dependency_graph,
    )

    # ---------------------------------------------------------
    # Test queries
    # ---------------------------------------------------------

    queries = [
        "generate_token",
        "Where is the authentication token generated?",
        "How does user login work?",
        "How does authentication communicate with the database?",
        "process payment",
        "send welcome email",
        "generate report",
        "validate email",
    ]

    for query in queries:

        print("\n" + "=" * 60)
        print(
            f"QUERY: {query}"
        )
        print("=" * 60)

        results = retriever.search(
            query=query,
            top_k=5,
            retrieval_k=10,
        )

        for result in results:

            metadata = result[
                "metadata"
            ]

            print(
                f"\n[{result['rank']}] "
                f"{metadata['file_path']}"
            )

            print(
                f"Symbol: "
                f"{metadata['symbol_name']}"
            )

            print(
                f"Type: "
                f"{metadata['symbol_type']}"
            )

            print(
                f"Lines: "
                f"{metadata['start_line']}-"
                f"{metadata['end_line']}"
            )

            print(
                f"Vector Rank: "
                f"{result['vector_rank']}"
            )

            print(
                f"BM25 Rank: "
                f"{result['bm25_rank']}"
            )

            print(
                f"RRF Score: "
                f"{result['rrf_score']:.6f}"
            )

            print(
                f"Exact Boost: "
                f"{result.get('exact_match_boost', 0.0):.6f}"
            )

            print(
                f"Final Score: "
                f"{result.get('final_score', result['rrf_score']):.6f}"
            )

            print(
                f"Graph Expanded: "
                f"{result['graph_expanded']}"
            )

    print("\n" + "=" * 60)
    print("HYBRID RETRIEVAL TEST COMPLETE")
    print("=" * 60)