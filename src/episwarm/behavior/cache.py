"""Persistent SQLite cache for behavioral policy decisions."""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Union


class DecisionCache:
    """Thread-safe SQLite persistent cache for (policy, question_id, situation, bucket) -> probabilities."""

    def __init__(self, db_path: Optional[Union[Path, str]] = None):
        if db_path is None:
            db_path = Path(".cache/behavior_decisions.sqlite")
        self.is_memory = (str(db_path) == ":memory:")
        self.db_path = ":memory:" if self.is_memory else Path(db_path)
        if not self.is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = None
        else:
            self._conn = sqlite3.connect(":memory:")
        self._mem_cache: Dict[str, Dict[str, float]] = {}
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.is_memory:
            return self._conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_cache (
                    key TEXT PRIMARY KEY,
                    policy TEXT,
                    question_id TEXT,
                    probabilities_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _make_key(self, policy: str, question_id: str, sit_hash: str, bucket_hash: str) -> str:
        return f"{policy}::{question_id}::{sit_hash}::{bucket_hash}"

    def get(
        self,
        policy: str,
        question_id: str,
        sit_hash: str,
        bucket_hash: str
    ) -> Optional[Dict[str, float]]:
        key = self._make_key(policy, question_id, sit_hash, bucket_hash)
        if key in self._mem_cache:
            return self._mem_cache[key]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT probabilities_json FROM decision_cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                res = json.loads(row[0])
                self._mem_cache[key] = res
                return res
        return None

    def put(
        self,
        policy: str,
        question_id: str,
        sit_hash: str,
        bucket_hash: str,
        probabilities: Dict[str, float]
    ) -> None:
        key = self._make_key(policy, question_id, sit_hash, bucket_hash)
        self._mem_cache[key] = probabilities
        prob_str = json.dumps(probabilities)
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO decision_cache (key, policy, question_id, probabilities_json) VALUES (?, ?, ?, ?)",
                    (key, policy, question_id, prob_str)
                )
                conn.commit()
        except Exception:
            pass
            conn.commit()

