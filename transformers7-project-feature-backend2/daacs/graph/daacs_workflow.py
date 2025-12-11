"""
DAACS v6.0 - Main Workflow
LangGraph 기반 병렬 실행 워크플로우
"""

from langgraph.graph import StateGraph, END
from ..models.daacs_state import DAACSState
from .orchestrator_nodes import (
    orchestrator_planning_node,
    orchestrator_judgment_node,
    orchestrator_replanning_node,
    context_db_node,
    deliver_node
)
from .backend_subgraph import create_backend_subgraph
from .frontend_subgraph import create_frontend_subgraph


def create_daacs_workflow(config):
    """
    DAACS v6.0 메인 워크플로우 생성

    Workflow:
    1. Orchestrator Planning → Backend/Frontend 필요 여부 결정
    2. Parallel Execution → Backend SubGraph ⚡ Frontend SubGraph
    3. Orchestrator Judgment → 호환성 검증
    4. Replanning (필요 시) → 재계획 후 반복
    5. Context DB → 결과 저장
    6. Deliver → 최종 결과 전달

    Args:
        config: DAACSConfig 인스턴스

    Returns:
        Compiled StateGraph
    """

    workflow = StateGraph(DAACSState)

    # ==================== 노드 정의 ====================

    # 1. Orchestrator Planning
    orchestrator_llm = config.get_llm_source("orchestrator")

    def orchestrator_planning_wrapper(state: DAACSState):
        return orchestrator_planning_node(state, orchestrator_llm)

    workflow.add_node("orchestrator_planning", orchestrator_planning_wrapper)

    # 2. 병렬 실행 시작 (Dummy node)
    def start_parallel_node(state: DAACSState):
        print(f"[Workflow] Starting parallel execution...")
        return {"current_phase": "parallel_execution"}

    workflow.add_node("start_parallel", start_parallel_node)

    # 3. Backend SubGraph
    backend_graph = create_backend_subgraph(config)
    workflow.add_node("backend_subgraph", backend_graph)

    # 4. Frontend SubGraph
    frontend_graph = create_frontend_subgraph(config)
    workflow.add_node("frontend_subgraph", frontend_graph)

    # 5. Orchestrator Judgment
    def orchestrator_judgment_wrapper(state: DAACSState):
        return orchestrator_judgment_node(state, orchestrator_llm)

    workflow.add_node("orchestrator_judgment", orchestrator_judgment_wrapper)

    # 6. Orchestrator Replanning
    def orchestrator_replanning_wrapper(state: DAACSState):
        return orchestrator_replanning_node(state, orchestrator_llm)

    workflow.add_node("orchestrator_replanning", orchestrator_replanning_wrapper)

    # 7. Context DB & Deliver
    workflow.add_node("save_context", context_db_node)
    workflow.add_node("deliver", deliver_node)

    # ==================== 엣지 연결 ====================

    # Entry Point
    workflow.set_entry_point("orchestrator_planning")

    # Planning → Parallel or Deliver
    def decide_after_planning(state: DAACSState) -> str:
        """Backend/Frontend 필요 여부에 따라 분기"""
        needs_backend = state.get("needs_backend", False)
        needs_frontend = state.get("needs_frontend", False)

        if needs_backend or needs_frontend:
            return "parallel_execution"
        else:
            return "deliver"

    workflow.add_conditional_edges(
        "orchestrator_planning",
        decide_after_planning,
        {
            "parallel_execution": "start_parallel",
            "deliver": "deliver"
        }
    )

    # Parallel Execution → Backend & Frontend 병렬 실행
    if config.get_execution_config().get("parallel_execution", False):
        # 병렬 실행 모드
        workflow.add_edge("start_parallel", "backend_subgraph")
        workflow.add_edge("start_parallel", "frontend_subgraph")
    else:
        # 순차 실행 모드 (v5.0 호환)
        workflow.add_edge("start_parallel", "backend_subgraph")
        workflow.add_edge("backend_subgraph", "frontend_subgraph")

    # SubGraphs → Judgment
    workflow.add_edge("backend_subgraph", "orchestrator_judgment")
    workflow.add_edge("frontend_subgraph", "orchestrator_judgment")

    # Judgment → Replan or Save
    def decide_after_judgment(state: DAACSState) -> str:
        """재작업 필요 여부 및 iteration 상한 확인"""
        needs_rework = state.get("needs_rework", False)
        consecutive_failures = state.get("consecutive_failures", 0)
        max_failures = state.get("max_failures", 5)
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 10)

        # 1. Iteration 상한 도달
        if iteration_count >= max_iterations:
            print(f"[Workflow] Max iterations ({max_iterations}) reached - forcing completion")
            return "save_context"

        # 2. 연속 실패 상한 도달
        if consecutive_failures >= max_failures:
            print(f"[Workflow] Max failures ({max_failures}) reached - forcing completion")
            return "save_context"

        # 3. 재작업 필요
        if needs_rework:
            return "replan"

        # 4. 정상 완료
        return "save_context"

    workflow.add_conditional_edges(
        "orchestrator_judgment",
        decide_after_judgment,
        {
            "replan": "orchestrator_replanning",
            "save_context": "save_context"
        }
    )

    # Replanning → Planning (재계획 후 다시 시작)
    def decide_after_replanning(state: DAACSState) -> str:
        """재계획 후 계속할지 중단할지 결정"""
        stop_reason = state.get("stop_reason", "")

        if stop_reason:
            print(f"[Workflow] Stopping: {stop_reason}")
            return "save_context"

        # Iteration count 증가
        print(f"[Workflow] Replanning complete - restarting cycle")
        return "orchestrator_planning"

    workflow.add_conditional_edges(
        "orchestrator_replanning",
        decide_after_replanning,
        {
            "orchestrator_planning": "orchestrator_planning",
            "save_context": "save_context"
        }
    )

    # Save Context → Deliver
    workflow.add_edge("save_context", "deliver")

    # Deliver → END
    workflow.add_edge("deliver", END)

    return workflow


def get_compiled_daacs_workflow(config):
    """
    컴파일된 DAACS 워크플로우 반환

    Args:
        config: DAACSConfig 인스턴스

    Returns:
        Compiled workflow
    """
    workflow = create_daacs_workflow(config)
    return workflow.compile()


# 사용 예시
if __name__ == "__main__":
    from ..config_loader import DAACSConfig

    print("=== DAACS Workflow Test ===\n")

    # Config 로드
    try:
        config = DAACSConfig("daacs_config.yaml")
    except Exception as e:
        print(f"Config load failed, using v5.0 compat mode: {e}")
        config = DAACSConfig()

    # Workflow 생성
    workflow = create_daacs_workflow(config)
    compiled_workflow = workflow.compile()

    print("[OK] Workflow compiled successfully!")
    print(f"Execution Mode: {'Parallel' if config.get_execution_config().get('parallel_execution') else 'Sequential'}")
    print(f"Max Iterations: {config.get_execution_config().get('max_iterations', 10)}")
    print(f"Max Failures: {config.get_execution_config().get('max_failures', 5)}")
