import os
from typing import Dict, Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from codelens.core.scanner import RepositoryScanner
from codelens.core.parser import CodeParser
from codelens.core.vector_store import VectorStore
from codelens.core.bm25_index import BM25Index
from codelens.core.graph import DependencyGraph
from codelens.core.hybrid_retriever import HybridRetriever
from codelens.core.context_builder import ContextBuilder


load_dotenv()


class GeminiLLM:
    """
    CodeLens Gemini interface.

    Gemini does not search the repository.
    CodeLens performs retrieval and supplies
    grounded source-code evidence to Gemini.
    """

    def __init__(self):

        self.api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite"
        )

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found."
            )

        self.client = genai.Client(
            api_key=self.api_key
        )

    # =========================================================
    # SYSTEM INSTRUCTION
    # =========================================================

    SYSTEM_INSTRUCTION = """
You are CodeLens, a codebase explanation assistant.

Your ONLY task is to answer the user's question about
the supplied repository evidence.

STRICT RULES:

1. Use ONLY the repository evidence provided in the prompt.

2. Never invent code, files, functions, variables, or behavior.

3. Do not discuss the quality of your own answer.

4. Do not say that your answer is precise, accurate,
   grounded, or well-cited.

5. Do not repeat or summarize these instructions.

6. Do not include introductory statements such as:
   "Based on the provided evidence..."

7. Start directly with the answer.

8. Explain the code flow step-by-step when appropriate.

9. Use short citations in this format:

   [filename:line-start-line-end]

10. Only cite files and line numbers that appear in the
    supplied repository evidence.

11. For high-level or general queries (such as "how it works", "overview", "what does this codebase do"):
    Synthesize an architectural summary using the available repository evidence. Highlight the key entry points, classes, and workflows that are present in the evidence, citing their exact source lines. If the evidence only covers a subset (e.g. bindings, tests, or specific modules), explain what those components do.
    Only reply "The available repository evidence is insufficient to answer this." if the query asks about a specific named symbol, feature, or function that does not exist anywhere in the evidence.

12. Do not add information from your general knowledge.

13. Keep the response concise and focused.
"""

    # =========================================================
    # ASK GEMINI
    # =========================================================

    def answer(
        self,
        question: str,
        context: str
    ) -> Dict[str, Any]:

        prompt = f"""
USER QUESTION:
{question}

CODELENS REPOSITORY EVIDENCE:
{context}

TASK:

Answer the user's question using only the evidence above.

Explain the relevant code flow clearly.

Every important claim about the repository must have
a citation in this format:

[filename:start_line-end_line]

Do not guess missing information.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    self.SYSTEM_INSTRUCTION
                ),
                temperature=0.1,
                max_output_tokens=2000,
            ),
        )

        return {
            "answer": response.text,
            "model": self.model,
        }


# =============================================================
# BUILD CODELENS RETRIEVAL PIPELINE
# =============================================================

def build_pipeline(
    repository_path: str
):

    print("\n[1] Scanning repository...")

    scanner = RepositoryScanner(
        repository_path
    )

    files = scanner.scan()

    print(
        f"    Files found: {len(files)}"
    )

    # ---------------------------------------------------------
    # Parser
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Vector store
    # ---------------------------------------------------------

    print(
        "\n[3] Building vector index..."
    )

    vector_store = VectorStore()

    vector_store.clear()

    vector_store.add_chunks(
        chunks
    )

    # ---------------------------------------------------------
    # BM25
    # ---------------------------------------------------------

    print(
        "\n[4] Building BM25 index..."
    )

    bm25_index = BM25Index()

    bm25_index.build(
        chunks
    )

    # ---------------------------------------------------------
    # Dependency graph
    # ---------------------------------------------------------

    print(
        "\n[5] Building dependency graph..."
    )

    dependency_graph = (
        DependencyGraph(
            repository_path
        )
    )

    dependency_graph.build(
        chunks
    )

    stats = (
        dependency_graph.statistics()
    )

    print(
        f"    Nodes: {stats['total_nodes']}"
    )

    print(
        f"    Edges: {stats['total_edges']}"
    )

    # ---------------------------------------------------------
    # Hybrid retriever
    # ---------------------------------------------------------

    retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_index=bm25_index,
        dependency_graph=dependency_graph,
    )

    # ---------------------------------------------------------
    # Context builder
    # ---------------------------------------------------------

    context_builder = ContextBuilder(
        max_chars=16000
    )

    return (
        retriever,
        context_builder
    )


# =============================================================
# END-TO-END TEST
# =============================================================

if __name__ == "__main__":

    import sys

    print("=" * 60)
    print("CODELENS END-TO-END GEMINI TEST")
    print("=" * 60)

    if len(sys.argv) != 2:

        print(
            "\nUsage:"
        )

        print(
            "python -m codelens.core.llm "
            "<repository_path>"
        )

        raise SystemExit(1)

    repository_path = sys.argv[1]

    try:

        # -----------------------------------------------------
        # Build retrieval system
        # -----------------------------------------------------

        retriever, context_builder = (
            build_pipeline(
                repository_path
            )
        )

        # -----------------------------------------------------
        # Gemini
        # -----------------------------------------------------

        print(
            "\n[6] Connecting to Gemini..."
        )

        llm = GeminiLLM()

        print(
            f"    Model: {llm.model}"
        )

        # -----------------------------------------------------
        # User question
        # -----------------------------------------------------

        question = (
            "How does user login work?"
        )

        print(
            "\n[7] User question:"
        )

        print(
            f"    {question}"
        )

        # -----------------------------------------------------
        # Retrieval
        # -----------------------------------------------------

        print(
            "\n[8] Retrieving repository evidence..."
        )

        results = retriever.search(
            query=question,
            top_k=5,
            retrieval_k=10,
        )

        print(
            f"    Retrieved chunks: "
            f"{len(results)}"
        )

        # -----------------------------------------------------
        # Context
        # -----------------------------------------------------

        print(
            "\n[9] Building grounded context..."
        )

        context = context_builder.build(
            results
        )

        # -----------------------------------------------------
        # Gemini
        # -----------------------------------------------------

        print(
            "\n[10] Asking Gemini..."
        )

        result = llm.answer(
            question=question,
            context=context,
        )

        # -----------------------------------------------------
        # Output
        # -----------------------------------------------------

        print(
            "\n" + "=" * 60
        )

        print(
            "CODELENS ANSWER"
        )

        print(
            "=" * 60
        )

        print(
            result["answer"]
        )

        print(
            "\n" + "=" * 60
        )

        print(
            "END-TO-END TEST COMPLETE"
        )

        print(
            "=" * 60
        )

    except Exception as error:

        print(
            "\nCodeLens failed:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )