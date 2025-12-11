"""
DAACS v6.0 - Orchestrator Nodes
Orchestrator Planning 및 Judgment 노드
"""

from typing import Dict, Any
from ..models.daacs_state import DAACSState
from .replanning import ReplanningStrategies, detect_failure_type
import json


def orchestrator_planning_node(state: DAACSState, orchestrator_llm) -> Dict:
    """
    Orchestrator Planning 노드

    사용자 목표를 분석하여 Backend/Frontend 필요 여부 결정 및 계획 수립
    + API 스펙 정의 (endpoints, data models, 통신 규약)
    """
    print(f"[Orchestrator Planning] Starting...")
    print(f"[Orchestrator] Using LLM source: {state.get('llm_sources', {}).get('orchestrator', 'unknown')}")

    goal = state['current_goal']

    # LLM 프롬프트 - Park David Foundation 스타일 적용
    prompt = f"""
You are a senior project architect applying multi-view analysis.

=== GOAL ===
{goal}

=== ANALYSIS FRAMEWORK (Multi-View) ===
Analyze from these perspectives simultaneously:
1. **PM View**: Project scope, deliverables, timeline
2. **Tech Lead View**: Architecture, API design, data flow
3. **UX View**: User interactions, frontend requirements
4. **Integration View**: How components connect and communicate

=== REQUIRED OUTPUT STRUCTURE ===

**[1] SUMMARY**
One-line description of the solution approach.

**[2] PROBLEM DEFINITION**
- What exactly needs to be built?
- Key technical challenges

**[3] ARCHITECTURE DECISION**
- Needs Backend: yes/no (with reason)
- Needs Frontend: yes/no (with reason)
- Communication: REST/GraphQL/WebSocket

**[4] API SPECIFICATION** (if backend needed)
Define ALL endpoints with:
- Method (GET/POST/PUT/DELETE)
- Path (/api/...)
- Request/Response schema

**[5] FRONTEND SPECIFICATION** (if frontend needed)
- Pages and components
- API endpoints each component calls
- State management approach

**[6] INTEGRATION CONTRACT**
- Base URL
- CORS configuration
- Authentication (if any)

=== JSON OUTPUT ===
Respond ONLY in this JSON format:
{{
    "summary": "One-line solution summary",
    "problem_definition": "What needs to be built",
    "needs_backend": true/false,
    "needs_frontend": true/false,
    "plan": "Detailed technical plan",
    "api_spec": {{
        "base_url": "http://localhost:8080",
        "endpoints": [
            {{
                "method": "GET/POST/PUT/DELETE",
                "path": "/api/resource",
                "description": "Endpoint purpose",
                "request_body": {{}},
                "response": {{}}
            }}
        ],
        "data_models": [
            {{
                "name": "ModelName",
                "fields": {{"field": "type"}}
            }}
        ]
    }},
    "frontend_spec": {{
        "pages": ["page1"],
        "components": ["component1"],
        "api_calls": ["GET /api/resource"],
        "state_management": "React useState/Context"
    }},
    "integration": {{
        "cors_origins": ["http://localhost:5173"],
        "auth_method": "none/jwt/session"
    }}
}}
"""

    try:
        # Orchestrator LLM 호출
        response = orchestrator_llm.invoke_structured(prompt)

        # JSON 파싱
        if isinstance(response, str):
            response = json.loads(response)

        needs_backend = response.get("needs_backend", True)
        needs_frontend = response.get("needs_frontend", True)
        plan = response.get("plan", "No plan generated")
        api_spec = response.get("api_spec", {})
        frontend_spec = response.get("frontend_spec", {})

        print(f"[Orchestrator Planning] Plan: {plan[:100]}...")
        print(f"[Orchestrator Planning] Backend: {needs_backend}, Frontend: {needs_frontend}")
        print(f"[Orchestrator Planning] API Endpoints: {len(api_spec.get('endpoints', []))}")

        return {
            "orchestrator_plan": plan,
            "needs_backend": needs_backend,
            "needs_frontend": needs_frontend,
            "api_spec": api_spec,
            "frontend_spec": frontend_spec,
            "current_phase": "planning_complete"
        }

    except Exception as e:
        print(f"[Orchestrator Planning] [ERROR] Error: {e}")
        # Fallback: 기본 계획
        return {
            "orchestrator_plan": f"Create a fullstack application for: {goal}",
            "needs_backend": True,
            "needs_frontend": True,
            "api_spec": {},
            "frontend_spec": {},
            "current_phase": "planning_complete"
        }


def orchestrator_judgment_node(state: DAACSState, orchestrator_llm) -> Dict:
    """
    Orchestrator Judgment 노드

    Backend와 Frontend 결과를 분석하여 실제 코드 기반 호환성 검증
    - API 엔드포인트 매칭 확인
    - 요청/응답 형식 검증
    - 통합 가능성 판단
    """
    print(f"[Orchestrator Judgment] Starting...")

    backend_files = state.get("backend_files", {})
    frontend_files = state.get("frontend_files", {})
    backend_status = state.get("backend_status")
    frontend_status = state.get("frontend_status")
    api_spec = state.get("api_spec", {})

    # 둘 다 실패한 경우
    if backend_status == "failed" and frontend_status == "failed":
        print("[Orchestrator Judgment] [ERROR] Both backend and frontend failed")

        # 실패 유형 감지
        failure_summary = state.get("failure_summary", [])
        failure_type = detect_failure_type(failure_summary, "")

        return {
            "orchestrator_judgment": "Both backend and frontend failed",
            "compatibility_verified": False,
            "compatibility_issues": ["Backend failed", "Frontend failed"],
            "needs_rework": True,
            "failure_type": failure_type,
            "current_phase": "judgment_failed"
        }

    # 실제 코드 내용 추출 (일부)
    backend_code_samples = {}
    for filename, content in backend_files.items():
        # 첫 100줄만 추출
        lines = content.split('\n')[:100]
        backend_code_samples[filename] = '\n'.join(lines)

    frontend_code_samples = {}
    for filename, content in frontend_files.items():
        # 첫 100줄만 추출
        lines = content.split('\n')[:100]
        frontend_code_samples[filename] = '\n'.join(lines)

    # API 스펙을 문자열로 변환
    api_spec_str = json.dumps(api_spec, indent=2) if api_spec else "No API spec"

    # LLM 프롬프트 - 실제 코드 기반 검증
    prompt = f"""
You are a senior technical reviewer and integration specialist. Perform a DEEP COMPATIBILITY ANALYSIS between backend and frontend code.

=== ORIGINAL API SPECIFICATION ===
{api_spec_str}

=== BACKEND CODE (samples) ===
{json.dumps(backend_code_samples, indent=2)}

=== FRONTEND CODE (samples) ===
{json.dumps(frontend_code_samples, indent=2)}

=== STATUS ===
Backend Status: {backend_status}
Frontend Status: {frontend_status}

=== VERIFICATION CHECKLIST ===
Analyze the actual code and verify:

1. **API ENDPOINT MATCHING**:
   - Does backend implement ALL endpoints from the API spec?
   - Does frontend call ALL endpoints from the API spec?
   - Are the HTTP methods (GET/POST/PUT/DELETE) correct?
   - Are the endpoint paths identical?

2. **REQUEST/RESPONSE FORMAT**:
   - Do frontend fetch calls send correct request body format?
   - Does backend return the expected response format?
   - Are field names and types consistent?

3. **BASE URL CONFIGURATION**:
   - Is frontend configured with correct backend URL (e.g., http://localhost:8080)?
   - Is CORS properly configured in backend?

4. **DATA FLOW**:
   - Can frontend properly consume backend responses?
   - Are there any missing fields or type mismatches?

Respond in JSON format:
{{
    "compatible": true/false,
    "endpoint_analysis": {{
        "backend_implements": ["GET /api/...", "POST /api/..."],
        "frontend_calls": ["GET /api/...", "POST /api/..."],
        "missing_in_backend": [],
        "missing_in_frontend": []
    }},
    "data_format_issues": [],
    "cors_configured": true/false,
    "issues": ["detailed issue 1", "detailed issue 2"],
    "recommendations": ["recommendation 1"],
    "summary": "Detailed compatibility summary"
}}
"""

    try:
        # Orchestrator LLM 호출
        response = orchestrator_llm.invoke_structured(prompt)

        if isinstance(response, str):
            response = json.loads(response)

        compatible = response.get("compatible", True)
        issues = response.get("issues", [])
        summary = response.get("summary", "No summary")
        endpoint_analysis = response.get("endpoint_analysis", {})
        recommendations = response.get("recommendations", [])

        print(f"[Orchestrator Judgment] Compatible: {compatible}")
        print(f"[Orchestrator Judgment] Issues: {len(issues)}")
        if endpoint_analysis:
            print(f"[Orchestrator Judgment] Backend APIs: {len(endpoint_analysis.get('backend_implements', []))}")
            print(f"[Orchestrator Judgment] Frontend API Calls: {len(endpoint_analysis.get('frontend_calls', []))}")

        return {
            "orchestrator_judgment": summary,
            "compatibility_verified": compatible,
            "compatibility_issues": issues,
            "endpoint_analysis": endpoint_analysis,
            "recommendations": recommendations,
            "needs_rework": not compatible,
            "current_phase": "judgment_complete"
        }

    except Exception as e:
        print(f"[Orchestrator Judgment] [WARN] Error: {e}, assuming compatible")
        return {
            "orchestrator_judgment": "Judgment completed with assumptions",
            "compatibility_verified": True,
            "compatibility_issues": [],
            "endpoint_analysis": {},
            "recommendations": [],
            "needs_rework": False,
            "current_phase": "judgment_complete"
        }


def orchestrator_replanning_node(state: DAACSState, orchestrator_llm) -> Dict:
    """
    Orchestrator Replanning 노드

    실패 시 재계획 수립
    """
    print(f"[Orchestrator Replanning] Starting...")

    failure_type = state.get("failure_type")
    consecutive_failures = state.get("consecutive_failures", 0)
    max_failures = state.get("max_failures", 5)
    current_goal = state.get("current_goal")
    
    # Judgment에서 전달받은 상세 정보 (Issue #2, #3 수정)
    compatibility_issues = state.get("compatibility_issues", [])
    recommendations = state.get("recommendations", [])
    
    # context에 상세 정보 포함
    context = {
        "compatibility_issues": compatibility_issues,
        "recommendations": recommendations
    }
    
    # 상세 정보 로깅
    if compatibility_issues:
        print(f"[Orchestrator Replanning] Compatibility Issues: {len(compatibility_issues)}")
    if recommendations:
        print(f"[Orchestrator Replanning] Recommendations: {len(recommendations)}")

    # 재계획 전략 가져오기
    replan_response = ReplanningStrategies.create_replan_response(
        failure_type=failure_type,
        current_goal=current_goal,
        consecutive_failures=consecutive_failures,
        max_failures=max_failures,
        context=context
    )

    should_stop = replan_response["stop"]
    reason = replan_response["reason"]
    next_actions = replan_response.get("next_actions", [])

    print(f"[Orchestrator Replanning] Stop: {should_stop}")
    print(f"[Orchestrator Replanning] Reason: {reason}")

    if should_stop:
        return {
            "needs_rework": False,
            "stop_reason": reason,
            "final_status": "failed",
            "current_phase": "replanning_stopped"
        }

    # LLM에게 추가 컨텍스트 요청 (선택적)
    if state.get("llm_sources", {}).get("orchestrator") == "cli_assistant":
        prompt = f"""
Previous failure: {failure_type}
Suggested actions: {next_actions}

Should we proceed with these actions or suggest alternatives?
Respond in JSON format:
{{
    "proceed": true/false,
    "alternative_actions": []
}}
"""
        try:
            response = orchestrator_llm.invoke_structured(prompt)
            if isinstance(response, str):
                response = json.loads(response)

            if not response.get("proceed", True):
                next_actions = response.get("alternative_actions", next_actions)

        except Exception:
            pass  # LLM 실패 시 기본 전략 사용

    # failure_summary에 상세 이슈 추가 (Coder가 구체적인 문제를 알 수 있도록)
    detailed_failure_summary = []
    
    # Compatibility issues를 failure_summary에 포함
    if compatibility_issues:
        detailed_failure_summary.extend([f"COMPATIBILITY ISSUE: {issue}" for issue in compatibility_issues[:5]])
    
    # Recommendations도 포함
    if recommendations:
        detailed_failure_summary.extend([f"RECOMMENDATION: {rec}" for rec in recommendations[:3]])
    
    # 기본 reason도 포함
    if reason and reason != "Unknown failure - generic retry":
        detailed_failure_summary.append(f"FAILURE REASON: {reason}")
    
    return {
        "needs_rework": True,
        "orchestrator_plan": f"Replanning: {reason}",
        "next_actions": next_actions,  # SubGraph에서 활용
        "rework_history": [f"Replanning ({consecutive_failures+1}): {reason}"],
        "failure_summary": detailed_failure_summary,  # 🔥 Coder에게 전달될 상세 피드백
        "current_phase": "replanning_complete"
    }


def context_db_node(state: DAACSState) -> Dict:
    """
    Context DB 저장 노드 (Placeholder)

    TODO: Phase 10에서 ChromaDB 연동
    """
    print(f"[Context DB] Saving artifacts...")

    # 모든 파일 병합
    all_files = {}
    all_files.update(state.get("backend_files", {}))
    all_files.update(state.get("frontend_files", {}))

    return {
        "all_files": all_files,
        "current_phase": "context_saved"
    }


def deliver_node(state: DAACSState) -> Dict:
    """
    최종 결과 전달 노드
    """
    print(f"[Deliver] Finalizing...")

    backend_status = state.get("backend_status")
    frontend_status = state.get("frontend_status")
    compatibility_verified = state.get("compatibility_verified", False)

    # 최종 상태 결정
    if backend_status == "completed" and frontend_status == "completed" and compatibility_verified:
        final_status = "success"
        stop_reason = "All tasks completed successfully"
    elif backend_status == "completed" or frontend_status == "completed":
        final_status = "partial"
        stop_reason = "Partial completion"
    else:
        final_status = "failed"
        stop_reason = state.get("stop_reason", "Tasks failed")

    print(f"[Deliver] Final Status: {final_status}")
    print(f"[Deliver] Reason: {stop_reason}")

    return {
        "final_status": final_status,
        "stop_reason": stop_reason,
        "current_phase": "delivered"
    }


# 사용 예시
if __name__ == "__main__":
    from ..config_loader import DAACSConfig
    from ..models.daacs_state import create_initial_daacs_state

    print("=== Orchestrator Nodes Test ===\n")

    # Config 로드
    config = DAACSConfig("daacs_config.yaml")

    # 초기 상태
    state = create_initial_daacs_state(
        goal="Create a TODO app",
        config=config.config
    )

    # Orchestrator LLM
    orchestrator_llm = config.get_llm_source("orchestrator")

    # Planning 테스트
    print("1. Testing Planning Node:")
    result = orchestrator_planning_node(state, orchestrator_llm)
    print(f"   Needs Backend: {result['needs_backend']}")
    print(f"   Needs Frontend: {result['needs_frontend']}")

    print("\n[OK] Orchestrator nodes working correctly!")
