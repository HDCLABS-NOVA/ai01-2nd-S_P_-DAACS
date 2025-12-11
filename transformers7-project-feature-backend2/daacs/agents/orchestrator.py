import os
import json
import subprocess
from typing import Any, Dict, List, Optional
from daacs.core.utils import setup_logger
from daacs.core.config import PLANNER_MODEL, SUPPORTED_MODELS

logger = setup_logger("OrchestratorAgent")


class OrchestratorAgent:
    """
    Former Planner renamed to OrchestratorAgent.
    Handles planning, sanitizing actions, verification, and replanning.
    """

    def __init__(self, model_name: str = None, mode: str = None):
        self.model_name = model_name or PLANNER_MODEL
        self.model_config = SUPPORTED_MODELS.get(self.model_name, SUPPORTED_MODELS.get("gpt-5.1-codex-max"))
        logger.info(f"OrchestratorAgent initialized with model: {self.model_name}")
        self.mode = (mode or os.getenv("DAACS_MODE", "test")).lower()
        self.constraints_enabled = self.mode == "test"

        self.use_llm = os.getenv("DAACS_PLANNER_USE_LLM", "true").lower() == "true"
        self.llm_timeout = int(os.getenv("DAACS_PLANNER_TIMEOUT_SEC", "60"))

        self.state = {
            "current_index": 0,
            "total_actions": 0
        }
        self.feedback: List[Dict[str, Any]] = []
        self.failed_streak = 0
        # 액션 타입별 기본 검증 템플릿
        self.verify_templates = {
            "shell": ["files_exist:files.txt", "files_not_empty:files.txt", "files_no_hidden:files.txt", "files_match_listing:files.txt"],
            "edit": ["files_exist:files.txt"],
            "test": ["tests_pass", "tests_no_error"],
            "codegen": ["tests_pass", "tests_no_error", "lint_pass"],
            "refactor": ["tests_pass", "tests_no_error", "lint_pass"],
            "build": ["build_success"],
            "deploy": ["build_success"]
        }

    def _format_prompt(self, goal: str) -> str:
        """LLM에게 JSON 액션을 요청하는 프롬프트 템플릿."""
        schema_hint = {
            "goal": goal,
            "actions": [
                {
                    "action": "dev_instruction",
                    "type": "shell",
                    "instruction": "natural language instruction for Codex CLI",
                    "verify": ["files_exist:files.txt"],
                    "comment": "why this step",
                    "targets": ["files.txt"],
                    "client": "frontend"
                }
            ],
            "next_goal": "optional next target or empty"
        }
        constraints_prompt = ""
        if self.constraints_enabled:
            constraints_prompt = (
                "DAACS TEST MODE is active. Apply mandatory constraints:\n"
                "- At most ONE file per turn.\n"
                "- Do NOT generate HTML/CSS/JS or other web assets.\n"
                "- Prefer CLI-based Python; keep outputs concise (<=200 lines).\n"
                "- If generating tests, create ONLY ONE dummy test (tests/test_basic.py).\n"
                "- For files.txt updates, use: find . -maxdepth 1 -mindepth 1 -not -name 'files.txt' -not -path './.*' -printf '%f\\n' | sort > files.txt\n"
            )
        else:
            constraints_prompt = (
                "DAACS PROD MODE is active. Constraints disabled; full codegen allowed. "
                "Still keep responses valid JSON only."
            )

        return (
            "You are the Orchestrator. Output ONLY JSON in the exact schema below. "
            "No markdown, no code fences. If you cannot follow, output nothing.\n"
            f"{constraints_prompt}\n"
            f"{json.dumps(schema_hint, ensure_ascii=False)}"
        )

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Codex CLI를 사용해 계획을 생성 (JSON 예상). 실패 시 None."""
        if not self.use_llm:
            return None

        cmd = [
            "codex",
            "exec",
            "-c",
            'sandbox_permissions=["disk-full-access"]',
            prompt
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.llm_timeout,
                check=False
            )
            if result.returncode != 0:
                logger.error(f"OrchestratorAgent LLM call failed: {result.stderr}")
                return None
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"OrchestratorAgent LLM call timed out after {self.llm_timeout}s")
        except Exception as e:
            logger.error(f"OrchestratorAgent LLM call exception: {e}")
        return None

    def _sanitize_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """액션 목록을 후처리하여 위험/비일관 지시를 교정."""
        sanitized = []
        for action in actions:
            a = dict(action)
            instr = a.get("instruction", "") or ""
            # ls -a, -la 등을 non-hidden으로 교체
            instr = instr.replace("ls -la", "ls -1").replace("ls -al", "ls -1").replace("ls -a", "ls -1")
            if "ls -A" in instr:
                instr = instr.replace("ls -A", "ls -1")
            # files.txt 목록 생성은 디렉터리 포함 안전 명령으로 강제
            if "files.txt" in instr and ("list" in instr.lower() or "ls" in instr.lower() or "rg --files" in instr.lower()):
                instr = (
                    "find . -maxdepth 1 -mindepth 1 -not -name 'files.txt' -not -path './.*' "
                    "-printf '%f\\n' | sort > files.txt"
                )
            if "files.txt" in instr and "exclude files.txt" not in instr.lower():
                instr = instr + " Exclude files.txt from the output."
            if "sort" not in instr.lower():
                instr = instr + " Sort names one per line."
            a["instruction"] = instr
            # 액션 타입 기본값
            if "type" not in a:
                a["type"] = "shell"
            # 클라이언트 기본값
            if "client" not in a:
                a["client"] = "frontend"
            # 기본 검증 템플릿 적용
            verify = list(a.get("verify") or [])
            if a["type"] == "shell" and "files.txt" not in instr:
                template = []
            else:
                template = self.verify_templates.get(a["type"], [])
            for v in template:
                if v not in verify:
                    verify.append(v)
            # files.txt 관련 검증이 없다면 추가
            if "files.txt" in instr and not any(v.startswith("files_exist:files.txt") for v in verify):
                verify.append("files_exist:files.txt")
            if "files.txt" in instr and not any(v.startswith("files_not_empty:files.txt") for v in verify):
                verify.append("files_not_empty:files.txt")
            if "files.txt" in instr and not any(v.startswith("files_no_hidden:files.txt") for v in verify):
                verify.append("files_no_hidden:files.txt")
            if "files.txt" in instr and not any(v.startswith("files_match_listing:files.txt") for v in verify):
                verify.append("files_match_listing:files.txt")
            a["verify"] = verify
            sanitized.append(a)
        return sanitized

    def _parse_llm_response(self, text: str) -> Optional[Dict[str, Any]]:
        """LLM 응답에서 JSON을 추출/파싱."""
        # 코드블록 제거
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`").strip()
        # 중괄호 기준으로 JSON 추출
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start:end+1]
            try:
                return json.loads(candidate)
            except Exception:
                pass
        # 완전히 실패 시 None
        return None

    def _fallback_actions(self, goal: str) -> List[Dict[str, Any]]:
        """LLM 미사용 시 기본 액션 생성."""
        goal_lower = goal.lower()
        if "files.txt" in goal_lower or "파일 목록" in goal_lower:
            return [
                {
                    "action": "dev_instruction",
                    "type": "shell",
                    "instruction": (
                        "List all non-hidden files and directories (exclude dotfiles) in the current folder and save them to files.txt. "
                        "Use `find . -maxdepth 1 -mindepth 1 -not -name \"files.txt\" -not -path \"./.*\" -printf '%f\\n' | sort > files.txt`. "
                        "Do NOT use ls -a. Exclude files.txt from the output. Sort the names one per line. If files.txt exists, overwrite it."
                    ),
                    "verify": [
                        "files_exist:files.txt",
                        "files_not_empty:files.txt",
                        "files_no_hidden:files.txt",
                        "files_match_listing:files.txt"
                    ],
                    "comment": "Create a file list",
                    "targets": ["files.txt"],
                    "client": "frontend"
                }
            ]
        # 기본 패스스루
        return [
            {
                "action": "dev_instruction",
                "type": "shell",
                "instruction": f"Please implement the following: {goal}",
                "verify": [],
                "comment": "pass-through instruction",
                "targets": [],
                "client": "frontend"
            }
        ]

    def _verify(self, action: Dict[str, Any], result: str) -> Dict[str, Any]:
        """간단한 검증 로직 (Cycle 3 확장 전)."""
        verdicts = []
        verify_items = action.get("verify", []) or []
        result_lower = result.lower()

        def add(verdict: bool, reason: str):
            verdicts.append({"ok": verdict, "reason": reason})

        # 결과에 Error/Exception 포함 시 즉시 실패
        if "Error" in result or "Exception" in result:
            add(False, "result contains error")
            return {"success": False, "verdicts": verdicts}

        # 테스트/린트/빌드 검증 (액션 타입과 무관하게 요청된 항목을 평가)
        if "tests_pass" in verify_items:
            ok = "fail" not in result_lower and "error" not in result_lower
            add(ok, "tests_pass")
        if "tests_no_error" in verify_items:
            ok = "error" not in result_lower
            add(ok, "tests_no_error")
        if "lint_pass" in verify_items:
            ok = "lint" in result_lower and ("pass" in result_lower or "no issues" in result_lower)
            add(ok, "lint_pass")
        if "build_success" in verify_items:
            ok = "build failed" not in result_lower and "error" not in result_lower
            add(ok, "build_success")

        for item in verify_items:
            if item.startswith("files_exist:"):
                path = item.split(":", 1)[1]
                exists = os.path.exists(path)
                add(exists, f"files_exist:{path}")
            elif item.startswith("files_not_empty:"):
                path = item.split(":", 1)[1]
                try:
                    nonempty = os.path.exists(path) and os.path.getsize(path) > 0
                except Exception:
                    nonempty = False
                add(nonempty, f"files_not_empty:{path}")
            elif item.startswith("files_no_hidden:"):
                path = item.split(":", 1)[1]
                ok = True
                try:
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                name = line.strip()
                                if name.startswith("."):
                                    ok = False
                                    break
                    else:
                        ok = False
                except Exception:
                    ok = False
                add(ok, f"files_no_hidden:{path}")
            elif item.startswith("files_match_listing:"):
                path = item.split(":", 1)[1]
                try:
                    if not os.path.exists(path):
                        add(False, f"files_match_listing:{path} (missing)")
                        continue
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = [line.strip() for line in f if line.strip()]
                    expected = sorted([p for p in os.listdir(".") if not p.startswith(".") and p != path])
                    content_filtered = sorted([p for p in content if p != path])
                    ok = content_filtered == expected
                    add(ok, f"files_match_listing:{path} (self-excluded)")
                except Exception:
                    add(False, f"files_match_listing:{path} (exception)")
            else:
                add(True, f"unknown verifier ignored: {item}")

        success = all(v["ok"] for v in verdicts) if verdicts else True
        return {"success": success, "verdicts": verdicts}

    def add_feedback(self, action: Dict[str, Any], result: str, review: Dict[str, Any]) -> None:
        """Codex 실행 결과를 Planner 피드백으로 적재."""
        self.feedback.append({
            "action": action,
            "result": result,
            "review": review
        })

    def create_plan(self, goal: str) -> dict:
        """목표를 받아 실행 계획을 수립합니다."""
        logger.info(f"Planning for goal: {goal}")

        actions = self._fallback_actions(goal)

        llm_prompt = self._format_prompt(goal)
        llm_raw = self._call_llm(llm_prompt) if self.use_llm else None
        if llm_raw:
            parsed = self._parse_llm_response(llm_raw)
            if parsed and isinstance(parsed.get("actions"), list) and parsed["actions"]:
                actions = parsed["actions"]
                logger.info(f"LLM-produced actions accepted: {len(actions)}")
            else:
                logger.warning("LLM response parsed but no valid actions; using fallback.")

        actions = self._sanitize_actions(actions)

        plan = {
            "goal": goal,
            "actions": actions,
            "current_index": 0,
            "next_goal": "",
            "mode": self.mode,
            "constraints_enabled": self.constraints_enabled
        }

        self.state["total_actions"] = len(plan["actions"])
        return plan

    def get_next_instruction(self, plan: dict) -> Optional[Dict[str, Any]]:
        """계획에서 다음 실행할 액션을 가져옵니다."""
        current = plan.get("current_index", 0)
        actions = plan.get("actions", [])
        if current < len(actions):
            action = actions[current]
            plan["current_index"] = current + 1
            self.state["current_index"] = plan["current_index"]
            return action
        return None

    def review_result(self, action: Dict[str, Any], result: str) -> dict:
        """Codex의 실행 결과를 리뷰합니다."""
        logger.info("Reviewing result...")

        verify_outcome = self._verify(action, result)
        success = verify_outcome["success"]
        if success:
            self.failed_streak = 0
        else:
            self.failed_streak += 1

        return {
            "success": success,
            "needs_retry": not success,
            "is_complete": self.state.get("current_index", 0) >= self.state.get("total_actions", 0),
            "verify": verify_outcome
        }

    def plan_next(self, goal: str) -> Optional[Dict[str, Any]]:
        """
        실패 피드백을 기반으로 재계획.
        - 연속 실패 3회 초과 시 중단.
        - 권한 문제(rollout recorder/permission) 시 즉시 중단 요청.
        - 타입/검증 실패에 따라 보강된 next_actions를 제안하고 기존 goal을 유지.
        """
        if self.failed_streak >= 3:
            return {"stop": True, "reason": "failed_streak_exceeded", "next_goal": goal, "next_actions": []}
        if not self.feedback:
            return {"stop": False, "next_goal": goal, "next_actions": []}

        last = self.feedback[-1]
        action = last.get("action", {}) or {}
        review = last.get("review", {}) or {}
        result_text = (last.get("result") or "")
        result_lower = result_text.lower()
        verify = review.get("verify", {}) if isinstance(review, dict) else {}
        verdicts = verify.get("verdicts") or []

        failed_reasons = [v.get("reason", "") for v in verdicts if not v.get("ok")]
        files_fail = any(r.startswith("files_") for r in failed_reasons)
        tests_fail = any("tests" in r for r in failed_reasons) or "assert" in result_lower
        lint_fail = any("lint" in r for r in failed_reasons)
        build_fail = any("build" in r for r in failed_reasons) or "build failed" in result_lower
        permission_error = "rollout recorder" in result_lower or "operation not permitted" in result_lower
        timeout_error = "timeout" in result_lower or "timed out" in result_lower

        if permission_error:
            return {"stop": True, "reason": "permission_denied_rollout", "next_goal": goal, "next_actions": []}

        next_actions: List[Dict[str, Any]] = []
        next_goal = goal

        def add_action(action_type: str, instruction: str, comment: str = "", verify: Optional[List[str]] = None, targets: Optional[List[str]] = None, client: str = "frontend"):
            next_actions.append({
                "action": "dev_instruction",
                "type": action_type,
                "instruction": instruction,
                "verify": verify if verify is not None else self.verify_templates.get(action_type, []),
                "comment": comment,
                "targets": targets or [],
                "client": client
            })

        if action.get("type") == "shell" and files_fail:
            add_action(
                "shell",
                "List both files and directories (non-hidden) at repo root using `find . -maxdepth 1 -mindepth 1 -not -name \"files.txt\" -not -path \"./.*\" -printf '%f\\n' | sort > files.txt`.",
                "Use find to include directories and avoid repeated listing failures",
                ["files_exist:files.txt", "files_not_empty:files.txt", "files_no_hidden:files.txt", "files_match_listing:files.txt"],
                ["files.txt"]
            )

        if tests_fail:
            add_action(
                "test",
                "Rerun tests with verbose output, capture failing cases, fix blocking issues, and rerun tests until they pass.",
                "Retry tests after addressing failures",
                self.verify_templates.get("test", []),
                client="backend"
            )

        if lint_fail:
            add_action(
                "refactor",
                "Run lint (e.g., ruff/flake8/pylint), fix reported issues, and rerun lint to ensure a clean result.",
                "Resolve lint blockers",
                self.verify_templates.get("refactor", []),
                client="backend"
            )

        if build_fail or action.get("type") == "build":
            add_action(
                "build",
                "Inspect build logs, fix errors, and rerun the same build command to confirm success.",
                "Retry build after fixing errors",
                self.verify_templates.get("build", []),
                client="backend"
            )

        if action.get("type") in ["codegen", "refactor"] and not tests_fail and not lint_fail:
            add_action(
                "test",
                "Run the project's tests to validate the generated changes; fix any failing cases and rerun.",
                "Validate generated code with tests",
                self.verify_templates.get("test", []),
                client="backend"
            )

        if action.get("type") == "deploy":
            add_action(
                "build",
                "Ensure the build succeeds before deploy; rerun the build command and fix any errors.",
                "Prepare for deploy",
                self.verify_templates.get("build", []),
                client="backend"
            )
            add_action(
                "deploy",
                "Retry deploy after build success; capture deploy logs and ensure no permission issues.",
                "Retry deploy after build",
                self.verify_templates.get("deploy", []),
                client="backend"
            )

        # codegen/large 작업 타임아웃 시, 더 작은 단계로 쪼개어 재시도
        if timeout_error and action.get("type") in ["codegen", "refactor", "build", "deploy"]:
            add_action(
                "shell",
                "Create project skeleton folders: mkdir -p project && cd project && mkdir -p todo_app tests && touch todo_app/__init__.py tests/__init__.py",
                "Ensure directories exist for skeleton",
                [],
                client="frontend"
            )
            add_action(
                "codegen",
                "Create todo_app/main.py with a minimal in-memory ToDoStore (add/list/complete/delete placeholders) and a simple CLI entry guarded by __name__ == '__main__'. Keep it concise.",
                "Minimal app entrypoint",
                [],
                client="frontend"
            )
            add_action(
                "codegen",
                "Create tests/test_basic.py with a minimal test for ToDoStore add/list behaviors using pytest; keep it short.",
                "Add a basic test to validate codegen",
                self.verify_templates.get("test", []),
                client="backend"
            )
            add_action(
                "test",
                "Run pytest -q to validate the skeleton and capture failures; fix blocking issues if any.",
                "Validate skeleton with tests",
                self.verify_templates.get("test", []),
                client="backend"
            )

        if not next_actions:
            return {"stop": False, "next_goal": next_goal, "next_actions": []}

        return {"stop": False, "next_goal": next_goal, "next_actions": self._sanitize_actions(next_actions)}
