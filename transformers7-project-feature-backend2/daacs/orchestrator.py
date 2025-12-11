import sys
import os
import time
import json
from .utils import setup_logger
from .llm.cli_executor import FrontendClient, BackendClient
from .orchestrator_agent import OrchestratorAgent
from .config import MAX_TURNS

logger = setup_logger("Orchestrator")

class DAACSOrchestrator:
    def __init__(self, planner_model: str = None, log_dir: str = "logs", max_failures: int = 5):
        # 모드: test(제약/짧은 타임아웃) | prod(제약 해제/긴 타임아웃)
        self.mode = os.getenv("DAACS_MODE", "test").lower()
        self.constraints_enabled = self.mode == "test"
        codex_timeout = 180 if self.constraints_enabled else 240

        self.clients = {
            "frontend": FrontendClient(timeout_sec=codex_timeout),
            "backend": BackendClient(timeout_sec=codex_timeout),
        }
        self.agent = OrchestratorAgent(model_name=planner_model, mode=self.mode)
        self.history = []
        self.log_dir = log_dir
        self.max_failures = max_failures
        logger.info(f"Orchestrator initialized with agent: {self.agent.model_name}, mode={self.mode}, constraints={self.constraints_enabled}")

    def run(self, initial_goal: str, scenario_id: str = None, scenario_type: str = "default"):
        logger.info("Starting DAACS Loop...")
        logger.info(f"Initial Goal: {initial_goal}")
        scenario_id = scenario_id or str(int(time.time()))
        # 1. 환경 점검
        # assume frontend existence for version check
        version = self.clients["frontend"].check_version()
        logger.info(f"Codex Version: {version}")
        if "Codex CLI not found" in version:
            logger.error("Critical: Codex CLI is not installed or not in PATH.")
            return

        current_goal = initial_goal
        turn = 0
        consecutive_failures = 0
        stop_reason = ""
        last_failed_verdicts = []
        failure_type = ""
        failure_summary = []

        # 2. Plan (Agent) - 한 번만 계획 수립
        plan = self.agent.create_plan(current_goal)
        actions = plan.get("actions", [])
        logger.info(f"Plan created with {len(actions)} actions")

        while turn < MAX_TURNS:
            turn += 1
            logger.info(f"--- Turn {turn} ---")

            # 3. Get next action
            action = self.agent.get_next_instruction(plan)
            if not action:
                logger.info("No more actions to execute.")
                break

            instruction = action.get("instruction") or action.get("cmd") or ""
            logger.info(f"Executing action: {instruction}")

            # 4. Execute (Codex)
            # Choose client (default client1)
            client_name = action.get("client") or "frontend"
            client = self.clients.get(client_name, self.clients["frontend"])
            result = client.execute(instruction)
            logger.info(f"Codex Result: {result}")

            # 5. Verify & Decide Next Step
            review = self.agent.review_result(action, result)
            failed_verdicts = [v for v in review.get("verify", {}).get("verdicts", []) if not v.get("ok")]
            self.history.append({
                "turn": turn,
                "goal": current_goal,
                "mode": self.mode,
                "constraints_enabled": self.constraints_enabled,
                "scenario_id": scenario_id,
                "scenario_type": scenario_type,
                "stop_reason": stop_reason,
                "consecutive_failures": consecutive_failures,
                "last_failed_verdicts": last_failed_verdicts,
                "failure_type": failure_type,
                "failure_summary": failure_summary,
                "current_goal": current_goal,
                "action": action,
                "result": result,
                "review": review
            })
            self.agent.add_feedback(action, result, review)

            if review["success"]:
                logger.info("Action successful.")
                consecutive_failures = 0
                if review["is_complete"]:
                    logger.info("All actions completed! Goal achieved.")
                    break
            else:
                logger.warning("Action failed.")
                consecutive_failures += 1
                last_failed_verdicts = failed_verdicts
                failure_type = "permission" if "rollout recorder" in result or "Operation not permitted" in result else "verify"
                reasons = [v.get("reason", "") for v in failed_verdicts]
                failure_summary = reasons
                if any("tests" in r for r in reasons):
                    failure_type = "tests_fail"
                elif any("build" in r for r in reasons):
                    failure_type = "build_fail"
                elif any("lint" in r for r in reasons):
                    failure_type = "lint_fail"
                elif failure_type != "permission":
                    failure_type = "verify_fail"
                if consecutive_failures >= self.max_failures:
                    stop_reason = "orchestrator_consecutive_failures"
                    logger.warning("Stopping due to orchestrator consecutive failures threshold.")
                    break
                if "rollout recorder" in result or "Operation not permitted" in result:
                    logger.error("Codex failed due to rollout recorder permission. Run with full access (danger-full-access).")
                # 재계획 확인
                next_plan = self.agent.plan_next(current_goal)
                if next_plan and next_plan.get("stop"):
                    stop_reason = next_plan.get("reason", "")
                    logger.warning(f"Stopping due to planner signal: {stop_reason}")
                    break

                if next_plan and next_plan.get("next_goal") and not next_plan.get("next_actions"):
                    current_goal = next_plan["next_goal"]
                    plan = self.agent.create_plan(current_goal)
                    actions = plan.get("actions", [])
                    self.history.append({
                        "turn": turn,
                        "goal": current_goal,
                        "mode": self.mode,
                        "constraints_enabled": self.constraints_enabled,
                        "scenario_id": scenario_id,
                        "scenario_type": scenario_type,
                        "stop_reason": stop_reason,
                        "consecutive_failures": consecutive_failures,
                        "last_failed_verdicts": last_failed_verdicts,
                        "failure_type": failure_type,
                        "failure_summary": failure_summary,
                        "current_goal": current_goal,
                        "action": {"action": "replan", "type": "system"},
                        "result": "Planner requested new goal; replanning",
                        "review": {"success": False, "needs_retry": True, "is_complete": False}
                    })
                    logger.info(f"Planner suggested new goal; replanning. current_goal={current_goal}, actions={len(actions)}")
                    consecutive_failures = 0
                    continue

                if next_plan and next_plan.get("next_actions"):
                    # next_actions를 병합: 새로운 액션을 앞에 붙이고 나머지 이어감
                    remaining = plan["actions"][plan.get("current_index", 0):]
                    plan["actions"] = next_plan["next_actions"] + remaining
                    plan["current_index"] = 0
                    self.agent.state["current_index"] = 0
                    if next_plan.get("next_goal"):
                        current_goal = next_plan["next_goal"]
                    logger.info(f"Planner suggested new actions; updating plan. current_goal={current_goal}")
                    continue

                if review["needs_retry"]:
                    logger.info("Will retry this action with backoff...")
                    plan["current_index"] = max(plan.get("current_index", 1) - 1, 0)
                    self.agent.state["current_index"] = plan["current_index"]
                    time.sleep(min(2 ** (turn - 1), 5))
                    continue
                
        logger.info("DAACS Loop Finished.")

        # 로그 파일로 저장
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            log_path = os.path.join(self.log_dir, "turns.jsonl")
            with open(log_path, "a", encoding="utf-8") as f:
                for entry in self.history:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.info(f"History appended to {log_path}")
        except Exception as e:
            logger.error(f"Failed to write history log: {e}")

if __name__ == "__main__":
    # 모델 선택 (환경 변수 또는 커맨드라인)
    planner_model = os.getenv("DAACS_PLANNER_MODEL")
    orchestrator = DAACSOrchestrator(planner_model=planner_model)
    
    if len(sys.argv) > 1:
        # 커맨드라인 인자가 있으면 바로 실행
        goal = sys.argv[1]
        orchestrator.run(goal)
    else:
        # 인자가 없으면 사용자 입력을 받음
        print("DAACS (Planner + Codex) Automation System")
        print(f"Planner Model: {orchestrator.planner.model_name}")
        print("----------------------------------------")
        while True:
            try:
                goal = input("\n명령을 입력하세요 (종료하려면 'exit' 또는 Ctrl+C): ").strip()
                if not goal:
                    continue
                if goal.lower() in ['exit', 'quit']:
                    print("종료합니다.")
                    break
                
                orchestrator.run(goal)
            except KeyboardInterrupt:
                print("\n종료합니다.")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
