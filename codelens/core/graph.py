from pathlib import Path
from typing import Dict, List, Set, Any, Optional

import ast
import networkx as nx

from codelens.core.models import CodeChunk


class DependencyGraph:
    """
    CodeLens dependency graph.

    Nodes:
        - files
        - functions
        - methods
        - classes

    Edges:
        - IMPORTS
        - CALLS

    V1 focuses on relationships that can be resolved
    reliably using static source-code analysis.
    """

    def __init__(self, repository_path: str):

        self.repository_path = Path(
            repository_path
        ).resolve()

        self.graph = nx.DiGraph()

        self.chunks: List[CodeChunk] = []

        self.file_chunks: Dict[
            str, List[CodeChunk]
        ] = {}

        self.symbol_index: Dict[
            str, CodeChunk
        ] = {}

    # =========================================================
    # PATH HELPERS
    # =========================================================

    def relative_path(self, file_path: str) -> str:

        try:

            return str(
                Path(file_path)
                .resolve()
                .relative_to(
                    self.repository_path
                )
            ).replace("\\", "/")

        except ValueError:

            return str(
                Path(file_path)
            ).replace("\\", "/")

    def module_from_file(
        self,
        file_path: str
    ) -> str:

        relative = self.relative_path(
            file_path
        )

        path = Path(relative)

        if path.suffix:

            path = path.with_suffix("")

        return ".".join(
            path.parts
        )

    # =========================================================
    # ADD FILE NODES
    # =========================================================

    def add_file_node(
        self,
        file_path: str
    ):

        relative = self.relative_path(
            file_path
        )

        self.graph.add_node(
            f"file::{relative}",
            node_type="file",
            file_path=relative,
        )

    # =========================================================
    # ADD SYMBOL NODES
    # =========================================================

    def add_symbol_nodes(
        self,
        chunks: List[CodeChunk]
    ):

        for chunk in chunks:

            relative = self.relative_path(
                chunk.file_path
            )

            file_node = (
                f"file::{relative}"
            )

            symbol_node = (
                f"symbol::{relative}::"
                f"{chunk.symbol_name}"
            )

            self.graph.add_node(
                symbol_node,
                node_type="symbol",
                file_path=relative,
                symbol_name=chunk.symbol_name,
                symbol_type=chunk.symbol_type,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
            )

            # Symbol belongs to its file.
            self.graph.add_edge(
                file_node,
                symbol_node,
                edge_type="CONTAINS",
            )

            # Index symbols.
            self.symbol_index[
                chunk.symbol_name
            ] = chunk

    # =========================================================
    # FILE IMPORT RESOLUTION
    # =========================================================

    def resolve_import(
        self,
        source_file: str,
        imported_module: str
    ) -> Optional[str]:
        """
        Try to resolve an imported module to a file
        inside the repository.

        Examples:

            from utils import generate_token
            -> utils.py

            from database import find_user
            -> database.py
        """

        imported_module = (
            imported_module
            .strip()
            .replace("\\", "/")
        )

        # Remove relative import prefix.
        imported_module = (
            imported_module
            .lstrip(".")
        )

        if not imported_module:
            return None

        module_path = Path(
            *imported_module.split(".")
        )

        candidates = [
            module_path.with_suffix(".py"),
            module_path.with_suffix(".js"),
            module_path.with_suffix(".jsx"),
            module_path.with_suffix(".ts"),
            module_path.with_suffix(".tsx"),
        ]

        for candidate in candidates:

            full_path = (
                self.repository_path /
                candidate
            )

            if full_path.exists():

                return self.relative_path(
                    str(full_path)
                )

        # JavaScript relative import handling.
        source_path = Path(
            source_file
        ).resolve()

        if imported_module.startswith(
            ("./", "../")
        ):

            target = (
                source_path.parent /
                imported_module
            )

            candidates = [
                target,
                target.with_suffix(".js"),
                target.with_suffix(".jsx"),
                target.with_suffix(".ts"),
                target.with_suffix(".tsx"),
            ]

            for candidate in candidates:

                if candidate.exists():

                    return self.relative_path(
                        str(candidate)
                    )

        return None

    # =========================================================
    # IMPORT EDGES
    # =========================================================

    def add_import_edges(
        self,
        chunks: List[CodeChunk]
    ):
        """
        Add file-level IMPORTS relationships.

        Imports are stored on CodeChunks by the parser,
        so duplicate processing is avoided.
        """

        processed_files: Set[str] = set()

        for chunk in chunks:

            source_file = str(
                Path(
                    chunk.file_path
                ).resolve()
            )

            if source_file in processed_files:
                continue

            processed_files.add(
                source_file
            )

            source_relative = (
                self.relative_path(
                    source_file
                )
            )

            source_node = (
                f"file::{source_relative}"
            )

            for imported_module in chunk.imports:

                target_relative = (
                    self.resolve_import(
                        source_file,
                        imported_module
                    )
                )

                if not target_relative:
                    continue

                target_node = (
                    f"file::{target_relative}"
                )

                self.graph.add_edge(
                    source_node,
                    target_node,
                    edge_type="IMPORTS",
                    module=imported_module,
                )

    # =========================================================
    # PYTHON CALL EXTRACTION
    # =========================================================

    def extract_python_calls(
        self,
        chunk: CodeChunk
    ) -> List[str]:
        """
        Extract explicit function calls from Python code.

        Examples:

            generate_token(...)
            -> generate_token

            database.find_user(...)
            -> find_user
        """

        calls = []

        try:

            tree = ast.parse(
                chunk.code
            )

        except SyntaxError:

            return calls

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call
            ):
                continue

            function = node.func

            # function()
            if isinstance(
                function,
                ast.Name
            ):

                calls.append(
                    function.id
                )

            # object.function()
            elif isinstance(
                function,
                ast.Attribute
            ):

                calls.append(
                    function.attr
                )

        return sorted(
            set(calls)
        )

    # =========================================================
    # CALL EDGES
    # =========================================================

    def add_call_edges(
        self,
        chunks: List[CodeChunk]
    ):
        """
        Add CALLS relationships when a called symbol can
        be matched to a known CodeChunk.

        This is deliberately conservative.
        """

        for chunk in chunks:

            relative = self.relative_path(
                chunk.file_path
            )

            source_node = (
                f"symbol::{relative}::"
                f"{chunk.symbol_name}"
            )

            if chunk.language != "python":
                continue

            calls = self.extract_python_calls(
                chunk
            )

            for called_name in calls:

                target_chunk = (
                    self.symbol_index.get(
                        called_name
                    )
                )

                if not target_chunk:
                    continue

                target_relative = (
                    self.relative_path(
                        target_chunk.file_path
                    )
                )

                target_node = (
                    f"symbol::{target_relative}::"
                    f"{target_chunk.symbol_name}"
                )

                # Avoid self-calls.
                if source_node == target_node:
                    continue

                self.graph.add_edge(
                    source_node,
                    target_node,
                    edge_type="CALLS",
                    symbol=called_name,
                )

    # =========================================================
    # BUILD GRAPH
    # =========================================================

    def build(
        self,
        chunks: List[CodeChunk]
    ):

        self.chunks = chunks

        self.file_chunks.clear()
        self.symbol_index.clear()

        # -----------------------------------------------------
        # Group chunks by file
        # -----------------------------------------------------

        for chunk in chunks:

            self.file_chunks.setdefault(
                str(chunk.file_path),
                []
            ).append(chunk)

            self.add_file_node(
                chunk.file_path
            )

        # -----------------------------------------------------
        # Symbol nodes
        # -----------------------------------------------------

        self.add_symbol_nodes(
            chunks
        )

        # -----------------------------------------------------
        # Import edges
        # -----------------------------------------------------

        self.add_import_edges(
            chunks
        )

        # -----------------------------------------------------
        # Call edges
        # -----------------------------------------------------

        self.add_call_edges(
            chunks
        )

        return self.graph

    # =========================================================
    # GRAPH STATISTICS
    # =========================================================

    def statistics(self) -> Dict[str, int]:

        nodes = list(
            self.graph.nodes(data=True)
        )

        files = sum(
            1
            for _, data in nodes
            if data.get("node_type") == "file"
        )

        symbols = sum(
            1
            for _, data in nodes
            if data.get("node_type") == "symbol"
        )

        imports = sum(
            1
            for _, _, data in
            self.graph.edges(data=True)
            if data.get("edge_type") == "IMPORTS"
        )

        calls = sum(
            1
            for _, _, data in
            self.graph.edges(data=True)
            if data.get("edge_type") == "CALLS"
        )

        contains = sum(
            1
            for _, _, data in
            self.graph.edges(data=True)
            if data.get("edge_type") == "CONTAINS"
        )

        return {
            "file_nodes": files,
            "symbol_nodes": symbols,
            "import_edges": imports,
            "imports_edges": imports,
            "call_edges": calls,
            "calls_edges": calls,
            "contains_edges": contains,
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
        }

    # =========================================================
    # DISPLAY GRAPH
    # =========================================================

    def print_graph(self):

        print("\n" + "=" * 60)
        print("DEPENDENCY GRAPH")
        print("=" * 60)

        for source, target, data in (
            self.graph.edges(data=True)
        ):

            edge_type = data.get(
                "edge_type",
                "UNKNOWN"
            )

            print(
                f"\n{source}"
                f"\n   --[{edge_type}]-->"
                f"\n{target}"
            )

    # =========================================================
    # CONTEXT EXPANSION
    # =========================================================

    def expand_context(
        self,
        seed_chunk_ids: List[str],
        max_hops: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Expand context around seed chunks in BOTH directions.

        Incoming edges:
            caller -> seed

        Outgoing edges:
            seed -> callee

        This allows CodeLens to discover both:
            - where a function is used
            - what a function depends on
        """

        if max_hops < 1:
            return []

        seed_nodes = []

        # ---------------------------------------------------------
        # Convert chunk IDs to graph symbol nodes
        # ---------------------------------------------------------

        for chunk in self.chunks:

            if chunk.chunk_id not in seed_chunk_ids:
                continue

            relative = self.relative_path(
                chunk.file_path
            )

            node = (
                f"symbol::{relative}::"
                f"{chunk.symbol_name}"
            )

            if node in self.graph:
                seed_nodes.append(node)

        seed_set = set(seed_nodes)

        # ---------------------------------------------------------
        # BFS in both directions
        # ---------------------------------------------------------

        visited = set(seed_nodes)

        queue = [
            (node, 0)
            for node in seed_nodes
        ]

        while queue:

            current, depth = queue.pop(0)

            if depth >= max_hops:
                continue

            # Outgoing = callees / dependencies
            outgoing = list(
                self.graph.successors(current)
            )

            # Incoming = callers
            incoming = list(
                self.graph.predecessors(current)
            )

            neighbors = outgoing + incoming

            for neighbor in neighbors:

                if neighbor in visited:
                    continue

                visited.add(neighbor)

                queue.append(
                    (
                        neighbor,
                        depth + 1
                    )
                )

        # ---------------------------------------------------------
        # Convert graph nodes back to chunks
        # ---------------------------------------------------------

        expanded = []

        for node in visited:

            if not node.startswith("symbol::"):
                continue

            data = self.graph.nodes[node]

            expanded.append({
                "node": node,
                "file_path": data.get(
                    "file_path"
                ),
                "symbol_name": data.get(
                    "symbol_name"
                ),
                "symbol_type": data.get(
                    "symbol_type"
                ),
                "start_line": data.get(
                    "start_line"
                ),
                "end_line": data.get(
                    "end_line"
                ),
                "is_seed": node in seed_set,
            })

        return expanded


# =============================================================
# TEST PROGRAM
# =============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print("Usage:")
        print(
            "python -m codelens.core.graph "
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
    print("CODELENS DEPENDENCY GRAPH TEST")
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
    # Statistics
    # ---------------------------------------------------------

    stats = (
        dependency_graph.statistics()
    )

    print("\nGraph statistics:")
    print("-" * 40)

    for key, value in stats.items():

        print(
            f"{key}: {value}"
        )

    # ---------------------------------------------------------
    # Print relationships
    # ---------------------------------------------------------

    dependency_graph.print_graph()

    print("\n" + "=" * 60)
    print("GRAPH TEST COMPLETE")
    print("=" * 60)