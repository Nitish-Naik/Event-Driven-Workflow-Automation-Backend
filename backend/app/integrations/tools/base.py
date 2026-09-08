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

    @property
    @abstractmethod
    def execute(self, inputs: dict[str, Any]) -> Any:
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        ...

    @property
    @abstractmethod
    async def execute(self, inputs : dict[str, Any]) -> Any:
        ...