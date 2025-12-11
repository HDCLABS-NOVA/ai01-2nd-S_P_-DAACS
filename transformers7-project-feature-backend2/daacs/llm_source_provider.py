"""
DAACS v6.0 - LLM Source Provider
역할별로 CLI Assistant의 LLM 또는 플러그인 LLM을 선택할 수 있는 추상화 계층
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import subprocess
import json


class LLMSource(ABC):
    """LLM 소스 베이스 클래스 (CLI Assistant 또는 Plugin)"""

    @abstractmethod
    def invoke(self, prompt: str, **kwargs) -> str:
        """LLM 호출"""
        pass

    @abstractmethod
    def invoke_structured(self, prompt: str, schema: Optional[Dict] = None) -> Dict:
        """구조화된 출력 (JSON)"""
        pass


class CLIAssistantLLMSource(LLMSource):
    """
    CLI Assistant의 내장 LLM 사용

    예: Claude Code를 실행하면 내부적으로 Claude의 LLM이 동작
    Codex를 실행하면 내부적으로 GPT의 LLM이 동작
    """

    def __init__(
        self,
        cli_type: str,
        temperature: float = 0.7,
        timeout_sec: int = 60,
        fallback_config: Optional[Dict] = None
    ):
        """
        Args:
            cli_type: CLI Assistant 타입 (codex, claude_code, cursor, aider)
            temperature: LLM temperature
            timeout_sec: 타임아웃 (초)
            fallback_config: Fallback 플러그인 LLM 설정
        """
        self.cli_type = cli_type
        self.temperature = temperature
        self.timeout_sec = timeout_sec
        self.fallback_config = fallback_config
        
        # Initialize CodexClient
        from .llm.cli_executor import CodexClient
        self.client = CodexClient(
            cwd=".",  # Default to current directory or project root handled by client
            timeout_sec=timeout_sec,
            client_name="cli_assistant",
            cli_type=cli_type
        )

    def invoke(self, prompt: str, **kwargs) -> str:
        """CLI Assistant LLM 호출 (실패 시 Fallback)"""

        try:
            # Use CodexClient to execute
            result = self.client.execute(prompt)
            
            if result.startswith("Error:") or result.startswith("Exception:"):
                raise RuntimeError(f"CLI Assistant failed: {result}")
                
            return result

        except Exception as e:
            print(f"[WARN] CLI Assistant LLM failed: {e}")

            # Fallback to Plugin LLM
            if self.fallback_config:
                print(f"🔄 Falling back to Plugin LLM ({self.fallback_config['provider']})")
                fallback_source = PluginLLMSource(
                    provider=self.fallback_config["provider"],
                    model=self.fallback_config.get("model", "gpt-5.1"),
                    temperature=self.temperature
                )
                return fallback_source.invoke(prompt, **kwargs)

            raise RuntimeError(f"CLI Assistant LLM unavailable and no fallback configured: {e}")

    def invoke_structured(self, prompt: str, schema: Optional[Dict] = None) -> Dict:
        """구조화된 출력"""
        response = self.invoke(prompt + "\n\nRespond in JSON format.")

        # JSON 파싱 시도
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # JSON이 아니면 텍스트를 감싸서 반환
            return {"response": response}


class PluginLLMSource(LLMSource):
    """
    플러그인 LLM 사용 (Groq, Claude, Gemini, GPT 등)
    실제 구현은 추후 LLM Registry에서 로드
    """

    def __init__(
        self,
        provider: str,
        model: str,
        temperature: float = 0.7,
        api_key: Optional[str] = None
    ):
        """
        Args:
            provider: LLM 프로바이더 (groq, claude, gemini, openai)
            model: 모델 이름
            temperature: LLM temperature
            api_key: API 키 (옵션, 환경 변수에서 자동 로드)
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.api_key = api_key

        # LLM 플러그인 초기화
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """LLM 플러그인 초기화"""
        import os
        
        if self.provider == "openai":
            try:
                from openai import OpenAI
                api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    print("[WARN] OPENAI_API_KEY not found. OpenAI plugin will fail.")
                    return None
                return OpenAI(api_key=api_key)
            except ImportError:
                print("[WARN] openai package not installed.")
                return None
            except Exception as e:
                print(f"[WARN] Failed to initialize OpenAI: {e}")
                return None
        
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    print("[WARN] ANTHROPIC_API_KEY not found. Anthropic plugin will fail.")
                    return None
                return Anthropic(api_key=api_key)
            except ImportError:
                print("[WARN] anthropic package not installed.")
                return None
            except Exception as e:
                print(f"[WARN] Failed to initialize Anthropic: {e}")
                return None
        
        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                api_key = self.api_key or os.environ.get("GOOGLE_API_KEY")
                if not api_key:
                    print("[WARN] GOOGLE_API_KEY not found. Gemini plugin will fail.")
                    return None
                genai.configure(api_key=api_key)
                return genai.GenerativeModel(self.model)
            except ImportError:
                print("[WARN] google-generativeai package not installed.")
                return None
            except Exception as e:
                print(f"[WARN] Failed to initialize Gemini: {e}")
                return None
                
        print(f"[PluginLLMSource] Initialized: {self.provider}/{self.model}")
        return None

    def invoke(self, prompt: str, **kwargs) -> str:
        """플러그인 LLM 호출"""
        if self.llm:
            try:
                if self.provider == "openai":
                    response = self.llm.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temperature
                    )
                    return response.choices[0].message.content
                
                elif self.provider == "anthropic":
                    response = self.llm.messages.create(
                        model=self.model,
                        max_tokens=8000,
                        temperature=self.temperature,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text
                
                elif self.provider == "gemini":
                    response = self.llm.generate_content(
                        prompt,
                        generation_config={"temperature": self.temperature}
                    )
                    return response.text
                
                # 다른 프로바이더는 아직 구현되지 않음
                return self.llm.invoke(prompt)
            except Exception as e:
                print(f"[WARN] Plugin execution failed: {e}")
                # Fallback으로 진행

        # Fallback: v5.0 방식으로 codex exec 사용
        print(f"[WARN] Plugin LLM not implemented or failed, using codex fallback")
        try:
            result = subprocess.run(
                ["codex", "exec", prompt],
                capture_output=True,
                text=True,
                timeout=60,
                check=False
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                raise RuntimeError(f"Codex failed: {result.stderr}")
        except Exception as e:
            print(f"[WARN] Codex fallback failed: {e}")
            print(f"🔄 Falling back to Mock LLM")
            # Mock으로 Fallback (시스템 안정성을 위해)
            mock = MockLLMSource(role="backend") # Role은 추정
            return mock.invoke(prompt)

    def invoke_structured(self, prompt: str, schema: Optional[Dict] = None) -> Dict:
        """구조화된 출력"""
        if self.llm and hasattr(self.llm, 'invoke_structured'):
            return self.llm.invoke_structured(prompt, schema)

        # Fallback: JSON 요청 후 파싱
        response = self.invoke(prompt + "\n\nRespond in JSON format.")
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"response": response}



class MockLLMSource(LLMSource):
    """테스트용 Mock LLM"""

    def __init__(self, role: str):
        self.role = role

    def invoke(self, prompt: str, **kwargs) -> str:
        print(f"[MockLLM:{self.role}] Invoked with prompt length: {len(prompt)}")
        
        if self.role == "orchestrator":
            return """
Plan:
1. Backend: Create main.py and requirements.txt
2. Frontend: Create App.jsx and package.json
"""
        elif self.role == "backend":
            return """
FILE: main.py
```python
from fastapi import FastAPI
app = FastAPI()
@app.get("/")
def read_root():
    return {"Hello": "World"}
```

FILE: requirements.txt
```
fastapi
uvicorn
```
"""
        elif self.role == "frontend":
            return """
FILE: App.jsx
```javascript
import React from 'react';
function App() {
  return <h1>Hello World</h1>;
}
export default App;
```

FILE: package.json
```json
{
  "dependencies": {
    "react": "^18.2.0"
  }
}
```
"""
        return "Mock response"

    def invoke_structured(self, prompt: str, schema: Optional[Dict] = None) -> Dict:
        return {"response": self.invoke(prompt)}


class LLMSourceFactory:

    """역할별 LLM 소스 생성 팩토리"""

    @staticmethod
    def create_from_config(role_config: Dict, cli_type: str, timeout_sec: int = 60) -> LLMSource:
        """
        설정에서 LLM 소스 생성

        Args:
            role_config: 역할 설정 (orchestrator, backend, frontend)
                예: {"source": "cli_assistant", "temperature": 0.7}
                또는: {"source": "plugin", "plugin": {"provider": "groq", "model": "llama-3.3-70b"}}
            cli_type: CLI Assistant 타입 (codex, claude_code, etc)
            timeout_sec: 타임아웃 (초)

        Returns:
            LLMSource 인스턴스
        """
        source = role_config.get("source")
        temperature = role_config.get("temperature", 0.7)

        if source == "cli_assistant":
            # CLI Assistant의 내장 LLM 사용
            # Allow role-specific override for cli_type
            effective_cli_type = role_config.get("cli_type", cli_type)
            fallback = role_config.get("fallback")
            return CLIAssistantLLMSource(
                cli_type=effective_cli_type,
                temperature=temperature,
                timeout_sec=timeout_sec,
                fallback_config=fallback
            )

        elif source == "plugin":
            # 플러그인 LLM 사용
            plugin_config = role_config.get("plugin", {})
            return PluginLLMSource(
                provider=plugin_config.get("provider", "openai"),
                model=plugin_config.get("model", "gpt-5.1"),
                temperature=temperature,
                api_key=plugin_config.get("api_key")
            )

        elif source == "mock":
            # 테스트용 Mock
            return MockLLMSource(role=role_config.get("role", "unknown"))

        else:
            raise ValueError(f"Unknown LLM source: {source}. Must be 'cli_assistant' or 'plugin'")


# 사용 예시
if __name__ == "__main__":
    # 예시 1: CLI Assistant LLM (Codex)
    cli_llm = CLIAssistantLLMSource(cli_type="codex", temperature=0.3)
    print("CLI Assistant LLM created")

    # 예시 2: Plugin LLM (Groq)
    plugin_llm = PluginLLMSource(provider="groq", model="llama-3.3-70b-versatile", temperature=0.7)
    print("Plugin LLM created")

    # 예시 3: Factory 사용
    config = {
        "source": "cli_assistant",
        "temperature": 0.5,
        "fallback": {
            "provider": "claude",
            "model": "claude-sonnet-4.5"
        }
    }
    llm_source = LLMSourceFactory.create_from_config(config, cli_type="codex")
    print("LLM Source created from config:", type(llm_source))
