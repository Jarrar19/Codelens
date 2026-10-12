from typing import List, Dict, Any


class ContextBuilder:
    """
    Builds clean, grounded context for the LLM.

    Input:
        Hybrid RRF results + graph-expanded results

    Output:
        Ordered evidence blocks with file/line citations.
    """

    def __init__(self, max_chars: int = 16000):
        self.max_chars = max_chars

    # =========================================================
    # BUILD CONTEXT
    # =========================================================

    def build(
        self,
        results: List[Dict[str, Any]]
    ) -> str:

        if not results:
            return (
                "No relevant code was found "
                "in the repository."
            )

        # -----------------------------------------------------
        # Remove duplicate chunks
        # -----------------------------------------------------

        unique_results = []
        seen = set()

        for result in results:

            chunk_id = result.get(
                "chunk_id"
            )

            if not chunk_id:
                continue

            if chunk_id in seen:
                continue

            seen.add(chunk_id)
            unique_results.append(result)

        # -----------------------------------------------------
        # Primary evidence first
        # Graph-expanded evidence second
        # -----------------------------------------------------

        primary = [
            result
            for result in unique_results
            if not result.get(
                "graph_expanded",
                False
            )
        ]

        primary = sorted(
            primary,
            key=lambda x: (
                x.get("final_score")
                if x.get("final_score") is not None
                else x.get("rrf_score", 0.0)
            ),
            reverse=True
        )

        graph_context = [
            result
            for result in unique_results
            if result.get(
                "graph_expanded",
                False
            )
        ]

        ordered = primary + graph_context

        # -----------------------------------------------------
        # Build evidence blocks
        # -----------------------------------------------------

        blocks = []

        for index, result in enumerate(
            ordered,
            start=1
        ):

            metadata = result.get(
                "metadata",
                {}
            )

            file_path = metadata.get(
                "file_path",
                "unknown"
            )
            file_path = str(file_path).replace("\\", "/")

            symbol_name = metadata.get(
                "symbol_name",
                "unknown"
            )

            symbol_type = metadata.get(
                "symbol_type",
                "unknown"
            )

            start_line = metadata.get(
                "start_line",
                "?"
            )

            end_line = metadata.get(
                "end_line",
                "?"
            )

            document = result.get(
                "document",
                ""
            )

            is_graph = result.get(
                "graph_expanded",
                False
            )

            if is_graph:

                evidence_type = (
                    "RELATED EVIDENCE"
                )

            else:

                evidence_type = (
                    "PRIMARY EVIDENCE"
                )

            block = (
                f"[{evidence_type} #{index}]\n"
                f"FILE: {file_path}\n"
                f"LINES: {start_line}-{end_line}\n"
                f"SYMBOL: {symbol_name}\n"
                f"TYPE: {symbol_type}\n"
                f"\n"
                f"{document}\n"
            )

            blocks.append(block)

        # -----------------------------------------------------
        # Apply context budget
        # -----------------------------------------------------

        context_parts = []

        current_length = 0

        for block in blocks:

            block_length = len(block)

            if (
                current_length + block_length
                > self.max_chars
            ):
                break

            context_parts.append(
                block
            )

            current_length += (
                block_length
            )

        # -----------------------------------------------------
        # Final context
        # -----------------------------------------------------

        context = (
            "\n"
            + "=" * 60
            + "\n"
            "CODELENS RETRIEVED CONTEXT"
            "\n"
            + "=" * 60
            + "\n\n"
        )

        context += "\n".join(
            context_parts
        )

        return context

    # =========================================================
    # CITATION EXTRACTION
    # =========================================================

    def get_citations(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        citations = []

        seen = set()

        for result in results:

            metadata = result.get(
                "metadata",
                {}
            )

            file_path = metadata.get(
                "file_path"
            )

            start_line = metadata.get(
                "start_line"
            )

            end_line = metadata.get(
                "end_line"
            )

            symbol_name = metadata.get(
                "symbol_name"
            )

            citation_key = (
                file_path,
                start_line,
                end_line,
                symbol_name,
            )

            if citation_key in seen:
                continue

            seen.add(
                citation_key
            )

            citations.append({
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "symbol_name": symbol_name,
            })

        return citations


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    import sys

    from codelens.core.scanner import (
        RepositoryScanner
    )

    from codelens.core.parser import (
        CodeParser
    )

    from codelens.core.vector_store import (
        VectorStore
    )

    from codelens.core.bm25_index import (
        BM25Index
    )

    from codelens.core.graph import (
        DependencyGraph
    )

    from codelens.core.hybrid_retriever import (
        HybridRetriever
    )

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python -m codelens.core.context_builder "
            "<repository_path>"
        )

        sys.exit(1)

    repository_path = sys.argv[1]

    print("=" * 60)
    print("CODELENS CONTEXT BUILDER TEST")
    print("=" * 60)

    # ---------------------------------------------------------
    # Scan
    # ---------------------------------------------------------

    scanner = RepositoryScanner(
        repository_path
    )

    files = scanner.scan()

    print(
        f"\nFiles found: {len(files)}"
    )

    # ---------------------------------------------------------
    # Parse
    # ---------------------------------------------------------

    parser = CodeParser()

    chunks = []

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
    # Build graph
    # ---------------------------------------------------------

    dependency_graph = (
        DependencyGraph(
            repository_path
        )
    )

    dependency_graph.build(
        chunks
    )

    # ---------------------------------------------------------
    # Retriever
    # ---------------------------------------------------------

    retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_index=bm25_index,
        dependency_graph=dependency_graph,
    )

    # ---------------------------------------------------------
    # Query
    # ---------------------------------------------------------

    query = (
        "How does user login work?"
    )

    print(
        f"\nQUERY: {query}"
    )

    results = retriever.search(
        query,
        top_k=5
    )

    print(
        f"\nRetrieved results: "
        f"{len(results)}"
    )

    # ---------------------------------------------------------
    # Build context
    # ---------------------------------------------------------

    builder = ContextBuilder(
        max_chars=16000
    )

    context = builder.build(
        results
    )

    print("\n" + context)

    # ---------------------------------------------------------
    # Citations
    # ---------------------------------------------------------

    citations = (
        builder.get_citations(
            results
        )
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "CITATIONS"
    )

    print(
        "=" * 60
    )

    for citation in citations:

        print(
            f"{citation['file_path']} "
            f"(lines "
            f"{citation['start_line']}-"
            f"{citation['end_line']}) "
            f"→ "
            f"{citation['symbol_name']}"
        )

    print(
        "\n" + "=" * 60
    )

    print(
        "CONTEXT BUILDER TEST COMPLETE"
    )

    print(
        "=" * 60
    )