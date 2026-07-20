import argparse
import uvicorn
from backend.api import app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the SHL assessment FastAPI app.")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload")
    args = parser.parse_args()

    uvicorn.run(
        "backend.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
