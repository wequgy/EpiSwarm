"""Gated Held-Out Evaluation on London Wave 2 (Phase 32 / Repair R1.4).

Evaluates status of the London Wave 2 held-out evaluation window under strict HeldOutGate.
Under Independent Audit 4 Finding Y4, London Wave 2 was accessed repeatedly with stand-in
approximations and is marked COMPROMISED for model generation v3.0.0.
Evaluation on compromised splits is strictly barred.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, Any

from episwarm.evidence.held_out import HeldOutGate, HeldOutGateError


def run_held_out_evaluation() -> Dict[str, Any]:
    print("=== EpiSwarm Phase 32: Gated Held-Out Wave 2 Evaluation ===")
    gate = HeldOutGate(log_path=Path("docs/validation/HELD_OUT_LOG.jsonl"))
    window_name = "London_Wave2_2020-09-01_to_2020-11-30"
    model_version = "v3.0.0"

    current_proto_hash = gate.compute_current_protocol_hash()
    print(f"Verified Committed PROTOCOL.md hash: {current_proto_hash}")

    is_comp = gate.is_window_compromised(window_name, model_version)
    if is_comp:
        print(f"\n[HELD-OUT GATE AUDIT NOTICE]")
        print(f"  Window: '{window_name}'")
        print(f"  Status: COMPROMISED for Model Generation {model_version}")
        print("  Reason: Independent Audit Finding Y4 (Stand-in evaluation & repeated access).")
        print("  Action: In accordance with EpiSwarm Scientific Rule 1 & Rule 5, further evaluation")
        print("          on this split is permanently invalidated. An external, unseen dataset")
        print("          (e.g., Birmingham/West Midlands Wave 1 or UK Wave 3) must be supplied externally.")

        # Update machine card
        card_path = Path("docs/validation/VALIDATION_CARD.json")
        if card_path.exists():
            card_data = json.loads(card_path.read_text(encoding="utf-8"))
        else:
            card_data = {"status": "UNCALIBRATED", "targets": {}}

        card_data["targets"]["held_out_wave2"] = {
            "passed": False,
            "status": "COMPROMISED",
            "reason": "Auditor finding Y4: Prior evaluations accessed local held-out dataset without hash chaining or counter increments; dataset compromised for v3.0.0.",
            "held_out_window": window_name,
            "external_dataset_required": True
        }

        val_targets = [k for k, v in card_data["targets"].items() if not v.get("in_sample", False)]
        passed_cnt = sum(1 for k in val_targets if card_data["targets"][k].get("passed", False))
        tot_cnt = len(val_targets)
        card_data["targets_passed"] = f"{passed_cnt}/{tot_cnt}"
        card_data["status"] = "UNVALIDATED" if passed_cnt == 0 else ("VALIDATED" if passed_cnt == tot_cnt else "PARTIALLY_VALIDATED")
        card_data["generated_at"] = datetime.now(timezone.utc).isoformat()

        card_path.write_text(json.dumps(card_data, indent=2), encoding="utf-8")
        print(f"\nUpdated machine validation card: {card_path} ({card_data['status']}, {card_data['targets_passed']})")

        return {
            "status": "COMPROMISED",
            "passed": False,
            "held_out_window": window_name,
            "protocol_hash": current_proto_hash
        }

    raise HeldOutGateError("Unexpected state: uncompromised evaluation requires external unseen dataset.")


if __name__ == "__main__":
    run_held_out_evaluation()
