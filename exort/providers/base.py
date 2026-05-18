"""
Base provider — abstract LLM backend interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, Optional


@dataclass
class ProviderResponse:
    content: str = ""
    tool_calls: list = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    model: str = ""
    finish_reason: str = ""


class BaseProvider(ABC):
    name: str = ""
    needs_key: bool = True

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 default_model: Optional[str] = None, **kw):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model

    @abstractmethod
    def chat(self, messages, model=None, tools=None, temperature=0.7,
             max_tokens=4096, stream=False) -> ProviderResponse | Generator:
        pass

    @abstractmethod
    def ok(self) -> bool:
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}({self.default_model})"
