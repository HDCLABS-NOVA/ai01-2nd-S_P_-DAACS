"""
DAACS v6.0 - Frontend SubGraph
Frontend: Coder → Verifier → Router
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from ..models.daacs_state import DAACSState
from ..llm.cli_executor import CodexClient
from .verification import run_verification
from .backend_subgraph import parse_files_from_response  # 파일 파싱 함수 재사용


def _get_frontend_model_instructions(llm_type: str) -> str:
    """
    Frontend용 모델별 특수 지시사항 반환 (에이전틱 모드용)
    """
    # Claude 전용 지시사항 (에이전틱 모드)
    if 'claude' in llm_type.lower():
        return """
=== 🚀 AGENTIC MODE (CLAUDE) ===
✅ You have FULL file creation permissions.
✅ CREATE all files in the WORKING DIRECTORY (cwd).
✅ You decide the best file structure for this project.
⚠️ Do NOT ask for confirmation - just create the files.
⚠️ Do NOT create .md files (README, docs, etc.) - code only!
⚠️ If creating vite.config.js, set server.open to false.
"""
    
    # Gemini 전용 지시사항 (에이전틱 모드)
    elif 'gemini' in llm_type.lower():
        return """
=== 🚀 AGENTIC MODE (GEMINI) ===
✅ You have file creation permissions.
✅ CREATE all files in the WORKING DIRECTORY (cwd).
✅ You decide the best file structure for this project.
⚠️ Generate COMPLETE files, not snippets.
"""
    
    # Codex 전용 지시사항 (에이전틱 모드)
    elif 'codex' in llm_type.lower():
        return """
=== 🚀 AGENTIC MODE (CODEX) ===
✅ Create all files in the WORKING DIRECTORY (cwd).
✅ Use your file creation tools.
✅ You decide the best file structure for this project.
"""
    
    # 기본
    else:
        return """
=== FILE CREATION ===
Create all files in the WORKING DIRECTORY (cwd).
"""


def frontend_coder_node(state: DAACSState, frontend_llm, cli_client: CodexClient) -> Dict:
    """
    Frontend 코드 생성 노드

    Args:
        state: 현재 상태
        frontend_llm: Frontend 역할의 LLM Source
        cli_client: CLI Assistant 클라이언트

    Returns:
        상태 업데이트
    """
    print(f"[Frontend Coder] Starting... (iteration {state['frontend_subgraph_iterations']})")
    
    # LLM 타입 확인
    llm_type = state.get('llm_sources', {}).get('frontend', 'unknown')
    print(f"[Frontend Coder] Using LLM source: {llm_type}")

    goal = state['current_goal']
    orchestrator_plan = state.get('orchestrator_plan', '')
    backend_files = list(state.get('backend_files', {}).keys())
    api_spec = state.get('api_spec', {})
    frontend_spec = state.get('frontend_spec', {})
    
    # 이전 실패 사유 (재작업 시 피드백 루프)
    failure_summary = state.get('failure_summary', [])
    failure_context = ""
    if failure_summary:
        failure_reasons = "\n".join(f"- {reason}" for reason in failure_summary)
        failure_context = f"""
=== ⚠️ PREVIOUS FAILURE REASONS (FIX THESE!) ===
The previous code generation failed verification. You MUST fix these issues:
{failure_reasons}

Please carefully address each issue above in your new code.
"""

    # API 스펙을 문자열로 변환
    import json
    import os
    import glob
    api_spec_str = json.dumps(api_spec, indent=2) if api_spec else "No API spec provided"
    frontend_spec_str = json.dumps(frontend_spec, indent=2) if frontend_spec else "No frontend spec provided"

    # 프론트엔드 디렉토리 설정 및 생성 (프롬프트에 포함시키기 위해 먼저 생성)
    project_dir = state.get("project_dir", "output")
    frontend_dir = os.path.abspath(f"{project_dir}/frontend")
    os.makedirs(frontend_dir, exist_ok=True)

    # 모델별 특수 지시사항
    model_specific_instructions = _get_frontend_model_instructions(llm_type)

    # LLM 프롬프트 - 절대 경로 포함
    prompt = f"""
You are a senior frontend developer with UX-first mindset.

=== GOAL ===
{goal}
{failure_context}
=== ORCHESTRATOR PLAN ===
{orchestrator_plan}

{model_specific_instructions}

=== BACKEND FILES ===
{backend_files}

=== API SPECIFICATION (MUST CALL THESE) ===
{api_spec_str}

=== FRONTEND SPECIFICATION ===
{frontend_spec_str}

=== UX PRINCIPLES ===
1. **User-First**: Intuitive and responsive UI
2. **Loading States**: Show spinners/skeletons during API calls
3. **Error Handling**: Display user-friendly error messages
4. **Feedback**: Confirm actions with visual feedback

=== STRICT ROLE SEPARATION ===
⚠️ IMPORTANT: You are the FRONTEND developer ONLY.
- Generate ONLY frontend files (React, CSS, HTML, JS)
- Do NOT generate any backend files (Python, requirements.txt, etc.)
- Backend is handled by a separate developer

=== 🚨 FILE CREATION PATH (CRITICAL!) 🚨 ===
**CREATE ALL FILES IN THIS EXACT DIRECTORY:**
{frontend_dir}

Example:
- {frontend_dir}/package.json
- {frontend_dir}/vite.config.js
- {frontend_dir}/index.html
- {frontend_dir}/src/main.jsx
- {frontend_dir}/src/App.jsx

⚠️ DO NOT create files anywhere else!
⚠️ DO NOT create files in the current directory or root!

=== CODING RULES (Strict) ===
1. **React 18 + Vite 4**: Target stable versions
   - Use React 18.2.x (NOT experimental features)
   - Use Vite 4.x (NOT 5.x breaking changes)
2. **Clarity**: Clean, readable component code
3. **Simplicity**: Minimal dependencies, no over-engineering
4. **Consistency**: Uniform styling and naming
5. **Complete**: Generate ALL FRONTEND files for runnable project
6. **CSS**: Always include App.css and index.css files
7. **NO MARKDOWN FILES**: Do NOT create .md files (README, docs, etc.) - code only!
8. **ENGLISH ONLY**: Write ALL code, comments, and string literals in English only. Do NOT use Korean or any other non-ASCII characters.

=== IMPLEMENTATION CHECKLIST ===
□ All pages from frontend_spec
□ All components from frontend_spec  
□ API calls to ALL endpoints
□ Proper BASE_URL config (http://localhost:8080)
□ Loading & error states
□ index.html, main.jsx, App.jsx, vite.config.js, package.json

Generate a complete Vite + React project in {frontend_dir}.
"""

    try:
        # CLI 클라이언트의 cwd를 프론트엔드 디렉토리로 설정
        cli_client.cwd = frontend_dir
        
        # Frontend LLM 호출 (에이전틱 모드 - 파일 직접 생성)
        response = frontend_llm.invoke(prompt)

        # 에이전틱 모드: 파일시스템에서 생성된 파일 스캔
        # node_modules, .git 등 제외
        EXCLUDE_DIRS = {'node_modules', '.git', '__pycache__', 'dist', 'build', '.next'}
        files = {}
        for ext in ['*.jsx', '*.js', '*.css', '*.html', '*.json', '*.ts', '*.tsx']:
            for filepath in glob.glob(os.path.join(frontend_dir, '**', ext), recursive=True):
                # 제외 폴더 안에 있는 파일 스킵
                path_parts = filepath.replace('\\', '/').split('/')
                if any(excluded in path_parts for excluded in EXCLUDE_DIRS):
                    continue
                relpath = os.path.relpath(filepath, frontend_dir)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    files[relpath] = f.read()

        if not files:
            # 폴백: 응답에서 파싱 시도 (텍스트 모드용)
            files = parse_files_from_response(response)
            if files:
                for filename, content in files.items():
                    filepath = os.path.join(frontend_dir, filename)
                    file_dir = os.path.dirname(filepath)
                    if file_dir:
                        os.makedirs(file_dir, exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"[Frontend Coder] Wrote {filename} to {frontend_dir}/")

        if not files:
            print("[Frontend Coder] [WARN] No files generated from LLM")
            return {
                "frontend_files": {},
                "frontend_status": "failed",
                "frontend_logs": ["Frontend coder failed: No files generated"],
                "frontend_action_type": "codegen",
                "frontend_subgraph_iterations": state.get("frontend_subgraph_iterations", 0) + 1
            }

        print(f"[Frontend Coder] Generated {len(files)} files: {list(files.keys())}")

        return {
            "frontend_files": files,
            "frontend_status": "working",
            "frontend_logs": [f"Frontend coder generated: {list(files.keys())}"],
            "frontend_action_type": "files",
            "frontend_subgraph_iterations": state.get("frontend_subgraph_iterations", 0) + 1
        }

    except Exception as e:
        print(f"[Frontend Coder] [ERROR] Error: {e}")
        return {
            "frontend_files": {},
            "frontend_status": "failed",
            "frontend_logs": [f"Frontend coder error: {str(e)}"],
            "frontend_action_type": "codegen",
            "frontend_subgraph_iterations": state.get("frontend_subgraph_iterations", 0) + 1
        }


def frontend_verifier_node(state: DAACSState) -> Dict:
    """
    Frontend 검증 노드

    v6.0 개선: JavaScript 구문 검사
    """
    print(f"[Frontend Verifier] Starting...")

    # 'frontend' 타입으로 변경 → JavaScript 구문 검사
    action_type = "frontend"
    
    project_dir = state.get("project_dir", "output")
    frontend_dir = f"{project_dir}/frontend"
    
    # 파일 경로 수정: project_dir/frontend/ 접두사 추가
    filenames = list(state.get("frontend_files", {}).keys())
    files = [f"{frontend_dir}/{f}" for f in filenames]

    if not files:
        print("[Frontend Verifier] [WARN] No files to verify")
        return {
            "frontend_needs_rework": True,
            "frontend_status": "failed",
            "frontend_logs": ["Frontend verifier: No files to verify"],
            "frontend_verification_details": []
        }

    # 검증 실행 (JavaScript 구문 검사)
    verification_result = run_verification(
        action_type=action_type,
        files=files,
        test_result=state.get("frontend_test_result"),
    )

    all_passed = verification_result["ok"]
    summary = verification_result["summary"]
    verdicts = verification_result["verdicts"]

    print(f"[Frontend Verifier] Result: {'[PASS]' if all_passed else '[FAIL]'}")
    print(f"[Frontend Verifier] Summary: {summary}")
    
    # 개별 검증 결과 출력
    for v in verdicts:
        status = "✅" if v["ok"] else "❌"
        print(f"  {status} {v['template']}: {v['reason'][:80]}")

    # 검증 실패 시 실패 정보 수집
    failure_summary = []
    if not all_passed:
        failure_summary = [v["reason"] for v in verdicts if not v["ok"]]

    return {
        "frontend_needs_rework": not all_passed,
        "frontend_status": "completed" if all_passed else "failed",
        "frontend_logs": [f"Frontend verifier: {summary}"],
        "frontend_verification_details": verdicts,
        "failure_summary": failure_summary if not all_passed else []
    }


def frontend_router(state: DAACSState) -> str:
    """
    Frontend Router: 재작업 또는 완료 결정
    """
    max_subgraph_iterations = state.get("max_subgraph_iterations", 2)  # Issue #5: config에서 읽음
    current_iterations = state.get("frontend_subgraph_iterations", 0)

    print(f"[Frontend Router] Iterations: {current_iterations}/{max_subgraph_iterations}")

    # 1. Iteration 상한 도달
    if current_iterations >= max_subgraph_iterations:
        print("[Frontend Router] → frontend_done (max iterations)")
        return "frontend_done"

    # 2. 재작업 필요 여부
    if state.get("frontend_needs_rework", False):
        print("[Frontend Router] → frontend_rework")
        return "frontend_rework"

    # 3. 정상 완료
    print("[Frontend Router] → frontend_done (success)")
    return "frontend_done"


def create_frontend_subgraph(config):
    """
    Frontend SubGraph 생성

    Args:
        config: DAACSConfig 인스턴스

    Returns:
        Compiled SubGraph
    """
    frontend_llm = config.get_llm_source("frontend")
    cli_config = config.get_cli_config()

    # CLI Client 생성
    cli_client = CodexClient(
        cwd="output/frontend",
        timeout_sec=cli_config.get("timeout", 180),
        client_name="frontend"
    )

    # SubGraph 정의
    graph = StateGraph(DAACSState)

    # 노드 추가
    graph.add_node("coder", lambda s: frontend_coder_node(s, frontend_llm, cli_client))
    graph.add_node("verifier", frontend_verifier_node)

    # 엣지 연결
    graph.set_entry_point("coder")
    graph.add_edge("coder", "verifier")

    # Conditional Edge: Router
    graph.add_conditional_edges(
        "verifier",
        frontend_router,
        {
            "frontend_rework": "coder",
            "frontend_done": END
        }
    )

    return graph.compile()


# 사용 예시
if __name__ == "__main__":
    from ..config_loader import DAACSConfig
    from ..models.daacs_state import create_initial_daacs_state

    print("=== Frontend SubGraph Test ===\n")

    # Config 로드
    config = DAACSConfig("daacs_config.yaml")

    # 초기 상태
    state = create_initial_daacs_state(
        goal="Create a TODO UI with React",
        config=config.config
    )

    # SubGraph 실행
    frontend_graph = create_frontend_subgraph(config)

    print("Frontend SubGraph compiled successfully!")
    print(f"Nodes: {frontend_graph.get_graph().nodes}")
