"""EpiSwarm Studio Server Entrypoint."""

import sys
import uvicorn
from pathlib import Path

def main(host: str = "127.0.0.1", port: int = 8501, reload: bool = False):
    """Run the EpiSwarm Studio FastAPI / Stitch UI application server."""
    print("=" * 64)
    print("  EPISWARM STUDIO // FIELD DISPATCH BLUEPRINT")
    print("  Tactile Simulation Studio & Policy Advisor")
    print(f"  Serving at: http://{host}:{port}")
    print("=" * 64)
    uvicorn.run("episwarm.studio.app:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8501
    main(host=host, port=port)

