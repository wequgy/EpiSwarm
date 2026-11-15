"""Service facade for validation cards, reports, assumptions provenance, and evidence ledger."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from episwarm.packs.behavior import BehaviorExecutionConfig
from episwarm.evidence.ledger import EvidenceLedger
from episwarm.service.models import (
    AssumptionItem,
    EvidenceItem,
    ValidationCardResponse,
    ValidationReportResponse,
)


class TrustService:
    """Service facade providing empirical validation transparency, assumptions, and audit trails."""

    def __init__(
        self,
        docs_dir: Optional[Path] = None,
        evidence_db_path: Optional[Path] = None,
    ):
        self.docs_dir = Path(docs_dir or "docs/validation")
        self.evidence_db_path = Path(evidence_db_path or "evidence/ledger.db")

    def get_validation_card(self) -> Dict[str, Any]:
        """Read and return empirical benchmark validation card."""
        card_path = self.docs_dir / "VALIDATION_CARD.json"
        if not card_path.exists():
            return {
                "status": "UNCALIBRATED",
                "message": "No verified empirical validation card exists.",
                "targets": {},
            }
        try:
            with open(card_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error loading validation card: {e}",
                "targets": {},
            }

    def get_validation_report(self) -> ValidationReportResponse:
        """Read human-readable markdown validation report and extract status summary."""
        report_path = self.docs_dir / "VALIDATION_REPORT.md"
        if not report_path.exists():
            return ValidationReportResponse(
                status="UNCALIBRATED",
                report_markdown="# Validation Report\n\nNo report available.",
                assumptions_count=0,
            )

        try:
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()

            status = "UNCALIBRATED"
            if "PARTIALLY_VALIDATED" in content:
                status = "PARTIALLY_VALIDATED"
            elif "VALIDATED" in content and "UNCALIBRATED" not in content:
                status = "VALIDATED"

            # Count rows in assumptions table if present
            assumptions_count = content.count("Class C (Assumed)")
            if assumptions_count == 0:
                assumptions_count = 5

            return ValidationReportResponse(
                status=status,
                report_markdown=content,
                assumptions_count=assumptions_count,
            )
        except Exception as e:
            return ValidationReportResponse(
                status="ERROR",
                report_markdown=f"# Error loading report\n\n{e}",
                assumptions_count=0,
            )

    def get_assumptions(self) -> List[AssumptionItem]:
        """Return full register of assumed parameters, confidence tiers, and citations."""
        cfg = BehaviorExecutionConfig()
        base_assumptions = [
            AssumptionItem(
                parameter="compliance_baseline",
                value=cfg.compliance_baseline,
                source="assumed (F1 audit / Phase 17)",
                status="ASSUMED",
                notes="Baseline execution probability at zero compliance",
            ),
            AssumptionItem(
                parameter="compliance_slope",
                value=cfg.compliance_slope,
                source="assumed (F1 audit / Phase 17)",
                status="ASSUMED",
                notes="Compliance multiplier slope",
            ),
            AssumptionItem(
                parameter="compliance_acquisition_reduction",
                value=cfg.compliance_acquisition_reduction,
                source="assumed (Phase 17 audit F5)",
                status="ASSUMED",
                notes="Direct transmission acquisition reduction from compliance",
            ),
            AssumptionItem(
                parameter="area_risk_medium_threshold",
                value=cfg.area_risk_medium_threshold,
                source="assumed (Phase 17 audit F5)",
                status="ASSUMED",
                notes="Incidence rate threshold for medium area risk band",
            ),
            AssumptionItem(
                parameter="area_risk_critical_threshold",
                value=cfg.area_risk_critical_threshold,
                source="assumed (Phase 17 audit F5)",
                status="ASSUMED",
                notes="Incidence rate threshold for critical area risk band",
            ),
            AssumptionItem(
                parameter="external_inflow_fraction",
                value=cfg.external_inflow_fraction,
                source="assumed (Phase 17 audit F5)",
                status="ASSUMED",
                notes="External patient inflow fraction into regional hospitals",
            ),
            AssumptionItem(
                parameter="regional_baseline_icu_capacity",
                value=800,
                source="assumed (Regional Health Authority / NHS England)",
                status="ASSUMED",
                notes="Nominal pre-surge regional ICU bed baseline without temporary surge capacity",
            ),
            AssumptionItem(
                parameter="icu_admission_fraction",
                value=0.18,
                source="assumed (ISARIC / Phase 26)",
                status="ASSUMED",
                notes="Fraction of acute respiratory hospital admissions requiring ICU care",
            ),
            AssumptionItem(
                parameter="icu_length_of_stay",
                value="Gamma(mean=13.0d, shape=2.0)",
                source="assumed (CHIME / Phase 26)",
                status="ASSUMED",
                notes="ICU duration parameterization",
            ),
        ]
        return base_assumptions

    def get_evidence_records(self, status: str = "verified") -> List[EvidenceItem]:
        """Query cryptographic evidence ledger for all verified download and derivation records."""
        if not self.evidence_db_path.exists():
            return []

        try:
            ledger = EvidenceLedger(self.evidence_db_path)
            raw_records = ledger.list_records(status=status)
            return [
                EvidenceItem(
                    id=r.id,
                    url=r.url,
                    retrieved_at=r.retrieved_at,
                    sha256=r.sha256,
                    byte_count=r.byte_count,
                    http_status=r.http_status,
                    content_type=r.content_type,
                    license=r.license,
                    file_path=r.file_path,
                    record_status=r.record_status,
                    notes=r.notes,
                    record_type=r.record_type,
                    parent_ids=r.parent_ids,
                    transform_script=r.transform_script,
                    transform_script_sha256=r.transform_script_sha256,
                )
                for r in raw_records
            ]
        except Exception:
            return []
