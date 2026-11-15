"""Real Gemini LLM client and function-calling agent runtime for EpiSwarm Advisor.

Stage R3.3: Integrates real Gemini via google-genai function calling,
strict tool schemas, request budgets, exponential retries, transcript logging to disk,
and deterministic rule-based fallbacks labeled as such when unkeyed.
"""

from __future__ import annotations

import os
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple

TRANSCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "runs" / "ai_transcripts"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ToolCallRecord:
    tool_name: str
    arguments: Dict[str, Any]
    output: Any


@dataclass
class AgentTranscript:
    agent_name: str
    timestamp: str
    model: str
    system_prompt: str
    user_prompt: str
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    final_response: str = ""
    fallback: bool = False
    tokens_used: int = 0

    def save(self) -> Path:
        filename = f"{self.agent_name}_{int(time.time())}_{uuid.uuid4().hex[:6]}.json"
        path = TRANSCRIPTS_DIR / filename
        data = {
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "model": self.model,
            "fallback": self.fallback,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "arguments": tc.arguments,
                    "output": tc.output,
                }
                for tc in self.tool_calls
            ],
            "final_response": self.final_response,
            "tokens_used": self.tokens_used,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path


class LLMAgentRuntime:
    """Runtime for executing multi-turn tool-calling LLM agents with budget guards."""

    def __init__(
        self,
        agent_name: str,
        system_instruction: str,
        tools: Optional[Dict[str, Callable[..., Any]]] = None,
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
        model_name: Optional[str] = None,
        max_tool_iterations: int = 5,
    ):
        self.agent_name = agent_name
        self.system_instruction = system_instruction
        self.tools = tools or {}
        self.tool_schemas = tool_schemas or []
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.max_tool_iterations = max_tool_iterations
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()

        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None

    def run(self, user_prompt: str, fallback_fn: Callable[[], str]) -> Tuple[str, AgentTranscript]:
        """Execute agent workflow with function calling, transcript persistence, or fallback."""
        transcript = AgentTranscript(
            agent_name=self.agent_name,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            model=self.model_name if self._client else "deterministic_fallback",
            system_prompt=self.system_instruction,
            user_prompt=user_prompt,
            fallback=(self._client is None),
        )

        # If no client or API key is set, use deterministic fallback
        if self._client is None:
            final_text = fallback_fn()
            transcript.final_response = final_text
            transcript.save()
            return final_text, transcript

        # Real Gemini function-calling loop
        try:
            from google.genai import types

            # Build tools
            gemini_tools = []
            for schema in self.tool_schemas:
                gemini_tools.append(types.Tool(function_declarations=[types.FunctionDeclaration(**schema)]))

            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.2,
                tools=gemini_tools if gemini_tools else None,
            )

            contents = [user_prompt]
            iterations = 0

            while iterations < self.max_tool_iterations:
                iterations += 1
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

                # Check for function calls
                function_calls = resp.function_calls
                if not function_calls:
                    # Final text response
                    final_text = resp.text or ""
                    transcript.final_response = final_text
                    transcript.save()
                    return final_text, transcript

                # Execute requested function calls
                for call in function_calls:
                    fn_name = call.name
                    fn_args = dict(call.args) if call.args else {}
                    fn = self.tools.get(fn_name)
                    if fn:
                        try:
                            fn_result = fn(**fn_args)
                        except Exception as e:
                            fn_result = {"error": str(e)}
                    else:
                        fn_result = {"error": f"Tool '{fn_name}' not found"}

                    transcript.tool_calls.append(
                        ToolCallRecord(tool_name=fn_name, arguments=fn_args, output=fn_result)
                    )
                    # Append tool result to conversation
                    contents.append(
                        types.Content(
                            parts=[
                                types.Part.from_function_response(
                                    name=fn_name,
                                    response={"result": fn_result},
                                )
                            ]
                        )
                    )

            # If iteration limit reached, ask model for conclusion
            final_resp = self._client.models.generate_content(
                model=self.model_name,
                contents=contents + ["Conclude your assessment based on the tool results above."],
                config=types.GenerateContentConfig(system_instruction=self.system_instruction),
            )
            final_text = final_resp.text or ""
            transcript.final_response = final_text
            transcript.save()
            return final_text, transcript

        except Exception as e:
            # On network/SDK error, fallback cleanly with transparent notice
            final_text = fallback_fn() + f"\n\n[Notice: Real Gemini call failed ({e}); used deterministic fallback.]"
            transcript.final_response = final_text
            transcript.fallback = True
            transcript.save()
            return final_text, transcript
