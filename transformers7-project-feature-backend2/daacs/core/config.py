import os

# Planner 모델 설정 (기본: gpt-5.1-codex-max)
PLANNER_MODEL = os.getenv("DAACS_PLANNER_MODEL", "gpt-5.1-codex-max")

# 지원되는 모델 목록
SUPPORTED_MODELS = {
    "gemini-3-pro-high": {
        "provider": "google",
        "model_name": "gemini-3-pro",
        "tier": "high"
    },
    "gemini-3-pro-low": {
        "provider": "google",
        "model_name": "gemini-3-pro",
        "tier": "low"
    },
    "claude-sonnet-4.5": {
        "provider": "anthropic",
        "model_name": "claude-sonnet-4.5",
        "tier": "standard"
    },
    "claude-sonnet-4.5-thinking": {
        "provider": "anthropic",
        "model_name": "claude-sonnet-4.5",
        "tier": "thinking"
    },
    "gpt-oss-120b": {
        "provider": "openai-compatible",
        "model_name": "gpt-oss-120b",
        "tier": "medium"
    },
    "gpt-5.1-codex-max": {
        "provider": "openai",
        "model_name": "gpt-5.1-codex-max",
        "tier": "max"
    },
    "gpt-5.1-codex": {
        "provider": "openai",
        "model_name": "gpt-5.1-codex",
        "tier": "standard"
    },
    "gpt-5.1": {
        "provider": "openai",
        "model_name": "gpt-5.1",
        "tier": "standard"
    },
    "gpt-5.1-codex-mini": {
        "provider": "openai",
        "model_name": "gpt-5.1-codex-mini",
        "tier": "mini"
    }
}

# Developer (Codex) 설정
DEVELOPER_TOOL = "codex"  # 고정

# Loop 설정
MAX_TURNS = int(os.getenv("DAACS_MAX_TURNS", "10"))
