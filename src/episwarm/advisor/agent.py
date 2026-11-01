"""Advisor Agent: Autonomous intervention planning using Gemini LLM function-calling (google-genai) with deterministic fallback (Spec 4.7 & Phase 16)."""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from pydantic import ValidationError
from episwarm.advisor.schemas import Recommendation
from episwarm.advisor.tools import AdvisorToolKit
from episwarm.packs.scenario import InterventionAction

logger = logging.getLogger(__name__)


class AdvisorAgent:
    """Agentic intervention advisor employing Gemini function calling with strict schema validation and deterministic fallback."""

    def __init__(
        self,
        toolkit: AdvisorToolKit,
        run_budget: int = 5,
        model_name: Optional[str] = None,
        gemini_client: Optional[Any] = None,
        transcript_dir: Optional[str] = "docs/transcripts"
    ):
        self.toolkit = toolkit
        self.run_budget = run_budget
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        self.client = gemini_client
        self.transcript_dir = transcript_dir
        self.transcripts: List[Dict[str, Any]] = []

    def _init_gemini_client(self) -> Optional[Any]:
        """Initialize real Google GenAI client if GEMINI_API_KEY is present."""
        if self.client is not None:
            return self.client

        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        if not api_key:
            return None

        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            return self.client
        except Exception as e:
            logger.warning(f"Failed to initialize google-genai Client: {e}")
            return None

    def _save_transcript(self, transcript_record: Dict[str, Any]):
        """Persist advisory dialogue and tool execution transcript to disk."""
        self.transcripts.append(transcript_record)
        if self.transcript_dir:
            try:
                p = Path(self.transcript_dir)
                p.mkdir(parents=True, exist_ok=True)
                ts_file = p / f"advisor_transcript_{int(time.time() * 1000)}.json"
                ts_file.write_text(json.dumps(self.transcripts, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not write advisor transcript to disk: {e}")

    def _deterministic_fallback(self, reason: str) -> Recommendation:
        """Deterministic policy evaluation fallback when Gemini is unavailable, exhausted, or fails."""
        baseline_id = self.toolkit.run_scenario({"interventions": []})
        baseline_metrics = self.toolkit.get_metrics(baseline_id)
        explored_runs = [baseline_id]

        best_run_id = baseline_id
        best_deaths = baseline_metrics["cumulative_deaths"]
        best_measures: List[InterventionAction] = []

        candidate_plans = [
            [
                InterventionAction(
                    name="early_school_closure",
                    measure_type="school_closure",
                    area_id="ALL",
                    start_day=7,
                    end_day=28,
                    stringency=1.0,
                    cost_per_day=1.0
                )
            ],
            [
                InterventionAction(
                    name="school_closure",
                    measure_type="school_closure",
                    area_id="ALL",
                    start_day=7,
                    end_day=28,
                    stringency=1.0,
                    cost_per_day=1.0
                ),
                InterventionAction(
                    name="surge_icu_capacity",
                    measure_type="surge_beds",
                    area_id="ALL",
                    start_day=10,
                    end_day=45,
                    stringency=0.5,
                    cost_per_day=1.5
                )
            ],
            [
                InterventionAction(
                    name="workplace_reduction",
                    measure_type="workplace_reduction",
                    area_id="ALL",
                    start_day=10,
                    end_day=30,
                    stringency=0.5,
                    cost_per_day=2.5
                )
            ]
        ]

        for plan in candidate_plans[:max(1, self.run_budget - 1)]:
            run_id = self.toolkit.run_scenario({
                "interventions": [p.model_dump() for p in plan]
            })
            explored_runs.append(run_id)
            metrics = self.toolkit.get_metrics(run_id)

            if metrics["cumulative_deaths"] < best_deaths:
                best_deaths = metrics["cumulative_deaths"]
                best_run_id = run_id
                best_measures = plan

        if not best_measures and candidate_plans:
            best_measures = candidate_plans[0]

        reduction_pct = 0.0
        if baseline_metrics["cumulative_deaths"] > 0:
            reduction_pct = (baseline_metrics["cumulative_deaths"] - best_deaths) / baseline_metrics["cumulative_deaths"] * 100.0

        priority_areas = list(self.toolkit.pop.area_id_to_int.keys())[:3]

        rec = Recommendation(
            priority_areas=priority_areas,
            recommended_measures=best_measures,
            evidence_run_ids=explored_runs,
            objective_achieved=(best_deaths < baseline_metrics["cumulative_deaths"]),
            predicted_deaths_reduction=round(reduction_pct, 1),
            caveats=[
                f"Deterministic fallback executed ({reason}).",
                "Evaluated structured candidate schedules without stochastic LLM exploration.",
                "Decision-makers must verify local capacity thresholds."
            ]
        )
        self._save_transcript({
            "mode": "deterministic_fallback",
            "reason": reason,
            "recommendation": rec.model_dump()
        })
        return rec

    def run_advisory_loop(self) -> Recommendation:
        """Run advisory cycle with Gemini function-calling or deterministic fallback."""
        client = self._init_gemini_client()
        if client is None:
            return self._deterministic_fallback("GEMINI_API_KEY not configured or client initialization failed")

        try:
            from google.genai import types
        except ImportError:
            return self._deterministic_fallback("google-genai package not available")

        # Define tool functions callable by the model
        def list_available_measures() -> str:
            """Retrieve the catalog of supported public health measures, parameters, and daily costs."""
            return json.dumps(self.toolkit.list_measures())

        def test_scenario(interventions_json: str) -> str:
            """Run a counterfactual simulation scenario with specified interventions (as a JSON array of actions)."""
            try:
                actions = json.loads(interventions_json)
                if not isinstance(actions, list):
                    return json.dumps({"error": "interventions_json must be a JSON array of intervention action objects."})
                run_id = self.toolkit.run_scenario({"interventions": actions})
                metrics = self.toolkit.get_metrics(run_id)
                return json.dumps(metrics)
            except Exception as ex:
                return json.dumps({"error": f"Failed to test scenario: {str(ex)}"})

        def compare_scenarios(run_id_a: str, run_id_b: str) -> str:
            """Compare cumulative metrics and trade-offs between two simulation run IDs."""
            return json.dumps(self.toolkit.compare(run_id_a, run_id_b))

        tool_map = {
            "list_available_measures": list_available_measures,
            "test_scenario": test_scenario,
            "compare_scenarios": compare_scenarios
        }

        tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="list_available_measures",
                    description="Retrieve the catalog of supported public health measures, parameters, and daily costs."
                ),
                types.FunctionDeclaration(
                    name="test_scenario",
                    description="Run a counterfactual simulation scenario with specified interventions (as a JSON array of actions).",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "interventions_json": {
                                "type": "STRING",
                                "description": "JSON string representing array of intervention actions (each with name, measure_type, area_id, start_day, end_day, stringency, cost_per_day)"
                            }
                        },
                        "required": ["interventions_json"]
                    }
                ),
                types.FunctionDeclaration(
                    name="compare_scenarios",
                    description="Compare cumulative metrics and trade-offs between two simulation run IDs.",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "run_id_a": {"type": "STRING", "description": "First run ID"},
                            "run_id_b": {"type": "STRING", "description": "Second run ID"}
                        },
                        "required": ["run_id_a", "run_id_b"]
                    }
                )
            ])
        ]

        system_instruction = (
            "You are the EpiSwarm Public Health Policy Advisor. You must evaluate candidate interventions to reduce "
            "epidemic mortality and clinical overflow within economic and social constraints.\n"
            "Workflow:\n"
            "1. Call `test_scenario` with empty interventions `[]` to establish the baseline.\n"
            "2. Call `list_available_measures` to inspect available interventions.\n"
            "3. Test 1 to 3 candidate intervention packages using `test_scenario`.\n"
            "4. Formulate your final response strictly as a JSON object matching this schema:\n"
            "{\n"
            '  "priority_areas": ["A01", ...],\n'
            '  "recommended_measures": [{"name": "...", "measure_type": "...", "area_id": "...", "start_day": 7, "end_day": 28, "stringency": 1.0, "cost_per_day": 1.0}],\n'
            '  "evidence_run_ids": ["run_...", ...],\n'
            '  "objective_achieved": true,\n'
            '  "predicted_deaths_reduction": 45.2,\n'
            '  "caveats": ["..."],\n'
            '  "human_in_the_loop_advisory": "..."\n'
            "}"
        )

        history: List[Any] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="Please evaluate response strategies for the current outbreak and recommend an optimal intervention plan.")]
            )
        ]

        # Multi-turn tool calling loop with request budget and backoff
        for call_idx in range(self.run_budget):
            response = None
            for backoff_retry in range(3):
                try:
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=history,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            tools=tools,
                            temperature=0.2
                        )
                    )
                    break
                except Exception as err:
                    err_msg = str(err)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        wait_sec = min(2 ** (backoff_retry + 1), 8)
                        logger.warning(f"Rate limit 429 hit; backing off {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        logger.error(f"Gemini API invocation error: {err}")
                        return self._deterministic_fallback(f"Gemini API invocation error: {err}")

            if response is None:
                return self._deterministic_fallback("Exceeded API retry budget on rate limits")

            # Check for tool call requests
            function_calls = getattr(response, "function_calls", None)
            if not function_calls and hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                    function_calls = [p.function_call for p in candidate.content.parts if getattr(p, "function_call", None)]

            if function_calls:
                # Append model content containing function calls to history
                if hasattr(response, "candidates") and response.candidates:
                    history.append(response.candidates[0].content)

                tool_response_parts = []
                for fc in function_calls:
                    fn_name = getattr(fc, "name", "")
                    fn_args = getattr(fc, "args", {}) or {}
                    self._save_transcript({
                        "step": call_idx,
                        "action": "function_call",
                        "function": fn_name,
                        "args": fn_args
                    })

                    fn = tool_map.get(fn_name)
                    if fn:
                        try:
                            fn_result = fn(**fn_args)
                        except Exception as tool_ex:
                            fn_result = json.dumps({"error": f"Tool execution failed: {str(tool_ex)}"})
                    else:
                        fn_result = json.dumps({"error": f"Unknown tool '{fn_name}'"})

                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": fn_result}
                        )
                    )

                history.append(types.Content(role="user", parts=tool_response_parts))
                continue

            # Model returned final text answer
            text_response = getattr(response, "text", "")
            if not text_response and hasattr(response, "candidates") and response.candidates:
                parts = response.candidates[0].content.parts
                text_response = "".join(p.text for p in parts if getattr(p, "text", None))

            self._save_transcript({
                "step": call_idx,
                "action": "final_text",
                "text": text_response
            })

            # Parse and validate Recommendation schema
            rec = self._parse_and_validate_recommendation(text_response)
            if rec is not None:
                return rec

            # Schema parsing failed: attempt one retry with schema feedback
            retry_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text="Your previous output was not valid JSON conforming to the Recommendation schema. Please output strictly valid JSON conforming to the schema now.")]
            )
            history.append(retry_content)
            try:
                retry_resp = client.models.generate_content(
                    model=self.model_name,
                    contents=history,
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                rec = self._parse_and_validate_recommendation(getattr(retry_resp, "text", ""))
                if rec is not None:
                    return rec
            except Exception as parse_err:
                logger.warning(f"Retry parsing failed: {parse_err}")

            return self._deterministic_fallback("Model output failed strict Recommendation schema validation after retry")

        return self._deterministic_fallback("Advisor loop exceeded maximum request budget")

    def _parse_and_validate_recommendation(self, text: str) -> Optional[Recommendation]:
        """Strictly validate and extract Recommendation from model response text."""
        if not text:
            return None
        # Extract json code block if wrapped
        raw = text.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return None
            return Recommendation(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.debug(f"Recommendation validation failure: {e}")
            return None
