import json
import sys
from pathlib import Path

from codelens.core.scanner import RepositoryScanner
from codelens.core.parser import CodeParser
from codelens.core.vector_store import VectorStore
from codelens.core.bm25_index import BM25Index
from codelens.core.graph import DependencyGraph
from codelens.core.hybrid_retriever import HybridRetriever
from codelens.baseline.naive_rag import NaiveRAG


# ============================================================
# LOAD BENCHMARK
# ============================================================

def load_benchmark():

    benchmark_path = Path(
        __file__
    ).parent / "benchmark_data.json"

    with open(
        benchmark_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# NORMALIZE SYMBOL
# ============================================================

def get_symbol(result):

    metadata = result.get(
        "metadata",
        {}
    )

    return metadata.get(
        "symbol_name",
        ""
    )


# ============================================================
# RETRIEVAL METRICS
# ============================================================

def calculate_metrics(
    retrieved_symbols,
    expected_symbols
):

    expected = set(
        expected_symbols
    )

    retrieved = [
        symbol
        for symbol in retrieved_symbols
        if symbol
    ]

    retrieved_set = set(
        retrieved
    )

    # --------------------------------------------------------
    # Hit@K
    # --------------------------------------------------------

    hit_at_1 = int(
        len(set(retrieved[:1]) & expected)
        > 0
    )

    hit_at_3 = int(
        len(set(retrieved[:3]) & expected)
        > 0
    )

    hit_at_5 = int(
        len(set(retrieved[:5]) & expected)
        > 0
    )

    # --------------------------------------------------------
    # MRR
    # --------------------------------------------------------

    reciprocal_rank = 0.0

    for rank, symbol in enumerate(
        retrieved,
        start=1
    ):

        if symbol in expected:

            reciprocal_rank = 1.0 / rank
            break

    # --------------------------------------------------------
    # Evidence coverage
    # --------------------------------------------------------

    matched = (
        retrieved_set & expected
    )

    coverage = (
        len(matched)
        / len(expected)
        if expected
        else 0.0
    )

    return {
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_5": hit_at_5,
        "mrr": reciprocal_rank,
        "coverage": coverage,
        "matched_symbols": sorted(
            matched
        ),
    }


# ============================================================
# BUILD CODELENS RETRIEVER
# ============================================================

def build_codelens(
    repository_path
):

    scanner = RepositoryScanner(
        repository_path
    )

    files = scanner.scan()

    parser = CodeParser()

    chunks = []

    for file_path in files:

        chunks.extend(
            parser.parse_file(
                file_path,
                base_path=repository_path
            )
        )

    vector_store = VectorStore()

    vector_store.clear()

    vector_store.add_chunks(
        chunks
    )

    bm25_index = BM25Index()

    bm25_index.build(
        chunks
    )

    graph = DependencyGraph(
        repository_path
    )

    graph.build(
        chunks
    )

    retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_index=bm25_index,
        dependency_graph=graph,
    )

    return retriever


# ============================================================
# BUILD NAIVE RAG RETRIEVER
# ============================================================

def build_naive(
    repository_path
):

    rag = NaiveRAG()

    rag.build_index(
        repository_path
    )

    return rag


# ============================================================
# EVALUATE ONE SYSTEM
# ============================================================

def evaluate_system(
    system,
    questions,
    system_name,
    top_k=5
):

    print(
        "\n" + "=" * 60
    )

    print(
        f"{system_name} EVALUATION"
    )

    print(
        "=" * 60
    )

    results = []

    for item in questions:

        question = item[
            "question"
        ]

        expected = item[
            "expected_symbols"
        ]

        # ----------------------------------------------------
        # Retrieve
        # ----------------------------------------------------

        if system_name == "NAIVE RAG":

            retrieved = system.retrieve(
                question,
                top_k=top_k
            )

        elif system_name == "CODELENS SEEDS":

            stages = system.search_stages(
                query=question,
                top_k=top_k,
                retrieval_k=25
            )

            retrieved = stages["seeds"]

        else:

            stages = system.search_stages(
                query=question,
                top_k=top_k,
                retrieval_k=25
            )

            retrieved = stages["final_results"]

        # ----------------------------------------------------
        # Symbols
        # ----------------------------------------------------

        symbols = [
            get_symbol(result)
            for result in retrieved
        ]

        metrics = calculate_metrics(
            symbols,
            expected
        )

        results.append(
            metrics
        )

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------

        print(
            f"\n[{item['id']}] "
            f"{question}"
        )

        print(
            f"Expected: "
            f"{', '.join(expected)}"
        )

        print(
            f"Retrieved: "
            f"{', '.join(symbols)}"
        )

        print(
            f"Hit@1: {metrics['hit_at_1']} | "
            f"Hit@3: {metrics['hit_at_3']} | "
            f"Hit@5: {metrics['hit_at_5']} | "
            f"MRR: {metrics['mrr']:.3f} | "
            f"Coverage: {metrics['coverage']:.3f}"
        )

    return results


# ============================================================
# AGGREGATE RESULTS
# ============================================================

def aggregate_results(
    results
):

    count = len(
        results
    )

    if count == 0:

        return {}

    return {
        "hit_at_1": sum(
            r["hit_at_1"]
            for r in results
        ) / count,

        "hit_at_3": sum(
            r["hit_at_3"]
            for r in results
        ) / count,

        "hit_at_5": sum(
            r["hit_at_5"]
            for r in results
        ) / count,

        "mrr": sum(
            r["mrr"]
            for r in results
        ) / count,

        "coverage": sum(
            r["coverage"]
            for r in results
        ) / count,
    }


# ============================================================
# MAIN EVALUATION
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CODELENS RETRIEVAL EVALUATION")
    print("=" * 60)

    if len(sys.argv) != 2:

        print(
            "\nUsage:"
        )

        print(
            "python -m codelens.evaluation.evaluate "
            "<repository_path>"
        )

        sys.exit(1)

    repository_path = sys.argv[1]

    benchmark = load_benchmark()

    questions = benchmark[
        "questions"
    ]

    print(
        f"\nBenchmark questions: "
        f"{len(questions)}"
    )

    # --------------------------------------------------------
    # Build systems
    # --------------------------------------------------------

    print(
        "\nBuilding Naive RAG..."
    )

    naive = build_naive(
        repository_path
    )

    print(
        "\nBuilding CodeLens..."
    )

    codelens = build_codelens(
        repository_path
    )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    naive_results = evaluate_system(
        naive,
        questions,
        "NAIVE RAG"
    )

    seeds_results = evaluate_system(
        codelens,
        questions,
        "CODELENS SEEDS"
    )

    expanded_results = evaluate_system(
        codelens,
        questions,
        "CODELENS EXPANDED"
    )

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    naive_summary = aggregate_results(
        naive_results
    )

    seeds_summary = aggregate_results(
        seeds_results
    )

    expanded_summary = aggregate_results(
        expanded_results
    )

    # --------------------------------------------------------
    # Final comparison
    # --------------------------------------------------------

    print(
        "\n" + "=" * 65
    )

    print(
        "FINAL COMPARISON"
    )

    print(
        "=" * 65
    )

    print(
        f"\n{'Metric':<15}"
        f"{'Naive RAG':<18}"
        f"{'CodeLens Seeds':<18}"
        f"{'CodeLens Expanded':<18}"
    )

    print(
        "-" * 65
    )

    for metric, label in [
        ("hit_at_1", "Hit@1"),
        ("hit_at_3", "Hit@3"),
        ("hit_at_5", "Hit@5"),
        ("mrr", "MRR"),
        ("coverage", "Coverage"),
    ]:

        print(
            f"{label:<15}"
            f"{naive_summary[metric]:<18.3f}"
            f"{seeds_summary[metric]:<18.3f}"
            f"{expanded_summary[metric]:<18.3f}"
        )

    print(
        "\n" + "=" * 65
    )

    print(
        "EVALUATION COMPLETE"
    )

    print(
        "=" * 65
    )
