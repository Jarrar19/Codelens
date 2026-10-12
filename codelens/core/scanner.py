from pathlib import Path


class RepositoryScanner:
    """
    Scans a repository and returns source files that CodeLens
    should analyze.
    """

    DEFAULT_IGNORED_DIRECTORIES = {
        ".git",
        ".github",
        ".idea",
        ".vscode",
        "node_modules",
        "venv",
        ".venv",
        "env",
        "__pycache__",
        "dist",
        "build",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
        ".next",
        "target",
    }

    DEFAULT_SUPPORTED_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
    }

    def __init__(
        self,
        repository_path,
        ignored_directories=None,
        supported_extensions=None,
        max_file_size_mb=2,
    ):
        self.repository_path = Path(repository_path).resolve()

        self.ignored_directories = (
            ignored_directories
            if ignored_directories is not None
            else self.DEFAULT_IGNORED_DIRECTORIES
        )

        self.supported_extensions = (
            supported_extensions
            if supported_extensions is not None
            else self.DEFAULT_SUPPORTED_EXTENSIONS
        )

        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def validate_repository(self):
        """Check that the repository exists and is a directory."""

        if not self.repository_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {self.repository_path}"
            )

        if not self.repository_path.is_dir():
            raise NotADirectoryError(
                f"Path is not a directory: {self.repository_path}"
            )

    def should_ignore_directory(self, directory_name):
        """Check whether a directory should be ignored."""

        return directory_name in self.ignored_directories

    def is_supported_file(self, file_path):
        """Check whether a file has a supported source-code extension."""

        return file_path.suffix.lower() in self.supported_extensions

    def is_file_too_large(self, file_path):
        """Prevent extremely large files from entering the pipeline."""

        try:
            return file_path.stat().st_size > self.max_file_size_bytes
        except OSError:
            return True

    def scan(self):
        """
        Scan the repository.

        Returns:
            list[Path]: supported source files.
        """

        self.validate_repository()

        source_files = []

        for path in self.repository_path.rglob("*"):

            if not path.is_file():
                continue

            relative_parts = path.relative_to(
                self.repository_path
            ).parts

            # Ignore files inside ignored directories
            if any(
                part in self.ignored_directories
                for part in relative_parts[:-1]
            ):
                continue

            # Ignore unsupported files
            if not self.is_supported_file(path):
                continue

            # Ignore very large files
            if self.is_file_too_large(path):
                continue

            source_files.append(path)

        return sorted(source_files)

    def get_relative_path(self, file_path):
        """Return repository-relative path."""

        return str(
            Path(file_path).resolve().relative_to(
                self.repository_path
            )
        )

    def get_statistics(self, source_files):
        """Return basic repository scanning statistics."""

        statistics = {
            "total_files": len(source_files),
            "python_files": 0,
            "javascript_files": 0,
            "typescript_files": 0,
            "other_supported_files": 0,
        }

        for file_path in source_files:

            extension = file_path.suffix.lower()

            if extension == ".py":
                statistics["python_files"] += 1

            elif extension in {".js", ".jsx"}:
                statistics["javascript_files"] += 1

            elif extension in {".ts", ".tsx"}:
                statistics["typescript_files"] += 1

            else:
                statistics["other_supported_files"] += 1

        return statistics


if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:
        print("Usage:")
        print("python scanner.py <repository_path>")
        sys.exit(1)

    repository = sys.argv[1]

    scanner = RepositoryScanner(repository)

    files = scanner.scan()

    print("=" * 60)
    print("CODELENS REPOSITORY SCANNER")
    print("=" * 60)

    print(f"\nRepository: {scanner.repository_path}")
    print(f"Files found: {len(files)}")

    print("\nStatistics:")
    print("-" * 40)

    stats = scanner.get_statistics(files)

    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\nFiles:")
    print("-" * 40)

    for file_path in files:
        print(scanner.get_relative_path(file_path))

    print("\nScan complete.")