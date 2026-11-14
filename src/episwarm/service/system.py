"""System health and backend integration status service facade."""

from datetime import datetime, timezone
import os
import requests
from typing import List

from episwarm.service.models import BackendItem, BackendsResponse, HealthResponse


class SystemService:
    """Service inspecting system health, operational status, and backend integrations safely."""

    def __init__(self, service_name: str = "episwarm-api", version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version

    def get_health(self) -> HealthResponse:
        """Return basic uptime and operational health status."""
        return HealthResponse(
            status="ok",
            service=self.service_name,
            version=self.version,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_backends(self) -> BackendsResponse:
        """Inspect and report readiness of simulation and AI reasoning backends without exposing secrets."""
        backends: List[BackendItem] = []

        # 1. Native ABM Simulation Engine
        backends.append(
            BackendItem(
                name="engine_abm",
                status="available",
                configured=True,
                active_model="episwarm-vectorized-numpy",
                details={
                    "type": "native_simulation_engine",
                    "supports_replicates": True,
                    "supports_spatial": True,
                    "supports_resources": True,
                },
            )
        )

        # 2. Google Gemini API Backend
        gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        backends.append(
            BackendItem(
                name="gemini",
                status="available" if bool(gemini_key) else "unavailable",
                configured=bool(gemini_key),
                active_model=gemini_model if gemini_key else None,
                details={
                    "provider": "Google GenAI",
                    "configured": bool(gemini_key),
                    "model": gemini_model,
                    "key_present": bool(gemini_key),
                },
            )
        )

        # 3. TypeSafe Jev Policy Backend
        jev_key = os.getenv("TYPESAFE_API_KEY", "").strip()
        jev_url = os.getenv("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone")
        backends.append(
            BackendItem(
                name="typesafe_jev",
                status="available" if bool(jev_key) else "unavailable",
                configured=bool(jev_key),
                active_model="jev-policy-v1" if jev_key else None,
                details={
                    "provider": "TypeSafe AI",
                    "configured": bool(jev_key),
                    "endpoint_url": jev_url,
                    "key_present": bool(jev_key),
                },
            )
        )

        # 4. Local Logprob / Ollama LLM Backend
        local_url = os.getenv("LOCAL_LLM_BASE_URL", "").strip().rstrip("/")
        local_reachable = False
        if local_url:
            try:
                resp = requests.get(f"{local_url}/api/tags", timeout=0.5)
                local_reachable = (resp.status_code == 200)
            except Exception:
                try:
                    resp = requests.get(f"{local_url}/v1/models", timeout=0.5)
                    local_reachable = (resp.status_code == 200)
                except Exception:
                    local_reachable = False

        backends.append(
            BackendItem(
                name="local_llm",
                status="available" if local_reachable else ("configured" if local_url else "unavailable"),
                configured=bool(local_url),
                active_model=os.getenv("LOCAL_LLM_MODEL", "llama3:latest") if local_url else None,
                details={
                    "provider": "Ollama / Local OpenAI Compat",
                    "base_url": local_url or "not configured",
                    "reachable": local_reachable,
                },
            )
        )

        # 5. OpenAI Compatible Backend
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        backends.append(
            BackendItem(
                name="openai",
                status="available" if bool(openai_key) else "unavailable",
                configured=bool(openai_key),
                active_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini") if openai_key else None,
                details={
                    "provider": "OpenAI",
                    "configured": bool(openai_key),
                    "key_present": bool(openai_key),
                },
            )
        )

        # 6. SQLite Job Queue & Storage
        backends.append(
            BackendItem(
                name="sqlite_jobs",
                status="available",
                configured=True,
                details={
                    "storage": "sqlite3",
                    "persistence": "file_backed",
                    "wal_mode": True,
                },
            )
        )

        return BackendsResponse(backends=backends)
