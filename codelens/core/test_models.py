import unittest

try:
    from codelens.core.models import CodeChunk
except ImportError:
    from models import CodeChunk


class TestCodeChunk(unittest.TestCase):
    def test_chunk_creation_and_citation(self):
        chunk = CodeChunk(
            chunk_id="auth.py::login",
            file_path="auth.py",
            language="python",
            symbol_name="login",
            symbol_type="function",
            start_line=4,
            end_line=6,
            code="def login(username):\n    token = generate_token(username)\n    return token",
            imports=["os", "jwt"]
        )
        self.assertEqual(chunk.chunk_id, "auth.py::login")
        self.assertIn("lines 4-6", chunk.citation())
        self.assertIn("Imports: os, jwt", chunk.searchable_text())
        self.assertEqual(chunk.to_dict()["symbol_name"], "login")

    def test_chunk_default_imports(self):
        chunk = CodeChunk(
            chunk_id="utils.py::helper",
            file_path="utils.py",
            language="python",
            symbol_name="helper",
            symbol_type="function",
            start_line=1,
            end_line=2,
            code="def helper(): pass"
        )
        self.assertEqual(chunk.imports, [])
        self.assertIn("lines 1-2", chunk.citation())


if __name__ == "__main__":
    unittest.main()