"""
DAACS v6.0 - Backend SubGraph
Backend: Coder → Verifier → Router
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from ..models.daacs_state import DAACSState
from ..llm.cli_executor import CodexClient
from .verification import run_verification
import re
import json


def parse_files_from_response(response: str) -> Dict[str, str]:
    """
    LLM 응답에서 파일 파싱

    Expected format:
    FILE: main.py
    ```python
    ...
    ```

    FILE: requirements.txt
    ```
    ...
    ```
    """
    files = {}
    current_file = None
    in_code_block = False
    code_lines = []

    for line in response.split('\n'):
        line_stripped = line.strip()
        
        # 1. FILE: filename 형식
        if line.startswith('FILE:'):
            # 이전 파일 저장
            if current_file and code_lines:
                files[current_file] = '\n'.join(code_lines)
                code_lines = []
            
            raw_filename = line.replace('FILE:', '').strip()
            current_file = _normalize_path(raw_filename)
            in_code_block = False
            continue

        # 2. 코드 블록 시작 (```python:main.py 또는 ```)
        if line.startswith('```'):
            # 코드 블록 종료
            if in_code_block:
                in_code_block = False
                # 파일 저장 (블록이 끝날 때 저장)
                if current_file and code_lines:
                    files[current_file] = '\n'.join(code_lines)
                    code_lines = []
                    current_file = None # 파일 컨텍스트 초기화 (다음 파일을 위해)
            # 코드 블록 시작
            else:
                in_code_block = True
                # ```python:main.py 형식 확인
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        raw_filename = parts[1].strip()
                        current_file = _normalize_path(raw_filename)
            continue

        # 3. 파일명 주석 (# main.py 또는 // main.py) - 코드 블록 밖에서만
        if not in_code_block and (line_stripped.startswith('# ') or line_stripped.startswith('// ')):
            potential_filename = line_stripped[2:].strip()
            # 확장자가 있는 경우만 파일명으로 간주
            if '.' in potential_filename and not ' ' in potential_filename:
                 # 이전 파일 저장
                if current_file and code_lines:
                    files[current_file] = '\n'.join(code_lines)
                    code_lines = []
                current_file = _normalize_path(potential_filename)
                continue

        # 코드 라인 수집
        if in_code_block and current_file:
            code_lines.append(line)

    # 마지막 파일 저장 (혹시 블록이 안 닫혔거나 마지막인 경우)
    if current_file and code_lines:
        files[current_file] = '\n'.join(code_lines)

    return files

def _normalize_path(path: str) -> str:
    """경로 정규화: output/, frontend/, backend/ prefix 제거"""
    normalized = path.strip()
    # 백틱 제거 (가끔 `main.py` 처럼 옴)
    normalized = normalized.replace('`', '')
    
    prefixes_to_remove = ['output/frontend/', 'output/backend/', 'output/', 'frontend/', 'backend/']
    for prefix in prefixes_to_remove:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return normalized


def _get_model_specific_instructions(llm_type: str, role: str) -> str:
    """
    모델별 특수 지시사항 반환 (에이전틱 모드용)
    
    Args:
        llm_type: LLM 타입 (claude_code, codex, gemini 등)
        role: 역할 (backend, frontend)
    
    Returns:
        모델별 특수 지시사항 문자열
    """
    instructions = []
    
    # Claude 전용 지시사항 (에이전틱 모드)
    if 'claude' in llm_type.lower():
        instructions.append("""
=== 🚀 AGENTIC MODE (CLAUDE) ===
✅ You have FULL file creation permissions.
✅ CREATE all files in the WORKING DIRECTORY (cwd).
✅ You decide the best file structure for this project.
⚠️ Do NOT ask for confirmation - just create the files.
⚠️ Do NOT create .md files (README, docs, etc.) - code only!
""")
    
    # Codex 전용 지시사항 (에이전틱 모드)
    elif 'codex' in llm_type.lower():
        instructions.append("""
=== 🚀 AGENTIC MODE (CODEX) ===
✅ Create all files in the WORKING DIRECTORY (cwd).
✅ Use your file creation tools.
✅ You decide the best file structure for this project.
""")
    
    # Gemini 전용 지시사항 (에이전틱 모드)
    elif 'gemini' in llm_type.lower():
        instructions.append("""
=== 🚀 AGENTIC MODE (GEMINI) ===
✅ You have file creation permissions.
✅ CREATE all files in the WORKING DIRECTORY (cwd).
✅ You decide the best file structure for this project.
⚠️ Generate COMPLETE files, not snippets.
""")
    
    # 기본 지시사항
    else:
        instructions.append("""
=== FILE CREATION ===
Create all files in the WORKING DIRECTORY (cwd).
""")
    
    return "\n".join(instructions)


def backend_coder_node(state: DAACSState, backend_llm, cli_client: CodexClient) -> Dict:
    """
    Backend 코드 생성 노드

    Args:
        state: 현재 상태
        backend_llm: Backend 역할의 LLM Source
        cli_client: CLI Assistant 클라이언트

    Returns:
        상태 업데이트
    """
    print(f"[Backend Coder] Starting... (iteration {state['backend_subgraph_iterations']})")
    
    # LLM 타입 확인
    llm_type = state.get('llm_sources', {}).get('backend', 'unknown')
    print(f"[Backend Coder] Using LLM source: {llm_type}")

    goal = state['current_goal']
    orchestrator_plan = state.get('orchestrator_plan', '')
    api_spec = state.get('api_spec', {})
    
    # 이전 실패 사유 (재작업 시 피드백 루프)
    failure_summary = state.get('failure_summary', [])
    failure_context = ""
    if failure_summary:
        print(f"[Backend Coder] 🔥 Received {len(failure_summary)} failure issues to fix!")
        for issue in failure_summary[:3]:
            print(f"[Backend Coder]   → {issue[:80]}...")
        failure_reasons = "\n".join(f"- {reason}" for reason in failure_summary)
        failure_context = f"""
=== ⚠️ PREVIOUS FAILURE REASONS (FIX THESE!) ===
The previous code generation failed verification. You MUST fix these issues:
{failure_reasons}

Please carefully address each issue above in your new code.
"""

    # API 스펙을 문자열로 변환
    api_spec_str = json.dumps(api_spec, indent=2) if api_spec else "No API spec provided"

    # 백엔드 디렉토리 설정 및 생성 (프롬프트에 포함시키기 위해 먼저 생성)
    import os
    import glob
    project_dir = state.get("project_dir", "output")
    backend_dir = os.path.abspath(f"{project_dir}/backend")
    os.makedirs(backend_dir, exist_ok=True)
    
    # 모델별 특수 지시사항
    model_specific_instructions = _get_model_specific_instructions(llm_type, "backend")

    # LLM 프롬프트 - 절대 경로 포함
    prompt = f"""
You are a senior backend developer with Tech Lead mindset.

=== GOAL ===
{goal}
{failure_context}
=== ORCHESTRATOR PLAN ===
{orchestrator_plan}

=== API SPECIFICATION (MUST IMPLEMENT EXACTLY) ===
{api_spec_str}

{model_specific_instructions}

=== STRICT ROLE SEPARATION ===
⚠️ IMPORTANT: You are the BACKEND developer ONLY.
- Generate ONLY backend files (Python, requirements.txt)
- Do NOT generate any frontend files (React, HTML, CSS, JS)
- Frontend is handled by a separate developer

=== 🚨 FILE CREATION PATH (CRITICAL!) 🚨 ===
**CREATE ALL FILES IN THIS EXACT DIRECTORY:**
{backend_dir}

⚠️ DO NOT create files anywhere else!
⚠️ DO NOT create files in the current directory or root!

=== CODING RULES (Strict) ===
1. **Python 3.12**: Target Python 3.12 (NOT 3.14+)
   - Use Pydantic V2 with `from_attributes=True` (not deprecated `orm_mode`)
   - Use `ast.Constant` for literals (NOT `ast.Str`, `ast.Num`)
2. **Clarity**: Code must be clear and simple
3. **No Complexity**: Avoid unnecessary abstractions
4. **Consistency**: Variable/function names must be consistent
5. **Complete**: Generate ALL BACKEND files for a runnable project
6. **CORS**: Include frontend integration config
7. **NO MARKDOWN FILES**: Do NOT create .md files (README, docs, etc.) - code only!
8. **ENGLISH ONLY**: Write ALL code, comments, docstrings, and string literals in English only. Do NOT use Korean or any other non-ASCII characters.

=== IMPLEMENTATION CHECKLIST ===
□ Implement ALL API endpoints from spec
□ Match EXACT paths and methods (GET/POST/PUT/DELETE)
□ Follow request/response schemas
□ Implement all data models
□ Add proper error handling
□ Include requirements.txt

=== 🚨 CRITICAL: RUNNABLE SERVER (REQUIRED!) 🚨 ===
The server MUST be runnable via `python main.py`. Include this at the END of main.py:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

⚠️ WITHOUT this, the server will NOT start!

Generate a complete Python/FastAPI project in {backend_dir}.
"""

    try:
        # CLI 클라이언트의 cwd를 백엔드 디렉토리로 설정
        cli_client.cwd = backend_dir
        
        # Backend LLM 호출 (에이전틱 모드 - 파일 직접 생성)
        response = backend_llm.invoke(prompt)
        
        # 에이전틱 모드: 파일시스템에서 생성된 파일 스캔
        # __pycache__, .git, venv 등 제외
        EXCLUDE_DIRS = {'__pycache__', '.git', 'venv', '.venv', 'env', '.env', 'node_modules'}
        files = {}
        for ext in ['*.py', '*.txt', '*.json', '*.yaml', '*.yml']:
            for filepath in glob.glob(os.path.join(backend_dir, '**', ext), recursive=True):
                # 제외 폴더 안에 있는 파일 스킵
                path_parts = filepath.replace('\\', '/').split('/')
                if any(excluded in path_parts for excluded in EXCLUDE_DIRS):
                    continue
                relpath = os.path.relpath(filepath, backend_dir)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    files[relpath] = f.read()
        
        if not files:
            # 폴백: 응답에서 파싱 시도 (Codex 같은 텍스트 모드용)
            files = parse_files_from_response(response)
            if files:
                # 파싱된 파일 저장
                for filename, content in files.items():
                    filepath = os.path.join(backend_dir, filename)
                    file_dir = os.path.dirname(filepath)
                    if file_dir:
                        os.makedirs(file_dir, exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"[Backend Coder] Wrote {filename} to {backend_dir}/")

        if not files:
            print("[Backend Coder] [WARN] No files generated from LLM")
            return {
                "backend_files": {},
                "backend_status": "failed",
                "backend_logs": ["Backend coder failed: No files generated"],
                "backend_action_type": "codegen",
                "backend_subgraph_iterations": state.get("backend_subgraph_iterations", 0) + 1
            }

        print(f"[Backend Coder] Generated {len(files)} files: {list(files.keys())}")

        return {
            "backend_files": files,
            "backend_status": "working",
            "backend_logs": [f"Backend coder generated: {list(files.keys())}"],
            "backend_action_type": "files",
            "backend_subgraph_iterations": state.get("backend_subgraph_iterations", 0) + 1
        }

    except Exception as e:
        print(f"[Backend Coder] [ERROR] Error: {e}")
        return {
            "backend_files": {},
            "backend_status": "failed",
            "backend_logs": [f"Backend coder error: {str(e)}"],
            "backend_action_type": "codegen",
            "backend_subgraph_iterations": state.get("backend_subgraph_iterations", 0) + 1
        }


def backend_verifier_node(state: DAACSState) -> Dict:
    """
    Backend 검증 노드

    v6.0 개선: Python 구문 검사 + API 스펙 준수 검증
    """
    print(f"[Backend Verifier] Starting...")

    # 'backend' 타입으로 변경 → 구문 검사 + API 스펙 준수 검증
    action_type = "backend"
    
    project_dir = state.get("project_dir", "output")
    backend_dir = f"{project_dir}/backend"
    
    # 파일 경로 수정: project_dir/backend/ 접두사 추가
    filenames = list(state.get("backend_files", {}).keys())
    files = [f"{backend_dir}/{f}" for f in filenames]
    
    # API 스펙 가져오기
    api_spec = state.get("api_spec", {})

    if not files:
        print("[Backend Verifier] [WARN] No files to verify")
        return {
            "backend_needs_rework": True,
            "backend_status": "failed",
            "backend_logs": ["Backend verifier: No files to verify"],
            "backend_verification_details": []
        }

    # 검증 실행 (구문 검사 + API 스펙 준수)
    verification_result = run_verification(
        action_type=action_type,
        files=files,
        test_result=state.get("backend_test_result"),
        api_spec=api_spec
    )

    all_passed = verification_result["ok"]
    summary = verification_result["summary"]
    verdicts = verification_result["verdicts"]

    print(f"[Backend Verifier] Result: {'[PASS]' if all_passed else '[FAIL]'}")
    print(f"[Backend Verifier] Summary: {summary}")
    
    # 개별 검증 결과 출력
    for v in verdicts:
        status = "✅" if v["ok"] else "❌"
        print(f"  {status} {v['template']}: {v['reason'][:80]}")

    # 검증 실패 시 실패 정보 수집
    failure_summary = []
    if not all_passed:
        failure_summary = [v["reason"] for v in verdicts if not v["ok"]]

    return {
        "backend_needs_rework": not all_passed,
        "backend_status": "completed" if all_passed else "failed",
        "backend_logs": [f"Backend verifier: {summary}"],
        "backend_verification_details": verdicts,
        "failure_summary": failure_summary if not all_passed else []
    }


def backend_router(state: DAACSState) -> str:
    """
    Backend Router: 재작업 또는 완료 결정

    v5.0의 iteration 제한 로직 적용
    """
    max_subgraph_iterations = state.get("max_subgraph_iterations", 2)  # Issue #5: config에서 읽음
    current_iterations = state.get("backend_subgraph_iterations", 0)

    print(f"[Backend Router] Iterations: {current_iterations}/{max_subgraph_iterations}")

    # 1. Iteration 상한 도달
    if current_iterations >= max_subgraph_iterations:
        print("[Backend Router] → backend_done (max iterations)")
        return "backend_done"

    # 2. 재작업 필요 여부
    if state.get("backend_needs_rework", False):
        print("[Backend Router] → backend_rework")
        return "backend_rework"

    # 3. 정상 완료
    print("[Backend Router] → backend_done (success)")
    return "backend_done"


def create_backend_subgraph(config):
    """
    Backend SubGraph 생성

    Args:
        config: DAACSConfig 인스턴스

    Returns:
        Compiled SubGraph
    """
    backend_llm = config.get_llm_source("backend")
    cli_config = config.get_cli_config()

    # CLI Client 생성
    cli_client = CodexClient(
        cwd="output/backend",
        timeout_sec=cli_config.get("timeout", 180),
        client_name="backend"
    )

    # SubGraph 정의
    graph = StateGraph(DAACSState)

    # 노드 추가
    graph.add_node("coder", lambda s: backend_coder_node(s, backend_llm, cli_client))
    graph.add_node("verifier", backend_verifier_node)

    # 엣지 연결
    graph.set_entry_point("coder")
    graph.add_edge("coder", "verifier")

    # Conditional Edge: Router
    graph.add_conditional_edges(
        "verifier",
        backend_router,
        {
            "backend_rework": "coder",  # 재작업 시 Coder로 돌아감
            "backend_done": END
        }
    )

    return graph.compile()


# 사용 예시
if __name__ == "__main__":
    from ..config_loader import DAACSConfig
    from ..models.daacs_state import create_initial_daacs_state

    print("=== Backend SubGraph Test ===\n")

    # Config 로드
    config = DAACSConfig("daacs_config.yaml")

    # 초기 상태
    state = create_initial_daacs_state(
        goal="Create a TODO API with FastAPI",
        config=config.config
    )

    # SubGraph 실행
    backend_graph = create_backend_subgraph(config)

    print("Backend SubGraph compiled successfully!")
    print(f"Nodes: {backend_graph.get_graph().nodes}")
