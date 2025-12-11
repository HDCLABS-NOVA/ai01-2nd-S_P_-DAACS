"""
DAACS v6.0 - LangGraph State Definition
Type-safe state management with Annotated reducers for parallel execution
"""

from typing import TypedDict, List, Dict, Literal, Optional, Annotated, Any
from datetime import datetime
import uuid


# ==================== Reducer Functions ====================

def pick_first(current: Any, new: Any) -> Any:
    """새 값이 None이 아니면 사용, 아니면 현재 값 유지"""
    return new if new is not None else current


def merge_dicts(current: Optional[Dict], new: Optional[Dict]) -> Dict:
    """딕셔너리 병합 (병렬 업데이트 안전)"""
    result = (current or {}).copy()
    result.update(new or {})
    return result


def append_lists(current: Optional[List], new: Optional[List]) -> List:
    """리스트 연결 (병렬 업데이트 안전)"""
    return (current or []) + (new or [])


# ==================== State Definition ====================

class DAACSState(TypedDict):
    """
    DAACS v6.0 상태 (LangGraph 기반)

    모든 필드는 Annotated reducer를 사용하여 병렬 실행 시
    상태 충돌을 방지합니다.
    """

    # ==================== 프로젝트 정보 ====================
    session_id: Annotated[str, pick_first]
    initial_goal: Annotated[str, pick_first]
    current_goal: Annotated[str, pick_first]
    project_dir: Annotated[str, pick_first]  # Output directory for the project

    # ==================== 역할별 LLM 소스 ====================
    llm_sources: Annotated[Dict[str, str], merge_dicts]  # role -> source type

    # ==================== 실행 모드 ====================
    mode: Annotated[Literal["test", "prod"], pick_first]
    parallel_execution: Annotated[bool, pick_first]

    # ==================== CLI 어시스턴트 ====================
    cli_assistant: Annotated[str, pick_first]
    cli_assistant_available: Annotated[bool, pick_first]

    # ==================== 순환 제어 ====================
    iteration_count: Annotated[int, pick_first]
    max_iterations: Annotated[int, pick_first]
    max_subgraph_iterations: Annotated[int, pick_first]  # Issue #5: config에서 읽음
    consecutive_failures: Annotated[int, pick_first]
    max_failures: Annotated[int, pick_first]

    # ==================== Orchestrator 계획 ====================
    orchestrator_plan: Annotated[str, pick_first]
    needs_backend: Annotated[bool, pick_first]
    needs_frontend: Annotated[bool, pick_first]
    api_spec: Annotated[Dict[str, Any], merge_dicts]  # Issue #8: API 스펙
    frontend_spec: Annotated[Dict[str, Any], merge_dicts]  # Issue #8: Frontend 스펙

    # ==================== Backend SubGraph ====================
    backend_files: Annotated[Dict[str, str], merge_dicts]  # filename -> content
    backend_status: Annotated[Literal["pending", "working", "completed", "failed"], pick_first]
    backend_needs_rework: Annotated[bool, pick_first]
    backend_subgraph_iterations: Annotated[int, pick_first]
    backend_logs: Annotated[List[str], append_lists]
    backend_action_type: Annotated[Optional[str], pick_first]  # files, test, lint, build, etc
    backend_test_result: Annotated[str, pick_first]

    # ==================== Frontend SubGraph ====================
    frontend_files: Annotated[Dict[str, str], merge_dicts]
    frontend_status: Annotated[Literal["pending", "working", "completed", "failed"], pick_first]
    frontend_needs_rework: Annotated[bool, pick_first]
    frontend_subgraph_iterations: Annotated[int, pick_first]
    frontend_logs: Annotated[List[str], append_lists]
    frontend_action_type: Annotated[Optional[str], pick_first]
    frontend_test_result: Annotated[str, pick_first]

    # ==================== Orchestrator 결과 판단 ====================
    orchestrator_judgment: Annotated[str, pick_first]
    compatibility_verified: Annotated[bool, pick_first]
    compatibility_issues: Annotated[List[str], append_lists]
    endpoint_analysis: Annotated[Dict[str, Any], merge_dicts]  # Issue #9: 엔드포인트 분석
    recommendations: Annotated[List[str], append_lists]  # Issue #3: 추천 사항
    needs_rework: Annotated[bool, pick_first]
    next_actions: Annotated[List[Dict], append_lists]  # Issue #4: Replanning actions

    # ==================== 실패 추적 ====================
    failure_type: Annotated[Optional[str], pick_first]  # permission, tests_fail, lint_fail, etc
    failure_summary: Annotated[List[str], append_lists]

    # ==================== 로그 및 히스토리 ====================
    turn_history: Annotated[List[Dict], append_lists]
    rework_history: Annotated[List[str], append_lists]

    # ==================== 최종 결과 ====================
    final_status: Annotated[Literal["success", "partial", "failed"], pick_first]
    stop_reason: Annotated[str, pick_first]
    all_files: Annotated[Dict[str, str], merge_dicts]

    # ==================== 워크플로우 추적 ====================
    current_phase: Annotated[str, pick_first]
    completed_phases: Annotated[List[str], append_lists]

    # ==================== 메타데이터 ====================
    created_at: Annotated[str, pick_first]
    updated_at: Annotated[str, pick_first]
    total_duration_seconds: Annotated[float, pick_first]


def create_initial_daacs_state(
    goal: str,
    config: Dict,
    session_id: Optional[str] = None
) -> DAACSState:
    """
    초기 DAACS 상태 생성

    Args:
        goal: 사용자 목표
        config: DAACSConfig에서 가져온 실행 설정
        session_id: 세션 ID (옵션, 없으면 자동 생성)

    Returns:
        초기화된 DAACSState
    """

    now = datetime.now().isoformat()
    session_id = session_id or f"daacs-{uuid.uuid4().hex[:8]}"
    
    # Create a unique project directory based on session_id
    # Format: project/project_{session_id}
    project_dir = f"project/project_{session_id.replace('daacs-', '')}"

    exec_config = config.get("execution", {})

    return DAACSState(
        # 프로젝트 정보
        session_id=session_id,
        initial_goal=goal,
        current_goal=goal,
        project_dir=project_dir,

        # LLM 소스 (역할별 source type)
        llm_sources={},

        # 실행 모드
        mode=exec_config.get("mode", "test"),
        parallel_execution=exec_config.get("parallel_execution", False),

        # CLI 어시스턴트
        cli_assistant=config.get("cli_assistant", {}).get("type", "codex"),
        cli_assistant_available=True,

        # 순환 제어
        iteration_count=0,
        max_iterations=exec_config.get("max_iterations", 10),
        max_subgraph_iterations=exec_config.get("max_subgraph_iterations", 2),  # Issue #5
        consecutive_failures=0,
        max_failures=exec_config.get("max_failures", 5),

        # Orchestrator
        orchestrator_plan="",
        needs_backend=False,
        needs_frontend=False,
        api_spec={},  # Issue #8
        frontend_spec={},  # Issue #8

        # Backend
        backend_files={},
        backend_status="pending",
        backend_needs_rework=False,
        backend_subgraph_iterations=0,
        backend_logs=[],
        backend_action_type=None,
        backend_test_result="",

        # Frontend
        frontend_files={},
        frontend_status="pending",
        frontend_needs_rework=False,
        frontend_subgraph_iterations=0,
        frontend_logs=[],
        frontend_action_type=None,
        frontend_test_result="",

        # Orchestrator 판단
        orchestrator_judgment="",
        compatibility_verified=False,
        compatibility_issues=[],
        endpoint_analysis={},  # Issue #9
        recommendations=[],  # Issue #3
        needs_rework=False,
        next_actions=[],  # Issue #4

        # 실패 추적
        failure_type=None,
        failure_summary=[],

        # 로그 및 히스토리
        turn_history=[],
        rework_history=[],

        # 최종 결과
        final_status="success",
        stop_reason="",
        all_files={},

        # 워크플로우 추적
        current_phase="initialization",
        completed_phases=[],

        # 메타데이터
        created_at=now,
        updated_at=now,
        total_duration_seconds=0.0,
    )


# 사용 예시
if __name__ == "__main__":
    print("=== DAACS State Test ===\n")

    # 초기 상태 생성
    config = {
        "cli_assistant": {"type": "codex"},
        "execution": {
            "mode": "test",
            "max_iterations": 10,
            "max_failures": 5,
            "parallel_execution": True
        }
    }

    state = create_initial_daacs_state("Create a TODO app", config)

    print(f"Session ID: {state['session_id']}")
    print(f"Goal: {state['initial_goal']}")
    print(f"Mode: {state['mode']}")
    print(f"Parallel: {state['parallel_execution']}")
    print(f"Max Iterations: {state['max_iterations']}")
    print(f"CLI Assistant: {state['cli_assistant']}")

    # 상태 업데이트 테스트 (병렬 안전)
    print("\n=== State Update Test ===")

    # Backend 파일 추가 (merge_dicts)
    backend_update = {"backend_files": {"main.py": "content1"}}
    state["backend_files"] = merge_dicts(state["backend_files"], backend_update["backend_files"])
    print(f"Backend Files: {list(state['backend_files'].keys())}")

    # 로그 추가 (append_lists)
    backend_log_update = {"backend_logs": ["Backend coder completed"]}
    state["backend_logs"] = append_lists(state["backend_logs"], backend_log_update["backend_logs"])
    print(f"Backend Logs: {state['backend_logs']}")

    print("\n[OK] State management working correctly!")
