from typing import Any

from app.ai.provider import AIProvider
from app.execution.contracts import ExecutionContext


class AIAnalysisNode:
    """Workflow node that delegates event analysis to an AI provider."""

    def __init__(self, provider: AIProvider):
        self.provider = provider

    async def execute(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        event = inputs.get("event")
        if not isinstance(event, dict):
            raise ValueError("AI analysis node requires an 'event' object input")

        prompt = config.get("prompt")
        result = await self.provider.analyze(event=event, prompt=prompt)
        return result.model_dump()
