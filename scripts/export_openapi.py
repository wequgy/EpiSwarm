"""Export FastAPI application OpenAPI schema to web/openapi.json."""

import json
from pathlib import Path
from episwarm.api.main import app


def export_openapi(output_path: Path = Path("web/openapi.json")):
    """Generate OpenAPI 3.x schema and write to disk."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    num_paths = len(schema.get("paths", {}))
    print(f"Successfully exported OpenAPI schema to {output_path} ({num_paths} paths documented).")


if __name__ == "__main__":
    export_openapi()
