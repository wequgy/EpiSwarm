"""Convenience CLI script to launch EpiSwarm Studio."""

import sys
import webbrowser
from episwarm.studio.server import main

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8501
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    main(host=host, port=port)
