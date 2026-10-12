import json
import re
import sys
import time
from pathlib import Path

from codelens.core.llm import GeminiLLM, build_pipeline
from codelens.core.scanner import RepositoryScanner
from codelens.core.parser import CodeParser
from codelens.baseline.naive_rag import NaiveRAG
from codelens.core.context_builder import ContextBuilder


CACHE_FILE = Path(__file__).parent / "answer_cache.json"


# ============================================================
# CACHE UTILITIES
# ============================================================

def load_cache():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")


def get_cached_or_query_llm(llm, question, context, system_name, question_id, cache):
    cache_key = f"{system_name}_{question_id}"
    if cache_key in cache:
        print("    (Using cached Gemini response)")
        return cache[cache_key]

    print("    Asking Gemini...")
    max_retries = 5
    retry_delay = 4

    for attempt in range(max_retries):
        try:
            response = llm.answer(
                question=question,
                context=context
            )
            answer = response["answer"]
            cache[cache_key] = answer
            save_cache(cache)
            time.sleep(2)  # avoid burst rate limits
            return answer
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota" in err_str:
                wait_time = retry_delay * (attempt + 1)
                print(f"    [Rate limited 429] Waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e

    raise RuntimeError(f"Failed to get response for question {question_id} after {max_retries} retries.")


# ============================================================
# LOAD BENCHMARK
# ============================================================

def load_benchmark():
    benchmark_path = (
        Path(__file__).parent / "benchmark_data.json"
    )

    with open(
        benchmark_path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# ============================================================
# EXTRACT SYMBOL
# ============================================================

def get_symbol(result):
    metadata = result.get("metadata", {})
    return metadata.get("symbol_name", "")


# ============================================================
# EXTRACT CITATIONS
# ============================================================

def extract_citations(answer):
    """
    Extract citations such as:

    [auth.py:5-12]
    [auth.py:6]
    [C:\\path\\database.py:15-23]
    """

    pattern = r"\[([A-Za-z0-9_./\\:-]+?):(\d+)(?:-(\d+))?\]"

    raw_matches = re.findall(
        pattern,
        answer
    )

    citations = []
    for raw_path, start, end in raw_matches:
        end = end if end else start
        filename = normalize_filename(raw_path)
        citations.append((filename, start, end))

    return citations


# ============================================================
# NORMALIZE FILENAME
# ============================================================

def normalize_filename(filename):
    filename = filename.replace("\\", "/")
    return Path(filename).name.lower()


# ============================================================
# ANSWER METRICS
# ============================================================

def evaluate_answer(
    answer,
    expected_symbols,
    retrieved_results
):
    retrieved_symbols = [
        get_symbol(result)
        for result in retrieved_results
    ]

    answer_lower = answer.lower()

    # --------------------------------------------------------
    # Expected symbols mentioned in answer
    # --------------------------------------------------------

    mentioned_symbols = []

    for symbol in expected_symbols:
        if symbol.lower() in answer_lower:
            mentioned_symbols.append(symbol)

    symbol_coverage = (
        len(mentioned_symbols)
        / len(expected_symbols)
        if expected_symbols
        else 0.0
    )

    # --------------------------------------------------------
    # Citations
    # --------------------------------------------------------

    citations = extract_citations(answer)

    citation_count = len(citations)

    # --------------------------------------------------------
    # Valid citations
    # --------------------------------------------------------

    valid_citations = 0

    available_files = set()

    for result in retrieved_results:
        metadata = result.get("metadata", {})

        file_path = (
            metadata.get("file_path")
            or result.get("file_path")
            or ""
        )

        if file_path:
            available_files.add(
                normalize_filename(file_path)
            )

    for filename, start, end in citations:
        if normalize_filename(filename) in available_files:
            valid_citations += 1

    citation_accuracy = (
        valid_citations / citation_count
        if citation_count
        else 0.0
    )

    # --------------------------------------------------------
    # Citation presence
    # --------------------------------------------------------

    citation_presence = int(
        citation_count > 0
    )

    # --------------------------------------------------------
    # Expected symbols retrieved
    # --------------------------------------------------------

    retrieved_expected = (
        set(retrieved_symbols)
        & set(expected_symbols)
    )

    retrieval_coverage = (
        len(retrieved_expected)
        / len(expected_symbols)
        if expected_symbols
        else 0.0
    )

    # --------------------------------------------------------
    # Basic answer quality checks
    # --------------------------------------------------------

    has_answer = int(
        len(answer.strip()) > 20
    )

    insufficient_evidence = (
        "insufficient to answer"
        in answer_lower
    )

    # A valid answer should normally not claim insufficiency
    # when the benchmark expects repository symbols.
    grounded_response = int(
        has_answer
        and not insufficient_evidence
    )

    return {
        "symbol_coverage": symbol_coverage,
        "citation_count": citation_count,
        "valid_citations": valid_citations,
        "citation_accuracy": citation_accuracy,
        "citation_presence": citation_presence,
        "retrieval_coverage": retrieval_coverage,
        "grounded_response": grounded_response,
        "mentioned_symbols": mentioned_symbols,
        "retrieved_symbols": retrieved_symbols,
    }


# ============================================================
# BUILD NAIVE RAG
# ============================================================

def build_naive(repository_path):
    print("\nBuilding Naive RAG...")

    rag = NaiveRAG()

    rag.build_index(
        repository_path
    )

    return rag


# ============================================================
# BUILD CODELENS
# ============================================================

def build_codelens(repository_path):
    print("\nBuilding CodeLens...")

    retriever, context_builder = build_pipeline(
        repository_path
    )

    return retriever, context_builder


# ============================================================
# BUILD NAIVE CONTEXT
# ============================================================

def build_naive_context(results):
    """
    Convert Naive RAG results into the same
    evidence format used by CodeLens.
    """

    context_builder = ContextBuilder(
        max_chars=16000
    )

    return context_builder.build(
        results
    )


# ============================================================
# EVALUATE SYSTEM
# ============================================================

def evaluate_system(
    system_name,
    questions,
    llm,
    retriever,
    context_builder=None,
    cache=None
):
    if cache is None:
        cache = {}

    print("\n" + "=" * 60)
    print(f"{system_name} ANSWER EVALUATION")
    print("=" * 60)

    all_results = []

    for item in questions:

        question = item["question"]

        expected_symbols = (
            item["expected_symbols"]
        )

        print(
            f"\n[{item['id']}] {question}"
        )

        # ----------------------------------------------------
        # Retrieval
        # ----------------------------------------------------

        if system_name == "NAIVE RAG":

            retrieved = retriever.retrieve(
                question,
                top_k=5
            )

            context = build_naive_context(
                retrieved
            )

        else:

            retrieved = retriever.search(
                query=question,
                top_k=5,
                retrieval_k=25
            )

            context = context_builder.build(
                retrieved
            )

        # ----------------------------------------------------
        # Gemini (Cached or Query)
        # ----------------------------------------------------

        answer = get_cached_or_query_llm(
            llm=llm,
            question=question,
            context=context,
            system_name=system_name,
            question_id=item["id"],
            cache=cache
        )

        # ----------------------------------------------------
        # Evaluate
        # ----------------------------------------------------

        metrics = evaluate_answer(
            answer=answer,
            expected_symbols=expected_symbols,
            retrieved_results=retrieved
        )

        metrics["question_id"] = item["id"]
        metrics["question"] = question

        all_results.append(
            metrics
        )

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------

        print(
            f"    Symbol coverage: "
            f"{metrics['symbol_coverage']:.3f}"
        )

        print(
            f"    Citations: "
            f"{metrics['citation_count']}"
        )

        print(
            f"    Valid citations: "
            f"{metrics['valid_citations']}"
        )

        print(
            f"    Citation accuracy: "
            f"{metrics['citation_accuracy']:.3f}"
        )

        print(
            "\n    ANSWER:"
        )

        print(
            answer
        )

    return all_results


# ============================================================
# AGGREGATE
# ============================================================

def aggregate(results):

    if not results:
        return {}

    count = len(results)

    return {
        "symbol_coverage": sum(
            r["symbol_coverage"]
            for r in results
        ) / count,

        "citation_accuracy": sum(
            r["citation_accuracy"]
            for r in results
        ) / count,

        "citation_presence": sum(
            r["citation_presence"]
            for r in results
        ) / count,

        "grounded_response": sum(
            r["grounded_response"]
            for r in results
        ) / count,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CODELENS ANSWER EVALUATION")
    print("=" * 60)

    if len(sys.argv) != 2:

        print(
            "\nUsage:"
        )

        print(
            "python -m codelens.evaluation.evaluate_answers "
            "<repository_path>"
        )

        raise SystemExit(1)

    repository_path = sys.argv[1]

    benchmark = load_benchmark()

    questions = benchmark["questions"]

    print(
        f"\nBenchmark questions: "
        f"{len(questions)}"
    )

    # --------------------------------------------------------
    # Gemini
    # --------------------------------------------------------

    print(
        "\nConnecting to Gemini..."
    )

    llm = GeminiLLM()

    print(
        f"Model: {llm.model}"
    )

    cache = load_cache()
    if cache:
        print(f"Loaded {len(cache)} cached answers.")

    # --------------------------------------------------------
    # Build systems
    # --------------------------------------------------------

    naive = build_naive(
        repository_path
    )

    codelens, context_builder = build_codelens(
        repository_path
    )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    naive_results = evaluate_system(
        "NAIVE RAG",
        questions,
        llm,
        naive,
        cache=cache
    )

    codelens_results = evaluate_system(
        "CODELENS",
        questions,
        llm,
        codelens,
        context_builder,
        cache=cache
    )

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    naive_summary = aggregate(
        naive_results
    )

    codelens_summary = aggregate(
        codelens_results
    )

    # --------------------------------------------------------
    # Final comparison
    # --------------------------------------------------------

    print(
        "\n" + "=" * 60
    )

    print(
        "FINAL ANSWER COMPARISON"
    )

    print(
        "=" * 60
    )

    print(
        f"\n{'Metric':<25}"
        f"{'Naive RAG':<18}"
        f"{'CodeLens':<18}"
    )

    print(
        "-" * 61
    )

    metrics = [
        ("symbol_coverage", "Symbol Coverage"),
        ("citation_accuracy", "Citation Accuracy"),
        ("citation_presence", "Citation Presence"),
        ("grounded_response", "Grounded Responses"),
    ]

    for key, label in metrics:

        print(
            f"{label:<25}"
            f"{naive_summary[key]:<18.3f}"
            f"{codelens_summary[key]:<18.3f}"
        )

    print(
        "\n" + "=" * 60
    )

    print(
        "ANSWER EVALUATION COMPLETE"
    )

    print(
        "=" * 60
    )
