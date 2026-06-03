"""
Start the MarkItDown Prompt Studio server.
Run: python run_server.py
"""

import uvicorn

if __name__ == "__main__":
    print("\n  MarkItDown Prompt Studio")
    print("  http://localhost:8000\n")
    uvicorn.run(
        "backend.server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
