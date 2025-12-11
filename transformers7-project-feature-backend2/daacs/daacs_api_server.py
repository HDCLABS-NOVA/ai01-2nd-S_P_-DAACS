"""
DAACS v6.0 - Web API Server
Nova-Canvas 프론트엔드와 연동하기 위한 REST API 서버
"""

import os
import sys
import json
import asyncio
import threading
import subprocess
import zipfile
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# DAACS 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

# ==================== 모델 정의 ====================

class ProjectConfig(BaseModel):
    orchestrator_model: Optional[str] = "gpt-4o"
    backend_model: Optional[str] = "gpt-4o"
    frontend_model: Optional[str] = "gpt-4o"
    max_iterations: Optional[int] = 10

class ProjectCreateRequest(BaseModel):
    goal: str
    config: Optional[ProjectConfig] = None
    
class ProjectResponse(BaseModel):
    id: str
    goal: str
    status: str
    created_at: str
    iteration: int = 0
    needs_backend: bool = False
    needs_frontend: bool = False
    plan: str = ""
    config: Optional[ProjectConfig] = None

class LogEntry(BaseModel):
    timestamp: str
    node: str
    message: str
    level: str = "info"

# ==================== 프로젝트 저장소 ====================

class ProjectStore:
    def __init__(self):
        self.projects: Dict[str, Dict] = {}
        self.logs: Dict[str, List[Dict]] = {}
        self.websockets: Dict[str, List] = {}
        self.log_watchers: Dict[str, List] = {}
    
    def create_project(self, goal: str) -> str:
        import random
        project_id = str(random.randint(10000000, 99999999))
        self.projects[project_id] = {
            "id": project_id,
            "goal": goal,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "iteration": 0,
            "needs_backend": False,
            "needs_frontend": False,
            "plan": "",
            "config": None,
        }
        self.logs[project_id] = []
        self.websockets[project_id] = []
        return project_id
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        return self.projects.get(project_id)
    
    def list_projects(self) -> List[Dict]:
        return list(self.projects.values())
    
    def update_project(self, project_id: str, updates: Dict):
        if project_id in self.projects:
            self.projects[project_id].update(updates)
    
    def add_log(self, project_id: str, node: str, message: str, level: str = "info"):
        if project_id not in self.logs:
            self.logs[project_id] = []
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "node": node,
            "message": message,
            "level": level,
        }
        self.logs[project_id].append(log_entry)
        print(f"[{level.upper()}] [{node}] {message}")
        
        # WebSocket으로 실시간 전송
        self._broadcast_log(project_id, log_entry)
    
    def _broadcast_log(self, project_id: str, log_entry: Dict):
        """WebSocket watchers에게 로그 브로드캐스트"""
        watchers = self.log_watchers.get(project_id, [])
        for ws in watchers[:]:  # 복사본으로 순회
            try:
                asyncio.create_task(ws.send_json(log_entry))
            except Exception:
                # 연결이 끊긴 경우 제거
                if ws in self.log_watchers.get(project_id, []):
                    self.log_watchers[project_id].remove(ws)
    
    def get_logs(self, project_id: str) -> List[Dict]:
        return self.logs.get(project_id, [])

store = ProjectStore()

# ==================== DAACS 워크플로우 실행 ====================

def run_daacs_workflow(project_id: str, goal: str, project_config: Optional[Dict] = None):
    """별도 스레드에서 DAACS 워크플로우 실행"""
    
    try:
        store.update_project(project_id, {"status": "planning"})
        store.add_log(project_id, "system", "Starting DAACS workflow...")
        
        # DAACS 모듈 임포트 경로 설정
        daacs_dir = Path(__file__).parent
        project_dir = daacs_dir.parent
        if str(project_dir) not in sys.path:
            sys.path.insert(0, str(project_dir))
        if str(daacs_dir) not in sys.path:
            sys.path.insert(0, str(daacs_dir))
        
        # DAACS config 로드
        from daacs.config_loader import DAACSConfig
        from daacs.graph.daacs_workflow import get_compiled_daacs_workflow
        from daacs.models.daacs_state import create_initial_daacs_state
        
        config = DAACSConfig("daacs_config.yaml")
        
        # 설정 오버라이드
        if project_config:
            # Provider → CLI 타입 매핑
            provider_to_cli = {
                "openai": "codex",
                "anthropic": "claude_code",
                "google": "gemini",
                "groq": "codex",  # Groq는 Codex로 fallback
            }
            
            # Orchestrator - 역할별 CLI 타입 설정
            if project_config.get("orchestrator_model"):
                model = project_config["orchestrator_model"]
                provider = config._parse_model_provider(model)
                orchestrator_cli = provider_to_cli.get(provider, "claude_code")
                config.role_cli_types["orchestrator"] = orchestrator_cli
                print(f"[{project_id}] Orchestrator: {model} ({provider}) → CLI: {orchestrator_cli}")
                config.config["roles"]["orchestrator"]["plugin"] = {
                    "provider": provider,
                    "model": model,
                    "temperature": 0.3
                }
            
            # Backend - 역할별 CLI 타입 설정
            if project_config.get("backend_model"):
                model = project_config["backend_model"]
                provider = config._parse_model_provider(model)
                backend_cli = provider_to_cli.get(provider, "claude_code")
                config.role_cli_types["backend"] = backend_cli
                print(f"[{project_id}] Backend: {model} ({provider}) → CLI: {backend_cli}")
                config.config["roles"]["backend"]["plugin"] = {
                    "provider": provider,
                    "model": model,
                    "temperature": 0.7
                }

            # Frontend - 역할별 CLI 타입 설정
            if project_config.get("frontend_model"):
                model = project_config["frontend_model"]
                provider = config._parse_model_provider(model)
                frontend_cli = provider_to_cli.get(provider, "claude_code")
                config.role_cli_types["frontend"] = frontend_cli
                print(f"[{project_id}] Frontend: {model} ({provider}) → CLI: {frontend_cli}")
                config.config["roles"]["frontend"]["plugin"] = {
                    "provider": provider,
                    "model": model,
                    "temperature": 0.7
                }
            
            # 역할별 CLI 타입 로그
            print(f"[{project_id}] Role CLI Types: {config.role_cli_types}")
                
            # Max Iterations
            if project_config.get("max_iterations"):
                print(f"[{project_id}] Overriding max iterations: {project_config['max_iterations']}")
                config.config["execution"]["max_iterations"] = int(project_config["max_iterations"])
            
            # LLM 소스 재생성 (변경된 역할별 CLI 타입 적용)
            config._create_llm_sources()
            
        workflow = get_compiled_daacs_workflow(config)
        
        # 초기 상태 생성
        initial_state = create_initial_daacs_state(
            goal=goal,
            config=config.get_execution_config(),
            session_id=project_id
        )
        
        store.add_log(project_id, "orchestrator", "Planning phase started")
        store.update_project(project_id, {"status": "running"})
        
        # 워크플로우 실행
        # 스트리밍 모드로 실행하여 중간 결과 캡처
        for event in workflow.stream(initial_state):
            # 이벤트 처리
            for node_name, node_output in event.items():
                if node_output:
                    # 노드별 상세 로그
                    if node_name == "orchestrator_planning":
                        store.add_log(project_id, "orchestrator", f"Orchestrator Planning Started")
                        if "orchestrator_plan" in node_output:
                            plan = node_output.get("orchestrator_plan", "")
                            needs_be = node_output.get("needs_backend", False)
                            needs_fe = node_output.get("needs_frontend", False)
                            store.update_project(project_id, {
                                "plan": plan,
                                "needs_backend": needs_be,
                                "needs_frontend": needs_fe
                            })
                            store.add_log(project_id, "orchestrator", f"Plan: {plan[:150]}..." if len(plan) > 150 else f"Plan: {plan}")
                            store.add_log(project_id, "orchestrator", f"Needs Backend: {needs_be}, Needs Frontend: {needs_fe}")
                    
                    elif node_name == "backend_subgraph":
                        if "backend_files" in node_output:
                            files = node_output.get("backend_files", {})
                            file_list = list(files.keys())
                            store.update_project(project_id, {
                                "backend_files": file_list,
                                "backend_files_map": files
                            })
                            store.add_log(project_id, "backend", f"[Backend Coder] Generated {len(files)} files: {file_list}")
                        if "backend_status" in node_output:
                            status = node_output.get("backend_status")
                            store.add_log(project_id, "backend", f"[Backend Verifier] Result: {status}")
                    
                    elif node_name == "frontend_subgraph":
                        if "frontend_files" in node_output:
                            files = node_output.get("frontend_files", {})
                            file_list = list(files.keys())
                            store.update_project(project_id, {
                                "frontend_files": file_list,
                                "frontend_files_map": files
                            })
                            store.add_log(project_id, "frontend", f"[Frontend Coder] Generated {len(files)} files: {file_list}")
                        if "frontend_status" in node_output:
                            status = node_output.get("frontend_status")
                            store.add_log(project_id, "frontend", f"[Frontend Verifier] Result: {status}")
                    
                    elif node_name == "orchestrator_judgment":
                        compatible = node_output.get("compatibility_verified", False)
                        issues = node_output.get("compatibility_issues", [])
                        store.add_log(project_id, "orchestrator", f"[Orchestrator Judgment] Compatible: {compatible}")
                        if issues:
                            store.add_log(project_id, "orchestrator", f"[Orchestrator Judgment] Issues: {len(issues)}")
                            for issue in issues[:3]:  # 처음 3개만
                                store.add_log(project_id, "orchestrator", f"  → {issue}")
                    
                    elif node_name == "orchestrator_replanning":
                        store.add_log(project_id, "orchestrator", "[Orchestrator Replanning] Rework initiated")
                        if "current_goal" in node_output:
                            store.add_log(project_id, "orchestrator", f"  → New Goal: {node_output['current_goal'][:100]}...")
                    
                    elif node_name == "save_context":
                        store.add_log(project_id, "system", "[Context DB] Saving artifacts...")
                    
                    elif node_name == "deliver":
                        final_status = node_output.get("final_status", "unknown")
                        stop_reason = node_output.get("stop_reason", "")
                        store.add_log(project_id, "system", f"[Deliver] Final Status: {final_status}")
                        if stop_reason:
                            store.add_log(project_id, "system", f"[Deliver] Reason: {stop_reason}")
                    
                    # 반복 횟수 업데이트
                    if "iteration_count" in node_output:
                        store.update_project(project_id, {"iteration": node_output["iteration_count"]})
                    
                    # 노드 완료 로그 (위에서 이미 상세 로그를 찍었으면 생략)
                    if node_name not in ["orchestrator_planning", "backend_subgraph", "frontend_subgraph", 
                                         "orchestrator_judgment", "orchestrator_replanning", "save_context", "deliver"]:
                        store.add_log(project_id, node_name, f"Node completed")
        
        store.update_project(project_id, {"status": "completed"})
        store.add_log(project_id, "system", "Workflow completed successfully!")
        
    except Exception as e:
        store.update_project(project_id, {"status": "failed", "errors": [str(e)]})
        store.add_log(project_id, "system", f"Workflow failed: {e}", level="error")

# ==================== FastAPI 앱 설정 ====================

app = FastAPI(title="DAACS API", version="6.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(request: ProjectCreateRequest):
    """새 DAACS 프로젝트 생성 및 워크플로우 시작"""
    project_id = store.create_project(request.goal)
    
    # 설정 저장
    if request.config:
        store.update_project(project_id, {"config": request.config.dict()})
    
    # 별도 스레드에서 워크플로우 실행
    thread = threading.Thread(
        target=run_daacs_workflow,
        args=(project_id, request.goal, request.config.dict() if request.config else None)
    )
    thread.daemon = True
    thread.start()
    
    project = store.get_project(project_id)
    return ProjectResponse(**project)

@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects():
    """모든 프로젝트 목록"""
    projects = store.list_projects()
    return [ProjectResponse(**p) for p in projects]

def recover_project_from_disk(project_id: str) -> Optional[Dict]:
    """디스크에서 프로젝트 복구 (서버 재시작 후)"""
    project_dir = Path(__file__).parent.parent / "project" / f"project_{project_id}"
    if not project_dir.exists():
        return None
    
    # 기본 프로젝트 정보 생성
    project_data = {
        "id": project_id,
        "goal": "(Recovered from disk)",
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "iteration": 0,
        "needs_backend": (project_dir / "backend").exists(),
        "needs_frontend": (project_dir / "frontend").exists(),
        "plan": "",
        "config": None,
    }
    
    # 인메모리 저장소에 추가
    store.projects[project_id] = project_data
    store.logs[project_id] = [{"timestamp": datetime.now().isoformat(), "node": "system", "message": "Project recovered from disk", "level": "info"}]
    
    return project_data

@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """프로젝트 상태 조회"""
    project = store.get_project(project_id)
    if not project:
        # 디스크에서 복구 시도
        project = recover_project_from_disk(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**project)

@app.get("/api/projects/{project_id}/logs", response_model=List[LogEntry])
async def get_project_logs(project_id: str):
    """프로젝트 로그 조회"""
    if project_id not in store.projects:
        # 디스크에서 복구 시도
        if not recover_project_from_disk(project_id):
            raise HTTPException(status_code=404, detail="Project not found")
    logs = store.get_logs(project_id)
    return [LogEntry(**log) for log in logs]

@app.get("/api/projects/{project_id}/files")
async def get_project_files(project_id: str):
    """생성된 파일 목록 - 디스크에서 직접 스캔"""
    # 디스크에서 프로젝트 디렉토리 확인 (인메모리 체크 생략)
    project_dir = Path(__file__).parent.parent / "project" / f"project_{project_id}"
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    backend_files = []
    frontend_files = []
    
    backend_dir = project_dir / "backend"
    frontend_dir = project_dir / "frontend"
    
    if backend_dir.exists():
        for f in backend_dir.rglob("*"):
            if f.is_file() and not any(x in str(f) for x in ["__pycache__", ".pyc", "node_modules", ".git"]):
                rel_path = str(f.relative_to(backend_dir))
                backend_files.append(rel_path)
    
    if frontend_dir.exists():
        for f in frontend_dir.rglob("*"):
            if f.is_file() and not any(x in str(f) for x in ["__pycache__", "node_modules", ".git", "dist"]):
                rel_path = str(f.relative_to(frontend_dir))
                frontend_files.append(rel_path)
    
    return {
        "backend_files": sorted(backend_files),
        "frontend_files": sorted(frontend_files)
    }

@app.get("/api/projects/{project_id}/files/content")
async def get_file_content(project_id: str, file: str, type: str):
    """파일 내용 조회"""
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 프로젝트 디렉토리 경로 구성
    project_dir = Path(__file__).parent.parent / "project" / f"project_{project_id}"
    
    if type == "backend":
        file_path = project_dir / "backend" / file
    elif type == "frontend":
        file_path = project_dir / "frontend" / file
    else:
        raise HTTPException(status_code=400, detail="Invalid type. Must be 'backend' or 'frontend'")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

class FileUpdateRequest(BaseModel):
    content: str

@app.put("/api/projects/{project_id}/files")
async def update_file_content(project_id: str, file: str, type: str, request: FileUpdateRequest):
    """파일 내용 저장"""
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_dir = Path(__file__).parent.parent / "project" / f"project_{project_id}"
    
    if type == "backend":
        file_path = project_dir / "backend" / file
    elif type == "frontend":
        file_path = project_dir / "frontend" / file
    else:
        raise HTTPException(status_code=400, detail="Invalid type. Must be 'backend' or 'frontend'")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file}")
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.content)
        
        store.add_log(project_id, "system", f"File updated: {type}/{file}")
        return {"message": "File updated successfully", "file": file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

@app.get("/api/projects/{project_id}/download")
async def download_project(project_id: str):
    """프로젝트 전체를 ZIP 파일로 다운로드"""
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_dir = Path(__file__).parent.parent / "project" / f"project_{project_id}"
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")
    
    zip_buffer = io.BytesIO()
    
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            backend_dir = project_dir / "backend"
            if backend_dir.exists():
                for file_path in backend_dir.rglob("*"):
                    if file_path.is_file() and not any(x in str(file_path) for x in ["__pycache__", ".pyc"]):
                        arcname = f"backend/{file_path.relative_to(backend_dir)}"
                        zip_file.write(file_path, arcname)
            
            frontend_dir = project_dir / "frontend"
            if frontend_dir.exists():
                for file_path in frontend_dir.rglob("*"):
                    if file_path.is_file() and not any(x in str(file_path) for x in ["node_modules", ".git", "dist"]):
                        arcname = f"frontend/{file_path.relative_to(frontend_dir)}"
                        zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        headers = {
            "Content-Disposition": f"attachment; filename=project_{project_id}.zip"
        }
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP: {str(e)}")

# ==================== 프로젝트 실행 ====================

# 실행 중인 프로세스 저장
running_processes: Dict[str, Dict] = {}

@app.post("/api/projects/{project_id}/run")
async def run_project(project_id: str, background_tasks: BackgroundTasks):
    """프로젝트 실행 - 백엔드와 프론트엔드 서버 시작"""
    # 디스크에서 프로젝트 디렉토리 확인 (인메모리 저장소 대신)
    project_dir = Path(__file__).parent.parent / "project" / f"project_{project_id}"
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project directory not found: {project_dir}")
    
    backend_dir = project_dir / "backend"
    frontend_dir = project_dir / "frontend"
    
    result = {"backend_port": None, "frontend_port": None, "status": "starting"}
    
    # 기존 프로세스 정리 (포트 충돌 방지)
    import subprocess
    for port in [8080, 3000]:
        try:
            subprocess.run(
                f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :{port}\') do taskkill /F /PID %a',
                shell=True, capture_output=True, timeout=5
            )
        except:
            pass
    
    # 백엔드 실행 (포트 8080)
    if backend_dir.exists():
        # 진입점 파일 찾기 (유동적)
        entry_files = ["main.py", "app.py", "server.py", "run.py"]
        entry_file = None
        for ef in entry_files:
            if (backend_dir / ef).exists():
                entry_file = ef
                break
        
        if entry_file:
            try:
                backend_port = 8080
                
                # Python 3.12 venv 경로 (프로젝트 루트의 .venv)
                venv_python = Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
                if not venv_python.exists():
                    # fallback: 시스템 python
                    venv_python = "python"
                else:
                    venv_python = str(venv_python)
                
                # requirements.txt 설치
                requirements_file = backend_dir / "requirements.txt"
                if requirements_file.exists():
                    store.add_log(project_id, "system", "Installing backend dependencies...")
                    install_result = subprocess.run(
                        [venv_python, "-m", "pip", "install", "-r", "requirements.txt"],
                        cwd=str(backend_dir),
                        capture_output=True,
                        timeout=120
                    )
                    if install_result.returncode == 0:
                        store.add_log(project_id, "system", "Backend dependencies installed")
                    else:
                        store.add_log(project_id, "system", f"Warning: pip install failed", "warning")
                
                # 백엔드 서버 시작 - uvicorn.run() 없으면 fallback으로 uvicorn 모듈 실행
                entry_path = backend_dir / entry_file
                use_uvicorn_module = False
                
                # main.py 내용 확인하여 uvicorn.run()이 있는지 체크
                try:
                    main_content = entry_path.read_text(encoding='utf-8')
                    if 'uvicorn.run' not in main_content and 'uvicorn' not in main_content.split('if __name__')[-1] if 'if __name__' in main_content else True:
                        # uvicorn.run()이 없으면 모듈로 실행
                        use_uvicorn_module = True
                        store.add_log(project_id, "system", "No uvicorn.run() found, using fallback: uvicorn module", "warning")
                except Exception:
                    pass
                
                if use_uvicorn_module:
                    # Fallback: uvicorn -m으로 실행 (main:app 형태)
                    module_name = entry_file.replace('.py', '')
                    backend_process = subprocess.Popen(
                        [venv_python, "-m", "uvicorn", f"{module_name}:app", "--host", "0.0.0.0", "--port", str(backend_port)],
                        cwd=str(backend_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                    )
                else:
                    # 정상: python main.py로 실행
                    backend_process = subprocess.Popen(
                        [venv_python, entry_file],
                        cwd=str(backend_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                    )
                running_processes[f"{project_id}_backend"] = {
                    "process": backend_process,
                    "port": backend_port
                }
                result["backend_port"] = backend_port
                store.add_log(project_id, "system", f"Backend server starting on port {backend_port} (using {entry_file})")
            except Exception as e:
                store.add_log(project_id, "system", f"Failed to start backend: {str(e)}", "error")
        else:
            store.add_log(project_id, "system", "No backend entry file found (main.py, app.py, server.py, run.py)", "warning")
    
    # 프론트엔드 실행 (포트 3000)
    if frontend_dir.exists() and (frontend_dir / "package.json").exists():
        try:
            import subprocess
            import re
            frontend_port = 3000

            # vite.config.js 파일에서 open: true를 open: false로 변경
            vite_config = frontend_dir / "vite.config.js"
            if vite_config.exists():
                try:
                    content = vite_config.read_text(encoding="utf-8")
                    # open: true를 open: false로 변경
                    content = re.sub(r'open:\s*true', 'open: false', content)
                    vite_config.write_text(content, encoding="utf-8")
                    store.add_log(project_id, "system", "Disabled auto-open in vite.config.js")
                except Exception as e:
                    store.add_log(project_id, "system", f"Warning: Could not modify vite.config.js: {e}", "warning")

            # npm install 먼저 실행
            subprocess.run(["npm", "install"], cwd=str(frontend_dir), capture_output=True, shell=True)
            frontend_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", str(frontend_port)],
                cwd=str(frontend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            running_processes[f"{project_id}_frontend"] = {
                "process": frontend_process,
                "port": frontend_port
            }
            result["frontend_port"] = frontend_port
            store.add_log(project_id, "system", f"Frontend server starting on port {frontend_port}")
        except Exception as e:
            store.add_log(project_id, "system", f"Failed to start frontend: {str(e)}", "error")
    
    result["status"] = "running" if (result["backend_port"] or result["frontend_port"]) else "failed"
    return result

@app.get("/api/projects/{project_id}/run/status")
async def get_run_status(project_id: str):
    """프로젝트 실행 상태 조회"""
    backend_key = f"{project_id}_backend"
    frontend_key = f"{project_id}_frontend"
    
    return {
        "backend": {
            "running": backend_key in running_processes and running_processes[backend_key]["process"].poll() is None,
            "port": running_processes.get(backend_key, {}).get("port")
        },
        "frontend": {
            "running": frontend_key in running_processes and running_processes[frontend_key]["process"].poll() is None,
            "port": running_processes.get(frontend_key, {}).get("port")
        }
    }

@app.post("/api/projects/{project_id}/run/stop")
async def stop_run(project_id: str):
    """실행 중인 프로젝트 서버 중지"""
    stopped = []
    
    for key in [f"{project_id}_backend", f"{project_id}_frontend"]:
        if key in running_processes:
            try:
                process = running_processes[key]["process"]
                process.terminate()
                process.wait(timeout=5)
                del running_processes[key]
                stopped.append(key.split("_")[-1])
            except Exception as e:
                store.add_log(project_id, "system", f"Failed to stop {key}: {str(e)}", "error")
    
    store.add_log(project_id, "system", f"Stopped servers: {stopped}")
    return {"stopped": stopped}

@app.post("/api/projects/{project_id}/stop")
async def stop_project(project_id: str):
    """워크플로우 중지"""
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    store.update_project(project_id, {"status": "stopped"})
    store.add_log(project_id, "system", "Workflow stopped by user")
    return {"status": "stopped"}

# ==================== WebSocket 로그 스트리밍 ====================

@app.websocket("/ws/projects/{project_id}/logs")
async def websocket_logs(websocket: WebSocket, project_id: str):
    """실시간 로그 스트리밍"""
    await websocket.accept()
    
    if project_id not in store.log_watchers:
        store.log_watchers[project_id] = []
    store.log_watchers[project_id].append(websocket)
    
    try:
        # 기존 로그 전송
        for log in store.get_logs(project_id):
            await websocket.send_json(log)
        
        # 연결 유지
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        if websocket in store.log_watchers.get(project_id, []):
            store.log_watchers[project_id].remove(websocket)

# ==================== 메인 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("DAACS API Server")
    print("=" * 50)
    print(f"Starting on http://localhost:8001")
    print(f"Docs: http://localhost:8001/docs")
    print("=" * 50)
    
    uvicorn.run(
        "daacs_api_server:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Disabled to prevent crash when project files are created
        log_level="info"
    )
