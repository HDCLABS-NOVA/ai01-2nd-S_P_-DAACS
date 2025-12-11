import os
import subprocess
import time
import json
from typing import Optional
from daacs.core.utils import setup_logger
from daacs.core.config import PLANNER_MODEL, SUPPORTED_MODELS

logger = setup_logger("CodexClient")

class GeminiRateLimiter:
    """Gemini 무료 티어 (분당 2회) 제한을 위한 Rate Limiter"""
    _last_request_time = 0
    _min_interval = 30.0  # 30초 대기 (여유 있게 설정)

    @classmethod
    def wait_for_slot(cls):
        current_time = time.time()
        elapsed = current_time - cls._last_request_time
        if elapsed < cls._min_interval:
            wait_time = cls._min_interval - elapsed
            logger.info(f"[GeminiRateLimiter] Waiting {wait_time:.1f}s for next slot...")
            time.sleep(wait_time)
        cls._last_request_time = time.time()


class CodexClient:
    def __init__(self, cwd: str = ".", timeout_sec: int = 240, retries: int = 2, sandbox_permissions=None, client_name: str = "frontend", model_name: Optional[str] = None, cli_type: str = "codex"):
        env_cwd = os.getenv("DAACS_WORKDIR")
        # 기본 작업 경로를 project/로 설정해 산출물이 루트에 흩어지지 않도록 함
        default_cwd = "project" if os.path.exists("project") else "."
        self.cwd = env_cwd or cwd or default_cwd
        if self.cwd and not os.path.exists(self.cwd):
            os.makedirs(self.cwd, exist_ok=True)
        self.process: Optional[subprocess.Popen] = None
        self.timeout_sec = timeout_sec
        self.retries = retries
        self.client_name = client_name
        self.cli_type = cli_type
        env_model = os.getenv(f"DAACS_{client_name.upper()}_MODEL")
        self.model_name = model_name or env_model or PLANNER_MODEL
        self.model_config = SUPPORTED_MODELS.get(self.model_name, SUPPORTED_MODELS.get("gpt-5.1-codex-max"))
        # 기본적으로 Codex가 rollout recorder를 홈 경로에 쓰려 하므로, 권한 오류 방지를 위해 풀 액세스 부여
        self.sandbox_permissions = sandbox_permissions or ['disk-full-access']

    def execute(self, prompt: str) -> str:
        """CLI를 비대화형 모드(exec)로 실행하여 결과를 받아옵니다."""
        logger.info(f"[{self.client_name}] Executing {self.cli_type} with prompt length: {len(prompt)}")

        # Gemini Rate Limiting
        if self.cli_type == "gemini":
            GeminiRateLimiter.wait_for_slot()

        cmd = []
        shell_mode = False
        input_str = None
        
        if self.cli_type == "claude_code":
            # Claude CLI: Agentic mode - let Claude create files directly in cwd
            # Remove --print to enable file creation
            cmd = ["claude.cmd", "--dangerously-skip-permissions"] if os.name == 'nt' else ["claude", "--dangerously-skip-permissions"]
            input_str = prompt
            shell_mode = True
        elif self.cli_type == "gemini":
            # Gemini CLI: Agentic mode - let Gemini create files directly in cwd
            # Remove -o text to enable file creation
            # Use -s to skip confirmation prompts
            gemini_cmd = "gemini.cmd" if os.name == 'nt' else "gemini"
            cmd = [gemini_cmd, "-s"]
            input_str = prompt
            shell_mode = True
        else:
            # Codex CLI (Default)
            # Use npx to run codex on Windows (npm global scripts have path issues)
            # Pass prompt via stdin to avoid command line length limits
            permissions_toml = f'sandbox_permissions={json.dumps(self.sandbox_permissions)}'
            if os.name == 'nt':
                # Windows: use npx to run @openai/codex
                cmd = ["npx", "@openai/codex", "exec", "--sandbox", "danger-full-access", "-c", permissions_toml]
            else:
                cmd = ["codex", "exec", "--sandbox", "danger-full-access", "-c", permissions_toml]
            input_str = prompt  # Pass prompt via stdin
            shell_mode = True

        for attempt in range(1, self.retries + 2):  # initial try + retries
            try:
                result = subprocess.run(
                    cmd,
                    input=input_str,
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                    check=False,
                    shell=shell_mode,
                    encoding='utf-8',
                    errors='ignore'
                )

                if result.returncode != 0:
                    logger.error(f"[{self.client_name}] {self.cli_type} execution failed (attempt {attempt}): {result.stderr}")
                    # Fallback: try 'claude' if 'claude.cmd' failed
                    if self.cli_type == "claude_code" and cmd[0] == "claude.cmd" and attempt == 1:
                         cmd[0] = "claude"
                         logger.info(f"[{self.client_name}] Retrying with 'claude'...")
                         continue
                    
                    # Fallback: try 'gemini' if 'gemini.cmd' failed
                    if self.cli_type == "gemini" and cmd[0] == "gemini.cmd" and attempt == 1:
                         cmd[0] = "gemini"
                         logger.info(f"[{self.client_name}] Retrying with 'gemini'...")
                         continue

                    if attempt <= self.retries:
                        time.sleep(1)
                        continue
                    return f"Error: {result.stderr}"

                logger.info(f"[{self.client_name}] {self.cli_type} execution successful")
                if not result.stdout:
                     logger.warning(f"[{self.client_name}] {self.cli_type} returned empty output. Stderr: {result.stderr}")
                
                output = result.stdout.strip() if result.stdout else ""
                
                # Gemini Output Cleaning
                if self.cli_type == "gemini":
                    # Remove "Loaded cached credentials." and other noise
                    lines = output.splitlines()
                    cleaned_lines = [l for l in lines if not l.startswith("Loaded cached credentials") and not l.startswith("Using project")]
                    output = "\n".join(cleaned_lines).strip()

                return output

            except subprocess.TimeoutExpired:
                logger.error(f"[{self.client_name}] {self.cli_type} execution timeout after {self.timeout_sec}s (attempt {attempt})")
                if attempt <= self.retries:
                    time.sleep(1)
                    continue
                return f"Error: Timeout after {self.timeout_sec}s"
            except Exception as e:
                logger.error(f"[{self.client_name}] Exception during {self.cli_type} execution (attempt {attempt}): {e}")
                if attempt <= self.retries:
                    time.sleep(1)
                    continue
                return f"Exception: {str(e)}"

    def check_version(self) -> str:
        try:
            if self.cli_type == "claude_code":
                cmd = ["claude.cmd", "--version"] if os.name == 'nt' else ["claude", "--version"]
            elif self.cli_type == "gemini":
                cmd = ["gemini.cmd", "--version"] if os.name == 'nt' else ["gemini", "--version"]
            else:
                cmd = ["codex", "--version"]
            
            shell_mode = (self.cli_type in ["claude_code", "gemini"])
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                shell=shell_mode,
                encoding='utf-8',
                errors='ignore'
            )
            return result.stdout.strip()
        except Exception:
            return f"{self.cli_type} CLI not found"


class FrontendClient(CodexClient):
    def __init__(self, **kwargs):
        super().__init__(client_name="frontend", **kwargs)


class BackendClient(CodexClient):
    def __init__(self, **kwargs):
        super().__init__(client_name="backend", **kwargs)
