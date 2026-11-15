"""Rule-Based Scenario Parser: Translates structured policy briefs into valid ScenarioPacks (Stage A5).

Deterministic rule-based parser that maps keyword patterns (e.g. school closures, workplace mandates)
into typed InterventionAction sequences with validated timing and parameters. Note: Real LLM generation is deferred to Stage R3.3.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import re
import yaml

from episwarm.packs.scenario import ScenarioPack, InterventionAction, SeedingConfig


class ScenarioAuthor:
    """Parses natural language policy intentions into valid ScenarioPack objects."""

    def __init__(self, base_scenario_dict: Optional[Dict[str, Any]] = None, model_name: Optional[str] = None):
        if base_scenario_dict is not None:
            self.base_dict = base_scenario_dict
        else:
            self.base_dict = {
                "name": "authored_scenario",
                "version": "1.0.0",
                "provenance": {"status": "synthetic", "source": "ScenarioAuthor"},
                "horizon_days": 90,
                "behavior_mode": "rule",
                "seeding": {"initial_cases_per_area": 30, "seeded_state": "I"},
                "interventions": []
            }
        from episwarm.advisor.llm_client import LLMAgentRuntime
        self.runtime = LLMAgentRuntime(
            agent_name="scenario_author",
            system_instruction=(
                "You are the EpiSwarm Scenario Author. You translate health authority intentions "
                "into structured, temporal InterventionAction lists. You never invent unsupported parameters "
                "and ensure all policy dates, stringencies, and costs comply with engine capabilities."
            ),
            model_name=model_name,
        )

    def author_interactive(self, brief_text: str) -> Tuple[ScenarioPack, Any]:
        """Interactively author a ScenarioPack with transcript logging and LLM/fallback triage."""
        def fallback():
            return f"Parsed scenario brief: {brief_text}"
        reply, transcript = self.runtime.run(brief_text, fallback_fn=fallback)
        sc = self.parse_natural_language_brief(brief_text)
        return sc, transcript

    def parse_natural_language_brief(self, brief_text: str) -> ScenarioPack:
        """Parse natural language brief text and synthesize typed ScenarioPack."""
        interventions: List[InterventionAction] = []
        text_lower = brief_text.lower()

        # Parse school closure
        if "school" in text_lower:
            start_day = 10
            duration = 21
            m_start = re.search(r"day\s*(\d+)", text_lower)
            if m_start:
                start_day = int(m_start.group(1))
            m_dur = re.search(r"(\d+)\s*(?:week|weeks)", text_lower)
            if m_dur:
                duration = int(m_dur.group(1)) * 7
            elif "month" in text_lower:
                duration = 30

            interventions.append(InterventionAction(
                name="school_closure_mandate",
                measure_type="school_closure",
                area_id="ALL",
                start_day=start_day,
                end_day=start_day + duration,
                stringency=1.0,
                cost_per_day=1.5
            ))

        # Parse workplace / work from home
        if "work" in text_lower or "workplace" in text_lower or "wfh" in text_lower:
            start_day = 15
            duration = 30
            m_start = re.search(r"(?:work|wfh).*?day\s*(\d+)", text_lower)
            if m_start:
                start_day = int(m_start.group(1))

            interventions.append(InterventionAction(
                name="workplace_wfh_mandate",
                measure_type="workplace_closure",
                area_id="ALL",
                start_day=start_day,
                end_day=start_day + duration,
                stringency=0.80,
                cost_per_day=3.0
            ))

        # Parse masks
        if "mask" in text_lower or "face covering" in text_lower:
            start_day = 5
            duration = 60
            interventions.append(InterventionAction(
                name="universal_mask_mandate",
                measure_type="mask_wearing",
                area_id="ALL",
                start_day=start_day,
                end_day=start_day + duration,
                stringency=0.75,
                cost_per_day=0.2
            ))

        # Parse lockdown / stay at home
        if "lockdown" in text_lower or "stay at home" in text_lower:
            start_day = 20
            duration = 45
            m_start = re.search(r"(?:lockdown|stay at home).*?day\s*(\d+)", text_lower)
            if not m_start:
                m_start = re.search(r"day\s*(\d+)", text_lower)
            if m_start:
                start_day = int(m_start.group(1))

            m_dur = re.search(r"for\s*(\d+)\s*days?", text_lower)
            if m_dur:
                duration = int(m_dur.group(1))
            elif "week" in text_lower:
                m_w = re.search(r"(\d+)\s*weeks?", text_lower)
                if m_w:
                    duration = int(m_w.group(1)) * 7

            interventions.append(InterventionAction(
                name="stay_at_home_order",
                measure_type="stay_at_home",
                area_id="ALL",
                start_day=start_day,
                end_day=start_day + duration,
                stringency=0.90,
                cost_per_day=5.0
            ))

        # Parse custom horizon if specified
        horizon = self.base_dict.get("horizon_days", 90)
        m_hor = re.search(r"(\d+)\s*days?", text_lower)
        if m_hor:
            horizon = max(horizon, int(m_hor.group(1)))

        sc_dict = dict(self.base_dict)
        sc_dict["horizon_days"] = horizon
        sc_dict["interventions"] = [i.model_dump() for i in interventions]
        return ScenarioPack(**sc_dict)
