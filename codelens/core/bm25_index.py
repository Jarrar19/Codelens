import re
from typing import List, Dict, Any

from rank_bm25 import BM25Okapi

from codelens.core.models import CodeChunk


class CodeTokenizer:
    """
    Code-aware tokenizer.

    Examples:

        generate_token
        ->
        ["generate_token", "generate", "token"]

        verifyAuthUser
        ->
        ["verifyauthuser", "verify", "auth", "user"]
    """

    @staticmethod
    def tokenize(text: str) -> List[str]:

        if not text:
            return []

        raw_tokens = re.findall(
            r"[A-Za-z_][A-Za-z0-9_]*",
            text
        )

        tokens = []

        for token in raw_tokens:

            # -------------------------------------------------
            # Original identifier
            # -------------------------------------------------

            tokens.append(token.lower())

            # -------------------------------------------------
            # snake_case
            # -------------------------------------------------

            snake_parts = re.split(
                r"_+",
                token
            )

            for part in snake_parts:

                if part:
                    tokens.append(
                        part.lower()
                    )

            # -------------------------------------------------
            # camelCase / PascalCase
            # -------------------------------------------------

            camel_parts = re.findall(
                r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+",
                token
            )

            for part in camel_parts:

                if part.lower() != token.lower():

                    tokens.append(
                        part.lower()
                    )

        return list(
            dict.fromkeys(tokens)
        )


class BM25Index:
    """
    Code-aware BM25 search index.

    Important fields receive additional weight:

        Symbol name  -> strongest
        File name    -> strong
        Imports      -> medium
        Source code  -> normal

    This makes BM25 more useful for source-code retrieval
    than treating every word equally.
    """

    def __init__(self):

        self.chunks: List[CodeChunk] = []

        self.tokenized_documents = []

        self.bm25 = None

    # =========================================================
    # WEIGHTED DOCUMENT CREATION
    # =========================================================

    def create_weighted_document(
        self,
        chunk: CodeChunk
    ) -> str:
        """
        Create a BM25 document with field weighting.

        Repeating important fields gives identifiers and
        filenames greater retrieval importance.
        """

        file_name = (
            chunk.file_path
            .replace("\\", "/")
            .split("/")[-1]
        )

        symbol = chunk.symbol_name

        symbol_parts = CodeTokenizer.tokenize(
            symbol
        )

        imports = " ".join(
            chunk.imports
        )

        # Symbol is intentionally repeated.
        #
        # Example:
        #
        # generate_token
        # generate_token
        # generate_token
        # generate token
        #
        # This gives exact symbol matches more importance.

        weighted_text = " ".join([
            symbol,
            symbol,
            symbol,

            file_name,
            file_name,

            " ".join(symbol_parts),

            imports,

            chunk.code,
        ])

        return weighted_text

    # =========================================================
    # BUILD INDEX
    # =========================================================

    def build(
        self,
        chunks: List[CodeChunk]
    ):

        if not chunks:

            raise ValueError(
                "Cannot build BM25 index with no chunks."
            )

        self.chunks = chunks

        documents = [
            self.create_weighted_document(
                chunk
            )
            for chunk in chunks
        ]

        self.tokenized_documents = [
            CodeTokenizer.tokenize(
                document
            )
            for document in documents
        ]

        self.bm25 = BM25Okapi(
            self.tokenized_documents,
            k1=1.5,
            b=0.75,
            epsilon=0.25
        )

        print(
            f"BM25 index built with "
            f"{len(chunks)} chunks."
        )

    # =========================================================
    # SEARCH
    # =========================================================

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:

        if self.bm25 is None:

            raise RuntimeError(
                "BM25 index has not been built yet."
            )

        query_tokens = CodeTokenizer.tokenize(
            query
        )

        if not query_tokens:
            return []

        scores = self.bm25.get_scores(
            query_tokens
        )

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )

        results = []

        for rank, index in enumerate(
            ranked_indices[:top_k],
            start=1
        ):

            chunk = self.chunks[index]

            results.append({
                "rank": rank,
                "chunk_id": chunk.chunk_id,
                "score": float(scores[index]),
                "chunk": chunk,
                "file_path": chunk.file_path,
                "symbol_name": chunk.symbol_name,
                "symbol_type": chunk.symbol_type,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
            })

        return results

    # =========================================================
    # TOKENIZER TEST
    # =========================================================

    @staticmethod
    def test_tokenizer():

        examples = [
            "generate_token",
            "verifyAuthUser",
            "JWTAuthentication",
            "get_user_by_id",
        ]

        print("\nTokenizer examples:")
        print("-" * 40)

        for example in examples:

            tokens = CodeTokenizer.tokenize(
                example
            )

            print(
                f"{example:25} -> {tokens}"
            )


# =============================================================
# TEST PROGRAM
# =============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print("Usage:")
        print(
            "python -m codelens.core.bm25_index "
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
    print("CODELENS BM25 SEARCH TEST")
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

        file_chunks = parser.parse_file(
            file_path
        )

        chunks.extend(
            file_chunks
        )

    print(
        f"Code chunks found: {len(chunks)}"
    )

    # ---------------------------------------------------------
    # Build BM25
    # ---------------------------------------------------------

    index = BM25Index()

    index.build(
        chunks
    )

    # ---------------------------------------------------------
    # Tokenizer tests
    # ---------------------------------------------------------

    index.test_tokenizer()

    # ---------------------------------------------------------
    # Search tests
    # ---------------------------------------------------------

    queries = [
        "generate_token",
        "password authentication",
        "database user",
        "process payment",
        "send welcome email",
        "generate report",
        "validate email",
        "transaction",
    ]

    for query in queries:

        print("\n" + "=" * 60)
        print(
            f"QUERY: {query}"
        )
        print("=" * 60)

        results = index.search(
            query,
            top_k=3
        )

        for result in results:

            print(
                f"\n[{result['rank']}] "
                f"{result['file_path']}"
            )

            print(
                f"Symbol: "
                f"{result['symbol_name']}"
            )

            print(
                f"Type: "
                f"{result['symbol_type']}"
            )

            print(
                f"Lines: "
                f"{result['start_line']}-"
                f"{result['end_line']}"
            )

            print(
                f"BM25 Score: "
                f"{result['score']:.4f}"
            )

    print("\n" + "=" * 60)
    print("BM25 TEST COMPLETE")
    print("=" * 60)