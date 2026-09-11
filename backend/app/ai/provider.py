from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AIAnalysis(BaseModel):
    summary: str
    severity: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)


class AIProvider(ABC):
    """Provider interface used by workflow AI nodes."""

    @abstractmethod
    async def analyze(
        self,
        *,
        event: dict[str, Any],
        prompt: str | None = None,
    ) -> AIAnalysis:
        raise NotImplementedError


class FakeAIProvider(AIProvider):
    """Deterministic provider for local development and tests."""

    async def analyze(
        self,
        *,
        event: dict[str, Any],
        prompt: str | None = None,
    ) -> AIAnalysis:
        message = str(event.get("message") or "Sentry event")
        level = str(event.get("level") or "error").lower()

        if level in {"fatal", "critical"}:
            severity = "critical"
        elif level == "warning":
            severity = "medium"
        else:
            severity = "high"

        category = "database" if "postgres" in message.lower() or "database" in message.lower() else "application"

        return AIAnalysis(
            summary=message,
            severity=severity,
            category=category,
            confidence=0.95,
        )
