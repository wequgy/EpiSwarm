"""Network Downloader & Evidence Registrar (Phase 26).

This module is the EXCLUSIVE, SOLE authorized mechanism in the entire EpiSwarm
codebase permitted to create records in the Evidence Ledger and designate data
as 'status: real'.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Optional
import httpx

from episwarm.evidence.ledger import EvidenceLedger, LedgerRecord, compute_sha256


class DownloadIntegrityError(Exception):
    """Raised when a download fails, returns non-200, or returns zero bytes."""
    pass


def fetch_and_register(
    url: str,
    dest_path: Path,
    license_name: str,
    notes: str = "",
    ledger: Optional[EvidenceLedger] = None,
    timeout: float = 45.0,
    headers: Optional[dict] = None
) -> LedgerRecord:
    """Fetch an empirical file from a verified URL and register it in the Evidence Ledger.

    Rules:
    1. Only real HTTP 200 responses with content are accepted.
    2. Zero-byte files or HTTP error statuses raise DownloadIntegrityError.
    3. The file is streamed to disk and hashed with SHA-256.
    4. An immutable LedgerRecord is immediately committed to the SQLite ledger.
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = ledger or EvidenceLedger()

    req_headers = {
        "User-Agent": "EpiSwarm-Evidence-Auditor/1.0 (+https://github.com/wequgy/EpiSwarm)"
    }
    if headers:
        req_headers.update(headers)

    hasher = hashlib.sha256()
    byte_count = 0

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            with client.stream("GET", url, headers=req_headers) as response:
                if response.status_code != 200:
                    raise DownloadIntegrityError(
                        f"Refusing to register download: HTTP status {response.status_code} from {url}"
                    )

                content_type = response.headers.get("content-type", "application/octet-stream")

                with open(dest_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if chunk:
                            hasher.update(chunk)
                            f.write(chunk)
                            byte_count += len(chunk)

        if byte_count == 0:
            if dest_path.exists():
                dest_path.unlink()
            raise DownloadIntegrityError(f"Refusing to register download: URL {url} returned 0 bytes.")

        sha256_digest = hasher.hexdigest()
        retrieved_at = datetime.now(timezone.utc).isoformat()

        record = LedgerRecord(
            id=f"rec_{sha256_digest[:16]}",
            url=url,
            retrieved_at=retrieved_at,
            sha256=sha256_digest,
            byte_count=byte_count,
            http_status=200,
            content_type=content_type,
            license=license_name,
            file_path=str(dest_path),
            record_status="verified",
            notes=notes
        )

        ledger.add_record(record)
        return record

    except Exception as e:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        if isinstance(e, DownloadIntegrityError):
            raise
        raise DownloadIntegrityError(f"Failed to fetch {url}: {str(e)}") from e

