from pathlib import Path
from typing import List, Dict, Any

import chromadb
from sentence_transformers import SentenceTransformer

from codelens.core.models import CodeChunk


class VectorStore:
    """
    Local semantic vector store for CodeLens.

    Uses:
    - Sentence Transformers for embeddings
    - ChromaDB for local vector storage
    """

    def __init__(
        self,
        persist_directory="chroma_db",
        collection_name="codelens_code",
        embedding_model="all-MiniLM-L6-v2",
    ):
        self.persist_directory = Path(persist_directory)

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer(
            embedding_model
        )

        print("Connecting to ChromaDB...")

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "CodeLens source code embeddings"
            }
        )

        print("Vector store ready.")

    def add_chunks(self, chunks: List[CodeChunk]):
        """
        Convert CodeChunks into embeddings and store them.
        """

        if not chunks:
            print("No chunks to add.")
            return

        documents = [
            chunk.searchable_text()
            for chunk in chunks
        ]

        ids = [
            chunk.chunk_id
            for chunk in chunks
        ]

        metadatas = [
    {
        "file_path": chunk.file_path,
        "language": chunk.language,
        "symbol_name": chunk.symbol_name,
        "symbol_type": chunk.symbol_type,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "imports": ", ".join(chunk.imports),
    }
    for chunk in chunks
]

        print(
            f"Creating embeddings for "
            f"{len(chunks)} chunks..."
        )

        embeddings = self.embedding_model.encode(
            documents,
            normalize_embeddings=True,
            show_progress_bar=True
        )

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings.tolist(),
            metadatas=metadatas
        )

        print(
            f"Stored {len(chunks)} chunks "
            f"in ChromaDB."
        )

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search.
        """

        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True
        )

        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k
        )

        formatted_results = []

        if not results["ids"]:
            return formatted_results

        ids = results["ids"][0]
        documents = results["documents"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        for i in range(len(ids)):

            formatted_results.append({
                "chunk_id": ids[i],
                "document": documents[i],
                "distance": distances[i],
                "metadata": metadatas[i],
            })

        return formatted_results

    def count(self):
        """Return number of indexed chunks."""

        return self.collection.count()

    def clear(self):
        """Delete all indexed chunks."""

        ids = self.collection.get()["ids"]

        if ids:
            self.collection.delete(
                ids=ids
            )

        print("Vector store cleared.")


if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python -m codelens.core.vector_store "
            "<repository_path>"
        )

        sys.exit(1)

    repository_path = sys.argv[1]

    # Import here to keep the module reusable.
    from codelens.core.scanner import RepositoryScanner
    from codelens.core.parser import CodeParser

    print("=" * 60)
    print("CODELENS VECTOR STORE TEST")
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

    chunks = []

    for file_path in files:

        file_chunks = parser.parse_file(
            file_path
        )

        chunks.extend(file_chunks)

    print(
        f"Code chunks found: {len(chunks)}"
    )

    # ---------------------------------------------------------
    # Create vector store
    # ---------------------------------------------------------

    store = VectorStore()

    # For a clean test, remove previous data.
    store.clear()

    store.add_chunks(chunks)

    print(
        f"\nIndexed chunks: {store.count()}"
    )

    # ---------------------------------------------------------
    # Test semantic search
    # ---------------------------------------------------------

    queries = [
        "Where is the authentication token generated?",
        "How does the user login?",
        "Where is the main function?"
    ]

    for query in queries:

        print("\n" + "=" * 60)
        print(f"QUERY: {query}")
        print("=" * 60)

        results = store.search(
            query,
            top_k=3
        )

        for rank, result in enumerate(
            results,
            start=1
        ):

            metadata = result["metadata"]

            print(
                f"\n[{rank}] "
                f"{metadata['file_path']}"
            )

            print(
                f"Symbol: "
                f"{metadata['symbol_name']}"
            )

            print(
                f"Lines: "
                f"{metadata['start_line']}-"
                f"{metadata['end_line']}"
            )

            print(
                f"Distance: "
                f"{result['distance']:.4f}"
            )

    print("\n" + "=" * 60)
    print("VECTOR SEARCH TEST COMPLETE")
    print("=" * 60)