import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

from codelens.core.scanner import RepositoryScanner
from codelens.core.parser import CodeParser
from codelens.core.vector_store import VectorStore


load_dotenv()


class NaiveRAG:
    """
    Baseline RAG system for CodeLens.

    IMPORTANT:
    This intentionally uses ONLY dense vector retrieval.

    It does NOT use:
        - BM25
        - RRF
        - Dependency graph
        - Graph expansion

    This gives us a clean baseline for research evaluation.
    """

    def __init__(self):

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite"
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found."
            )

        self.client = genai.Client(
            api_key=api_key
        )

    # =========================================================
    # BUILD VECTOR INDEX
    # =========================================================

    def build_index(self, repository_path):

        print("\n[1] Scanning repository...")

        scanner = RepositoryScanner(
            repository_path
        )

        files = scanner.scan()

        print(
            f"    Files found: {len(files)}"
        )

        # -----------------------------------------------------

        print(
            "\n[2] Parsing source files..."
        )

        parser = CodeParser()

        chunks = []

        for file_path in files:

            chunks.extend(
                parser.parse_file(
                    file_path,
                    base_path=repository_path
                )
            )

        print(
            f"    Code chunks: {len(chunks)}"
        )

        # -----------------------------------------------------

        print(
            "\n[3] Building dense vector index..."
        )

        self.vector_store = VectorStore()

        self.vector_store.clear()

        self.vector_store.add_chunks(
            chunks
        )

        print(
            "    Vector index ready."
        )

    # =========================================================
    # RETRIEVE
    # =========================================================

    def retrieve(
        self,
        query,
        top_k=5
    ):

        results = self.vector_store.search(
            query,
            top_k=top_k
        )

        return results

    # =========================================================
    # GENERATE ANSWER
    # =========================================================

    def answer(
        self,
        question,
        results
    ):

        context_parts = []

        for index, result in enumerate(
            results,
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

            start_line = metadata.get(
                "start_line",
                "?"
            )

            end_line = metadata.get(
                "end_line",
                "?"
            )

            symbol_name = metadata.get(
                "symbol_name",
                "unknown"
            )

            document = result.get(
                "document",
                ""
            )

            context_parts.append(
                f"""
[EVIDENCE {index}]
FILE: {file_path}
LINES: {start_line}-{end_line}
SYMBOL: {symbol_name}

{document}
"""
            )

        context = "\n".join(
            context_parts
        )

        prompt = f"""
You are a codebase explanation assistant.

Answer the user's question using ONLY the
repository evidence supplied below.

Do not invent files, functions, behavior,
or relationships.

If the evidence is insufficient, say so.

USER QUESTION:
{question}

REPOSITORY EVIDENCE:
{context}

Give a concise step-by-step explanation.

For important claims, cite the evidence using:

[filename:line-start-line-end]
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2000,
            ),
        )

        return response.text

    # =========================================================
    # COMPLETE QUERY
    # =========================================================

    def query(
        self,
        question,
        top_k=5
    ):

        results = self.retrieve(
            question,
            top_k
        )

        answer = self.answer(
            question,
            results
        )

        return results, answer


# =============================================================
# COMMAND LINE TEST
# =============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CODELENS NAIVE RAG BASELINE")
    print("=" * 60)

    if len(sys.argv) != 2:

        print(
            "\nUsage:"
        )

        print(
            "python -m codelens.baseline.naive_rag "
            "<repository_path>"
        )

        sys.exit(1)

    repository_path = sys.argv[1]

    try:

        # -----------------------------------------------------
        # Create baseline
        # -----------------------------------------------------

        rag = NaiveRAG()

        # -----------------------------------------------------
        # Build index
        # -----------------------------------------------------

        rag.build_index(
            repository_path
        )

        # -----------------------------------------------------
        # Test query
        # -----------------------------------------------------

        question = (
            "How does user login work?"
        )

        print(
            "\n[4] Query:"
        )

        print(
            f"    {question}"
        )

        # -----------------------------------------------------
        # Retrieve
        # -----------------------------------------------------

        print(
            "\n[5] Dense vector retrieval..."
        )

        results, answer = rag.query(
            question,
            top_k=5
        )

        print(
            f"    Retrieved chunks: "
            f"{len(results)}"
        )

        # -----------------------------------------------------
        # Show retrieval results
        # -----------------------------------------------------

        print(
            "\n" + "=" * 60
        )

        print(
            "NAIVE RAG RETRIEVED RESULTS"
        )

        print(
            "=" * 60
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            metadata = result.get(
                "metadata",
                {}
            )

            print(
                f"\n[{index}] "
                f"{metadata.get('file_path')}"
            )

            print(
                f"Symbol: "
                f"{metadata.get('symbol_name')}"
            )

            print(
                f"Lines: "
                f"{metadata.get('start_line')}-"
                f"{metadata.get('end_line')}"
            )

            if "distance" in result:

                print(
                    f"Distance: "
                    f"{result['distance']}"
                )

        # -----------------------------------------------------
        # Show answer
        # -----------------------------------------------------

        print(
            "\n" + "=" * 60
        )

        print(
            "NAIVE RAG ANSWER"
        )

        print(
            "=" * 60
        )

        print(
            answer
        )

        print(
            "\n" + "=" * 60
        )

        print(
            "NAIVE RAG TEST COMPLETE"
        )

        print(
            "=" * 60
        )

    except Exception as error:

        print(
            "\nNaive RAG failed:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )