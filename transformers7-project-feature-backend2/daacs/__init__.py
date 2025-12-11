"""
DAACS v6.0 - Developer Agent Automation & Coordination System

Main modules:
- config_loader: Configuration management (YAML + env vars)
- llm_source_provider: LLM source abstraction (CLI Assistant vs Plugin)
- models: State management (TypedDict with reducers)
- graph: LangGraph workflow and SubGraphs
- logging: Turn-based and workflow logging
"""

__version__ = "6.0.0"

from .config_loader import DAACSConfig
from .llm_source_provider import LLMSource, CLIAssistantLLMSource, PluginLLMSource, LLMSourceFactory
from .models import DAACSState, create_initial_daacs_state
from .daacs_logging import DAACSLogger

__all__ = [
    "DAACSConfig",
    "LLMSource",
    "CLIAssistantLLMSource",
    "PluginLLMSource",
    "LLMSourceFactory",
    "DAACSState",
    "create_initial_daacs_state",
    "DAACSLogger",
]
