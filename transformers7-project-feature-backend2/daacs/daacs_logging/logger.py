"""
DAACS v6.0 - Logger
v5.0 로깅 구조를 v6.0로 확장 (하위 호환성 유지)
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from ..models.daacs_state import DAACSState


class DAACSLogger:
    """
    DAACS v6.0 Logger

    v5.0 필드를 모두 보존하면서 v6.0 확장 필드 추가
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.turns_file = os.path.join(log_dir, "turns.jsonl")
        self.workflow_file = os.path.join(log_dir, "workflow.jsonl")
        self.summary_file = os.path.join(log_dir, "summary.json")

    def log_turn(self, state: DAACSState, event: Optional[Dict[str, Any]] = None):
        """
        턴별 로그 (v5.0 호환)

        Args:
            state: 현재 DAACS 상태
            event: 이벤트 데이터 (옵션)
        """
        event = event or {}

        log_entry = {
            # ==================== v5.0 필드 (하위 호환성) ====================
            "turn": state.get("iteration_count", 0),
            "goal": state.get("current_goal", ""),
            "mode": state.get("mode", "test"),
            "scenario_id": state.get("session_id", ""),
            "scenario_type": event.get("type", "default"),
            "stop_reason": state.get("stop_reason", ""),
            "consecutive_failures": state.get("consecutive_failures", 0),
            "failure_type": state.get("failure_type"),
            "failure_summary": state.get("failure_summary", []),

            # ==================== v6.0 확장 필드 ====================
            "timestamp": datetime.now().isoformat(),
            "phase": state.get("current_phase", "unknown"),
            "parallel_execution": state.get("parallel_execution", False),

            # 역할별 LLM 소스
            "llm_sources": state.get("llm_sources", {}),
            "cli_assistant": state.get("cli_assistant", ""),

            # Backend 상태
            "backend_status": state.get("backend_status", "pending"),
            "backend_files": list(state.get("backend_files", {}).keys()),
            "backend_iterations": state.get("backend_subgraph_iterations", 0),

            # Frontend 상태
            "frontend_status": state.get("frontend_status", "pending"),
            "frontend_files": list(state.get("frontend_files", {}).keys()),
            "frontend_iterations": state.get("frontend_subgraph_iterations", 0),

            # Orchestrator 판단
            "orchestrator_judgment": state.get("orchestrator_judgment", ""),
            "compatibility_verified": state.get("compatibility_verified", False),
            "compatibility_issues": state.get("compatibility_issues", []),

            # 이벤트 데이터
            "event": event,
        }

        # JSONL 형식으로 추가 (v5.0과 동일)
        try:
            with open(self.turns_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARN] Failed to write turn log: {e}")

    def log_workflow_event(self, event_type: str, data: Dict[str, Any]):
        """
        워크플로우 이벤트 로그 (v6.0 신규)

        Args:
            event_type: 이벤트 타입 (node_start, node_end, edge_transition)
            data: 이벤트 데이터
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }

        try:
            with open(self.workflow_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARN] Failed to write workflow log: {e}")

    def log_summary(self, state: DAACSState):
        """
        최종 요약 로그

        Args:
            state: 최종 DAACS 상태
        """
        summary = {
            "session_id": state.get("session_id"),
            "goal": state.get("initial_goal"),
            "final_status": state.get("final_status", "unknown"),
            "stop_reason": state.get("stop_reason", ""),
            "total_iterations": state.get("iteration_count", 0),
            "consecutive_failures": state.get("consecutive_failures", 0),
            "mode": state.get("mode"),
            "parallel_execution": state.get("parallel_execution"),
            "cli_assistant": state.get("cli_assistant"),

            # 결과
            "backend": {
                "status": state.get("backend_status"),
                "files": list(state.get("backend_files", {}).keys()),
                "iterations": state.get("backend_subgraph_iterations", 0)
            },
            "frontend": {
                "status": state.get("frontend_status"),
                "files": list(state.get("frontend_files", {}).keys()),
                "iterations": state.get("frontend_subgraph_iterations", 0)
            },

            # 호환성
            "compatibility_verified": state.get("compatibility_verified", False),
            "compatibility_issues": state.get("compatibility_issues", []),

            # 타임스탬프
            "created_at": state.get("created_at"),
            "completed_at": datetime.now().isoformat(),
            "duration_seconds": state.get("total_duration_seconds", 0)
        }

        try:
            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to write summary log: {e}")

    def get_turns(self) -> list:
        """턴 로그 읽기"""
        turns = []
        try:
            if os.path.exists(self.turns_file):
                with open(self.turns_file, "r", encoding="utf-8") as f:
                    for line in f:
                        turns.append(json.loads(line))
        except Exception as e:
            print(f"[WARN] Failed to read turn logs: {e}")
        return turns

    def get_summary(self) -> Optional[Dict]:
        """요약 로그 읽기"""
        try:
            if os.path.exists(self.summary_file):
                with open(self.summary_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to read summary log: {e}")
        return None


# 사용 예시
if __name__ == "__main__":
    from ..models.daacs_state import create_initial_daacs_state

    print("=== DAACS Logger Test ===\n")

    # Logger 생성
    logger = DAACSLogger("logs")

    # 초기 상태
    config = {
        "cli_assistant": {"type": "codex"},
        "execution": {
            "mode": "test",
            "max_iterations": 10,
            "max_failures": 5,
            "parallel_execution": True
        }
    }
    state = create_initial_daacs_state("Create TODO app", config)

    # 턴 로그
    print("1. Logging turn:")
    logger.log_turn(state, {"type": "orchestrator_planning"})

    # 워크플로우 이벤트 로그
    print("2. Logging workflow event:")
    logger.log_workflow_event("node_start", {"node": "orchestrator_planning"})

    # 요약 로그
    print("3. Logging summary:")
    state["final_status"] = "success"
    state["stop_reason"] = "All tasks completed"
    logger.log_summary(state)

    # 로그 읽기
    print("\n4. Reading logs:")
    turns = logger.get_turns()
    print(f"   Turns logged: {len(turns)}")
    summary = logger.get_summary()
    print(f"   Summary status: {summary.get('final_status') if summary else 'N/A'}")

    print("\n[OK] Logger working correctly!")
