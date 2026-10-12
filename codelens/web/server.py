"""
CodeLens Web Server Launcher.

Usage:
    python -m codelens.web.server
    python -m codelens.web.server --port 8000 --host 127.0.0.1
"""

import argparse
import sys
from pathlib import Path
import uvicorn

from codelens.web.state import state


def main():
    parser = argparse.ArgumentParser(description="CodeLens Grounded Codebase Assistant Web Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    print("=" * 65)
    print("  CODELENS: GROUNDED CODEBASE EXPLANATION ENGINE")
    print(f"  Server URL: http://{args.host}:{args.port}")
    print("=" * 65 + "\n")

    uvicorn.run(
        "codelens.web.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
