from pathlib import Path
import re
from typing import List, Optional, Set

from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript

from codelens.core.models import CodeChunk


class CodeParser:
    """
    Tree-sitter based parser for Python and JavaScript/TypeScript.

    Extracts:
    - Functions
    - Classes
    - Methods
    - Imports
    - Line numbers
    - Qualified symbol names
    """

    def __init__(self):

        self.parsers = {}

        # -----------------------------------------------------
        # Python
        # -----------------------------------------------------

        python_language = Language(
            tree_sitter_python.language()
        )

        self.parsers[".py"] = Parser(
            python_language
        )

        # -----------------------------------------------------
        # JavaScript / TypeScript
        # -----------------------------------------------------

        javascript_language = Language(
            tree_sitter_javascript.language()
        )

        javascript_parser = Parser(
            javascript_language
        )

        self.parsers[".js"] = javascript_parser
        self.parsers[".jsx"] = javascript_parser
        self.parsers[".ts"] = javascript_parser
        self.parsers[".tsx"] = javascript_parser

    # =========================================================
    # GENERAL HELPERS
    # =========================================================

    def get_parser(self, file_path):

        extension = Path(
            file_path
        ).suffix.lower()

        return self.parsers.get(extension)

    def read_file(self, file_path):

        try:

            return Path(file_path).read_text(
                encoding="utf-8",
                errors="ignore"
            )

        except Exception as e:

            print(
                f"Could not read {file_path}: {e}"
            )

            return ""

    def get_node_text(
        self,
        source_bytes,
        node
    ):

        return source_bytes[
            node.start_byte:node.end_byte
        ].decode(
            "utf-8",
            errors="ignore"
        )

    # =========================================================
    # PYTHON IMPORT EXTRACTION
    # =========================================================

    def extract_python_imports(
        self,
        root_node,
        source_bytes
    ):

        imports = []

        def walk(node):

            # ---------------------------------------------
            # import utils
            # import utils.helpers
            # ---------------------------------------------

            if node.type == "import_statement":

                text = self.get_node_text(
                    source_bytes,
                    node
                )

                text = text.replace(
                    "import",
                    "",
                    1
                ).strip()

                for item in text.split(","):

                    item = item.strip()

                    if " as " in item:
                        item = item.split(
                            " as "
                        )[0].strip()

                    if item:
                        imports.append(item)

            # ---------------------------------------------
            # from utils import generate_token
            # ---------------------------------------------

            elif node.type == "import_from_statement":

                module_name = None

                for child in node.children:

                    if child.type in {
                        "dotted_name",
                        "identifier",
                    }:

                        module_name = (
                            self.get_node_text(
                                source_bytes,
                                child
                            )
                        )

                        break

                if module_name:
                    imports.append(module_name)

            for child in node.children:
                walk(child)

        walk(root_node)

        return sorted(
            set(imports)
        )

    # =========================================================
    # JAVASCRIPT IMPORT EXTRACTION
    # =========================================================

    def extract_javascript_imports(
        self,
        root_node,
        source_bytes
    ):

        imports = []

        def walk(node):

            # ---------------------------------------------
            # import ... from "./auth"
            # ---------------------------------------------

            if node.type == "import_statement":

                text = self.get_node_text(
                    source_bytes,
                    node
                )

                # Try to find quoted module path
                for child in node.children:

                    if child.type == "string":

                        module = (
                            self.get_node_text(
                                source_bytes,
                                child
                            )
                        )

                        module = (
                            module
                            .strip("'\"")
                        )

                        imports.append(module)

            # ---------------------------------------------
            # require("./auth")
            # ---------------------------------------------

            elif node.type == "call_expression":

                function_node = node.child_by_field_name(
                    "function"
                )

                arguments_node = node.child_by_field_name(
                    "arguments"
                )

                if function_node:

                    function_name = (
                        self.get_node_text(
                            source_bytes,
                            function_node
                        )
                    )

                    if function_name == "require":

                        if arguments_node:

                            for child in arguments_node.children:

                                if child.type == "string":

                                    module = (
                                        self.get_node_text(
                                            source_bytes,
                                            child
                                        )
                                    )

                                    module = (
                                        module
                                        .strip("'\"")
                                    )

                                    imports.append(module)

            for child in node.children:
                walk(child)

        walk(root_node)

        return sorted(
            set(imports)
        )

    # =========================================================
    # PYTHON CHUNK EXTRACTION
    # =========================================================

    def extract_python_chunks(
        self,
        root_node,
        source_bytes,
        file_path
    ):

        chunks = []

        imports = self.extract_python_imports(
            root_node,
            source_bytes
        )

        def walk(
            node,
            class_context=None
        ):

            # -------------------------------------------------
            # Class
            # -------------------------------------------------

            if node.type == "class_definition":

                name = None

                for child in node.children:

                    if child.type == "identifier":

                        name = self.get_node_text(
                            source_bytes,
                            child
                        )

                        break

                name = name or "anonymous"

                chunks.append(
                    CodeChunk(
                        chunk_id=(
                            f"{file_path}::{name}"
                        ),
                        file_path=str(file_path),
                        language="python",
                        symbol_name=name,
                        symbol_type="class",
                        start_line=(
                            node.start_point[0] + 1
                        ),
                        end_line=(
                            node.end_point[0] + 1
                        ),
                        code=self.get_node_text(
                            source_bytes,
                            node
                        ),
                        imports=imports,
                    )
                )

                # Continue inside class
                for child in node.children:

                    walk(
                        child,
                        class_context=name
                    )

                return

            # -------------------------------------------------
            # Function / Method
            # -------------------------------------------------

            if node.type == "function_definition":

                name = None

                for child in node.children:

                    if child.type == "identifier":

                        name = self.get_node_text(
                            source_bytes,
                            child
                        )

                        break

                name = name or "anonymous"

                if class_context:

                    symbol_name = (
                        f"{class_context}.{name}"
                    )

                    symbol_type = "method"

                else:

                    symbol_name = name
                    symbol_type = "function"

                chunks.append(
                    CodeChunk(
                        chunk_id=(
                            f"{file_path}::"
                            f"{symbol_name}"
                        ),
                        file_path=str(file_path),
                        language="python",
                        symbol_name=symbol_name,
                        symbol_type=symbol_type,
                        start_line=(
                            node.start_point[0] + 1
                        ),
                        end_line=(
                            node.end_point[0] + 1
                        ),
                        code=self.get_node_text(
                            source_bytes,
                            node
                        ),
                        imports=imports,
                    )
                )

            for child in node.children:

                walk(
                    child,
                    class_context
                )

        walk(root_node)

        # Collect top-level script/module chunks
        has_symbols = len(chunks) > 0
        top_level_chunks = self._extract_top_level_chunks(
            root_node=root_node,
            source_bytes=source_bytes,
            file_path=file_path,
            language="python",
            imports=imports,
            has_functions_or_classes=has_symbols,
        )
        chunks.extend(top_level_chunks)
        chunks.sort(key=lambda c: c.start_line)

        return chunks

    # =========================================================
    # JAVASCRIPT CHUNK EXTRACTION
    # =========================================================

    def extract_javascript_chunks(
        self,
        root_node,
        source_bytes,
        file_path
    ):

        chunks = []

        imports = self.extract_javascript_imports(
            root_node,
            source_bytes
        )

        function_types = {
            "function_declaration",
            "function",
            "method_definition",
            "arrow_function",
            "class_declaration",
        }

        def walk(node):

            if node.type in function_types:

                name = None

                for child in node.children:

                    if child.type == "identifier":

                        name = self.get_node_text(
                            source_bytes,
                            child
                        )

                        break

                name = name or "anonymous"

                if node.type == "class_declaration":

                    symbol_type = "class"

                elif node.type == "method_definition":

                    symbol_type = "method"

                else:

                    symbol_type = "function"

                chunks.append(
                    CodeChunk(
                        chunk_id=(
                            f"{file_path}::{name}"
                        ),
                        file_path=str(file_path),
                        language="javascript",
                        symbol_name=name,
                        symbol_type=symbol_type,
                        start_line=(
                            node.start_point[0] + 1
                        ),
                        end_line=(
                            node.end_point[0] + 1
                        ),
                        code=self.get_node_text(
                            source_bytes,
                            node
                        ),
                        imports=imports,
                    )
                )

            for child in node.children:
                walk(child)

        walk(root_node)

        # Collect top-level script/module chunks for JavaScript
        has_symbols = len(chunks) > 0
        top_level_chunks = self._extract_top_level_chunks(
            root_node=root_node,
            source_bytes=source_bytes,
            file_path=file_path,
            language="javascript",
            imports=imports,
            has_functions_or_classes=has_symbols,
        )
        chunks.extend(top_level_chunks)
        chunks.sort(key=lambda c: c.start_line)

        return chunks

    # =========================================================
    # SCRIPT / MODULE TOP-LEVEL CHUNKER
    # =========================================================

    @staticmethod
    def _extract_section_title(text: str) -> Optional[str]:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(("#", "//", "/*")) and len(line) > 2:
                clean = re.sub(r"^[#\s=/*\-]+", "", line).strip()
                clean = re.sub(r"[=/*\-]+$", "", clean).strip()
                if clean and len(clean) >= 3 and not clean.startswith("!"):
                    slug = re.sub(r"[^\w\s-]", "", clean).strip().lower()
                    slug = re.sub(r"[-\s]+", "_", slug)
                    if slug and len(slug) >= 3:
                        return slug[:40]
        return None

    def _extract_top_level_chunks(
        self,
        root_node,
        source_bytes: bytes,
        file_path: str,
        language: str,
        imports: List[str],
        has_functions_or_classes: bool = False,
        max_chunk_lines: int = 75,
    ) -> List[CodeChunk]:
        chunks = []
        file_stem = Path(file_path).stem
        all_lines = source_bytes.decode("utf-8", errors="ignore").splitlines()
        if not all_lines:
            return chunks

        script_statements = []
        for child in root_node.children:
            script_statements.append(child)

        current_stmts = []
        chunk_idx = 1

        def emit_block(stmts, idx):
            if not stmts:
                return None
            start_l = stmts[0].start_point[0] + 1
            end_l = stmts[-1].end_point[0] + 1
            code_slice = "\n".join(all_lines[start_l - 1:end_l])

            non_empty_lines = [
                l for l in code_slice.splitlines()
                if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))
            ]

            # If the file has functions/classes, ignore trivial top-level statements like pure imports or < 3 lines
            if has_functions_or_classes:
                if len(non_empty_lines) < 3:
                    return None
                if all(l.startswith(("import ", "from ", "const ", "require(")) for l in non_empty_lines):
                    return None

            if not non_empty_lines:
                return None

            title = self._extract_section_title(code_slice)
            sym_name = f"{file_stem}::{title}" if title else f"{file_stem}::section_{idx}"

            return CodeChunk(
                chunk_id=f"{file_path}::{sym_name}",
                file_path=str(file_path),
                language=language,
                symbol_name=sym_name,
                symbol_type="module",
                start_line=start_l,
                end_line=end_l,
                code=code_slice,
                imports=imports,
            )

        for stmt in script_statements:
            if stmt.type in (
                "function_definition", "class_definition",
                "function_declaration", "class_declaration"
            ):
                block_chunk = emit_block(current_stmts, chunk_idx)
                if block_chunk:
                    chunks.append(block_chunk)
                    chunk_idx += 1
                current_stmts = []
                continue

            start_l = stmt.start_point[0] + 1
            end_l = stmt.end_point[0] + 1

            if current_stmts:
                block_start = current_stmts[0].start_point[0] + 1
                if (end_l - block_start) > max_chunk_lines:
                    block_chunk = emit_block(current_stmts, chunk_idx)
                    if block_chunk:
                        chunks.append(block_chunk)
                        chunk_idx += 1
                    current_stmts = []

            current_stmts.append(stmt)

        if current_stmts:
            block_chunk = emit_block(current_stmts, chunk_idx)
            if block_chunk:
                chunks.append(block_chunk)

        return chunks

    # =========================================================
    # PARSE FILE
    # =========================================================

    def parse_file(
        self,
        file_path,
        base_path=None
    ):

        parser = self.get_parser(
            file_path
        )

        if parser is None:
            return []

        source = self.read_file(
            file_path
        )

        if not source:
            return []

        source_bytes = source.encode(
            "utf-8"
        )

        tree = parser.parse(
            source_bytes
        )

        file_path_obj = Path(file_path)
        if base_path:
            try:
                display_path = str(
                    file_path_obj.resolve().relative_to(
                        Path(base_path).resolve()
                    )
                ).replace("\\", "/")
            except Exception:
                display_path = str(file_path).replace("\\", "/")
        else:
            display_path = str(file_path).replace("\\", "/")

        extension = file_path_obj.suffix.lower()

        if extension == ".py":
            chunks = self.extract_python_chunks(
                tree.root_node,
                source_bytes,
                display_path
            )
        else:
            chunks = self.extract_javascript_chunks(
                tree.root_node,
                source_bytes,
                display_path
            )

        # Guarantee unique chunk_ids across the file
        seen_ids = set()
        for chunk in chunks:
            if chunk.chunk_id in seen_ids:
                chunk.chunk_id = f"{chunk.chunk_id}::L{chunk.start_line}"
            seen_ids.add(chunk.chunk_id)

        return chunks


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python -m codelens.core.parser "
            "<file_path>"
        )

        sys.exit(1)

    file_path = sys.argv[1]

    parser = CodeParser()

    chunks = parser.parse_file(
        file_path
    )

    print("=" * 60)
    print("CODELENS IMPROVED PARSER")
    print("=" * 60)

    print(
        f"\nFile: {file_path}"
    )

    print(
        f"Chunks found: {len(chunks)}"
    )

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        print(f"\n[{index}]")

        print(
            f"ID: {chunk.chunk_id}"
        )

        print(
            f"Symbol: {chunk.symbol_name}"
        )

        print(
            f"Type: {chunk.symbol_type}"
        )

        print(
            f"Lines: "
            f"{chunk.start_line}-"
            f"{chunk.end_line}"
        )

        print(
            f"Language: {chunk.language}"
        )

        print(
            f"Imports: "
            f"{chunk.imports}"
        )

        print("\nCode:")

        print(chunk.code)

        print("\nCitation:")

        print(chunk.citation())

    print(
        "\nParsing complete."
    )