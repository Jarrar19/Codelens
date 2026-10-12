from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List


@dataclass
class CodeChunk:
    """
    Standard representation of a searchable piece of source code.
    """

    chunk_id: str
    file_path: str
    language: str
    symbol_name: str
    symbol_type: str
    start_line: int
    end_line: int
    code: str

    # Imports used by this file/chunk (defaults to empty list)
    imports: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the chunk into a dictionary."""
        return asdict(self)

    def searchable_text(self) -> str:
        """
        Text used later by semantic search and BM25.
        """

        imports_text = ", ".join(self.imports)

        return (
            f"File: {self.file_path}\n"
            f"Language: {self.language}\n"
            f"Symbol: {self.symbol_name}\n"
            f"Type: {self.symbol_type}\n"
            f"Lines: {self.start_line}-{self.end_line}\n"
            f"Imports: {imports_text}\n\n"
            f"{self.code}"
        )

    def citation(self) -> str:
        """Return a human-readable source reference."""

        return (
            f"{self.file_path} "
            f"(lines {self.start_line}-{self.end_line})"
        )