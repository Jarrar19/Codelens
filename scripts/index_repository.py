from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from codelens.core.scanner import RepositoryScanner
from codelens.core.parser import CodeParser


def index_repository(repository_path):
    """
    Scan a repository and convert supported source files
    into standardized CodeChunk objects.
    """

    print("=" * 60)
    print("CODELENS REPOSITORY INDEXER")
    print("=" * 60)

    print(f"\nRepository: {repository_path}")

    # ---------------------------------------------------------
    # 1. Scanner
    # ---------------------------------------------------------

    scanner = RepositoryScanner(repository_path)

    print("\n[1/2] Scanning repository...")

    files = scanner.scan()

    print(f"Files found: {len(files)}")

    stats = scanner.get_statistics(files)

    print("\nFile statistics:")
    print("-" * 40)

    for key, value in stats.items():
        print(f"{key}: {value}")

    # ---------------------------------------------------------
    # 2. Parser
    # ---------------------------------------------------------

    parser = CodeParser()

    print("\n[2/2] Parsing source files...")

    all_chunks = []

    parsed_files = 0
    failed_files = 0

    for file_path in files:

        try:

            chunks = parser.parse_file(file_path)

            if chunks:
                parsed_files += 1
                all_chunks.extend(chunks)

                print(
                    f"[OK] {scanner.get_relative_path(file_path)} "
                    f"-> {len(chunks)} chunks"
                )

            else:

                print(
                    f"[EMPTY] {scanner.get_relative_path(file_path)} "
                    f"-> 0 chunks"
                )

        except Exception as e:

            failed_files += 1

            print(
                f"[ERROR] {scanner.get_relative_path(file_path)} "
                f"-> ERROR: {e}"
            )

    # ---------------------------------------------------------
    # Results
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("INDEXING RESULTS")
    print("=" * 60)

    print(f"\nFiles scanned: {len(files)}")
    print(f"Files parsed: {parsed_files}")
    print(f"Files failed: {failed_files}")
    print(f"Total chunks: {len(all_chunks)}")

    print("\n" + "-" * 60)
    print("EXTRACTED CODE CHUNKS")
    print("-" * 60)

    for index, chunk in enumerate(all_chunks, start=1):

        relative_file = scanner.get_relative_path(
            chunk.file_path
        )

        print(f"\n[{index}]")
        print(f"File: {relative_file}")
        print(f"Symbol: {chunk.symbol_name}")
        print(f"Type: {chunk.symbol_type}")
        print(
            f"Lines: "
            f"{chunk.start_line}-{chunk.end_line}"
        )
        print(f"Language: {chunk.language}")

    print("\n" + "=" * 60)
    print("REPOSITORY INDEXING COMPLETE")
    print("=" * 60)

    return all_chunks


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "\nUsage:"
        )

        print(
            "python scripts/index_repository.py "
            "<repository_path>"
        )

        sys.exit(1)

    repository_path = sys.argv[1]

    index_repository(repository_path)