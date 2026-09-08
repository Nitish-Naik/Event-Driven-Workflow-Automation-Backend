from abc import ABC, abstractmethod
from typing import Any


class IntegrationTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    async def execute(self, inputs: dict[str, Any]) -> Any:
        ...