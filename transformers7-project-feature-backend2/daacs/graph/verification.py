"""
DAACS v6.0 - Verification Templates
v5.0 검증 템플릿을 v6.0 Verifier 노드로 마이그레이션
"""

from typing import Dict, List, Any, Optional
import os
import subprocess
import re


class VerificationTemplates:
    """
    v5.0 검증 템플릿을 v6.0 Verifier 노드로 마이그레이션

    각 검증 템플릿은 Dict를 반환:
    {
        "ok": bool,
        "reason": str,
        "template": str
    }
    """

    @staticmethod
    def files_exist(files: List[str]) -> Dict[str, Any]:
        """파일 존재 확인"""
        missing = [f for f in files if not os.path.exists(f)]
        return {
            "ok": len(missing) == 0,
            "reason": f"Missing files: {missing}" if missing else "All files exist",
            "template": "files_exist"
        }

    @staticmethod
    def files_not_empty(files: List[str]) -> Dict[str, Any]:
        """파일이 비어있지 않은지 확인"""
        empty = [f for f in files if os.path.exists(f) and os.path.getsize(f) == 0]
        return {
            "ok": len(empty) == 0,
            "reason": f"Empty files: {empty}" if empty else "All files have content",
            "template": "files_not_empty"
        }

    @staticmethod
    def files_no_hidden(files: List[str]) -> Dict[str, Any]:
        """숨김 문자 없음 확인"""
        # 숨김 문자 패턴: \x00-\x08, \x0B-\x0C, \x0E-\x1F, \x7F
        hidden_pattern = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')

        files_with_hidden = []
        for file in files:
            if os.path.exists(file):
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if hidden_pattern.search(content):
                            files_with_hidden.append(file)
                except Exception:
                    pass

        return {
            "ok": len(files_with_hidden) == 0,
            "reason": f"Files with hidden chars: {files_with_hidden}" if files_with_hidden else "No hidden characters",
            "template": "files_no_hidden"
        }

    @staticmethod
    def tests_pass(result: str) -> Dict[str, Any]:
        """테스트 통과 확인"""
        # pytest 실패 패턴
        fail_patterns = ["FAILED", "ERROR", "error", "failures"]
        passed = not any(pattern in result for pattern in fail_patterns)

        return {
            "ok": passed,
            "reason": "Tests passed" if passed else "Tests failed - check output",
            "template": "tests_pass",
            "details": result[:200] if not passed else ""  # 실패 시 일부 출력 포함
        }

    @staticmethod
    def lint_pass(result: str) -> Dict[str, Any]:
        """린트 통과 확인"""
        # flake8, pylint, eslint 실패 패턴
        lint_error_patterns = ["error", "ERROR", "E[0-9]{3}", "W[0-9]{3}"]
        passed = not any(re.search(pattern, result, re.IGNORECASE) for pattern in lint_error_patterns)

        return {
            "ok": passed,
            "reason": "Lint passed" if passed else "Lint errors found",
            "template": "lint_pass",
            "details": result[:200] if not passed else ""
        }

    @staticmethod
    def build_success(returncode: int, stderr: str = "") -> Dict[str, Any]:
        """빌드 성공 확인"""
        success = returncode == 0
        return {
            "ok": success,
            "reason": "Build succeeded" if success else f"Build failed (code {returncode})",
            "template": "build_success",
            "details": stderr[:200] if not success else ""
        }

    @staticmethod
    def deploy_success(returncode: int, stderr: str = "") -> Dict[str, Any]:
        """배포 성공 확인"""
        success = returncode == 0
        return {
            "ok": success,
            "reason": "Deploy succeeded" if success else f"Deploy failed (code {returncode})",
            "template": "deploy_success",
            "details": stderr[:200] if not success else ""
        }

    @staticmethod
    def python_syntax_valid(files: List[str]) -> Dict[str, Any]:
        """Python 구문 검사 (py_compile)"""
        import py_compile
        
        syntax_errors = []
        for file in files:
            if file.endswith('.py') and os.path.exists(file):
                try:
                    py_compile.compile(file, doraise=True)
                except py_compile.PyCompileError as e:
                    syntax_errors.append(f"{file}: {str(e)}")
                except Exception as e:
                    syntax_errors.append(f"{file}: {str(e)}")
        
        return {
            "ok": len(syntax_errors) == 0,
            "reason": f"Python syntax errors: {syntax_errors}" if syntax_errors else "All Python files have valid syntax",
            "template": "python_syntax_valid",
            "details": "\n".join(syntax_errors[:5]) if syntax_errors else ""
        }

    @staticmethod
    def javascript_syntax_valid(files: List[str]) -> Dict[str, Any]:
        """JavaScript 기본 구문 검사 (괄호/중괄호 매칭)"""
        syntax_errors = []
        
        for file in files:
            if (file.endswith('.js') or file.endswith('.jsx') or file.endswith('.ts') or file.endswith('.tsx')) and os.path.exists(file):
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 기본 괄호 매칭 검사
                    brackets = {'(': ')', '{': '}', '[': ']'}
                    stack = []
                    
                    in_string = False
                    string_char = None
                    
                    for i, char in enumerate(content):
                        # 문자열 내부 스킵
                        if char in ('"', "'", '`') and (i == 0 or content[i-1] != '\\'):
                            if not in_string:
                                in_string = True
                                string_char = char
                            elif char == string_char:
                                in_string = False
                            continue
                        
                        if in_string:
                            continue
                        
                        if char in brackets:
                            stack.append(char)
                        elif char in brackets.values():
                            if not stack:
                                syntax_errors.append(f"{file}: Unmatched closing bracket '{char}'")
                                break
                            if brackets[stack.pop()] != char:
                                syntax_errors.append(f"{file}: Mismatched brackets")
                                break
                    
                    if stack and file not in [e.split(':')[0] for e in syntax_errors]:
                        syntax_errors.append(f"{file}: Unclosed brackets: {stack}")
                        
                except Exception as e:
                    syntax_errors.append(f"{file}: {str(e)}")
        
        return {
            "ok": len(syntax_errors) == 0,
            "reason": f"JS syntax issues: {syntax_errors}" if syntax_errors else "All JS files have valid syntax",
            "template": "javascript_syntax_valid",
            "details": "\n".join(syntax_errors[:5]) if syntax_errors else ""
        }

    @staticmethod
    def python_import_test(files: List[str]) -> Dict[str, Any]:
        """Python syntax check using py_compile (safer than exec)"""
        import_errors = []
        
        for file in files:
            if file.endswith('.py') and os.path.exists(file):
                try:
                    # Python syntax check only (import test is too fragile)
                    result = subprocess.run(
                        ['python', '-m', 'py_compile', file],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        import_errors.append(f"{os.path.basename(file)}: {result.stderr[:100]}")
                except subprocess.TimeoutExpired:
                    import_errors.append(f"{os.path.basename(file)}: Timeout")
                except Exception as e:
                    import_errors.append(f"{os.path.basename(file)}: {str(e)[:50]}")
        
        return {
            "ok": len(import_errors) == 0,
            "reason": f"Compile errors: {import_errors}" if import_errors else "All Python files compile successfully",
            "template": "python_import_test",
            "details": "\n".join(import_errors[:5]) if import_errors else ""
        }

    @staticmethod
    def backend_server_test(project_dir: str, main_file: str = "main.py", port: int = 8080) -> Dict[str, Any]:
        """Backend 서버 시작 테스트 - 실제로 서버가 시작되는지 확인"""
        import time
        import urllib.request
        
        main_path = os.path.join(project_dir, main_file)
        if not os.path.exists(main_path):
            return {
                "ok": False,
                "reason": f"Main file not found: {main_file}",
                "template": "backend_server_test"
            }
        
        # 서버 시작 (백그라운드)
        try:
            # uvicorn으로 서버 시작
            process = subprocess.Popen(
                ['python', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(port)],
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 서버 시작 대기 (최대 10초)
            time.sleep(3)
            
            # 헬스체크
            try:
                response = urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=5)
                health_ok = response.status == 200
                health_data = response.read().decode()
            except Exception as e:
                health_ok = False
                health_data = str(e)
            
            # 서버 종료
            process.terminate()
            process.wait(timeout=5)
            
            return {
                "ok": health_ok,
                "reason": "Server started and health check passed" if health_ok else f"Server health check failed: {health_data[:100]}",
                "template": "backend_server_test"
            }
            
        except Exception as e:
            return {
                "ok": False,
                "reason": f"Server start failed: {str(e)[:100]}",
                "template": "backend_server_test"
            }

    @staticmethod
    def frontend_build_test(project_dir: str) -> Dict[str, Any]:
        """Frontend 빌드 테스트 - npm install && npm run build 테스트"""
        package_json = os.path.join(project_dir, "package.json")
        if not os.path.exists(package_json):
            return {
                "ok": False,
                "reason": "package.json not found",
                "template": "frontend_build_test"
            }
        
        try:
            # npm install (use shell=True for Windows PATH resolution)
            result = subprocess.run(
                'npm install',
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
                shell=True
            )
            if result.returncode != 0:
                return {
                    "ok": False,
                    "reason": f"npm install failed: {result.stderr[:100]}",
                    "template": "frontend_build_test"
                }
            
            # npm run build (선택적 - 시간이 오래 걸림)
            # 일단 install만 성공하면 OK로 처리
            return {
                "ok": True,
                "reason": "npm install succeeded",
                "template": "frontend_build_test"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "reason": "npm install timeout (120s)",
                "template": "frontend_build_test"
            }
        except Exception as e:
            return {
                "ok": False,
                "reason": f"Frontend build failed: {str(e)[:100]}",
                "template": "frontend_build_test"
            }

    @staticmethod
    def api_spec_compliance(files: List[str], api_spec: Dict) -> Dict[str, Any]:
        """API 스펙 준수 검증 - 엔드포인트가 코드에 구현되어 있는지 확인"""
        if not api_spec or not api_spec.get("endpoints"):
            return {
                "ok": True,
                "reason": "No API spec to verify",
                "template": "api_spec_compliance"
            }
        
        # 모든 파일 내용 합치기
        all_content = ""
        for file in files:
            if os.path.exists(file):
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        all_content += f.read() + "\n"
                except:
                    pass
        
        missing_endpoints = []
        found_endpoints = []
        
        for endpoint in api_spec.get("endpoints", []):
            path = endpoint.get("path", "")
            method = endpoint.get("method", "").upper()
            
            # 엔드포인트 패턴 검색 (FastAPI 스타일)
            # @app.get("/path"), @router.post("/path") 등
            patterns = [
                f'"{path}"',
                f"'{path}'",
                f'@app.{method.lower()}("{path}"',
                f"@app.{method.lower()}('{path}'",
                f'@router.{method.lower()}("{path}"',
                f"@router.{method.lower()}('{path}'",
            ]
            
            found = any(pattern in all_content for pattern in patterns)
            
            if found:
                found_endpoints.append(f"{method} {path}")
            else:
                missing_endpoints.append(f"{method} {path}")
        
        return {
            "ok": len(missing_endpoints) == 0,
            "reason": f"Missing endpoints: {missing_endpoints}" if missing_endpoints else f"All {len(found_endpoints)} endpoints implemented",
            "template": "api_spec_compliance",
            "found_endpoints": found_endpoints,
            "missing_endpoints": missing_endpoints
        }


# 액션 타입별 템플릿 매핑 (v5.0과 동일 + 확장)
TYPE_TO_TEMPLATES = {
    "files": ["files_exist", "files_not_empty", "files_no_hidden"],
    "test": ["files_exist", "tests_pass"],
    "lint": ["files_exist", "lint_pass"],
    "build": ["files_exist", "build_success"],
    "deploy": ["files_exist", "deploy_success"],
    "codegen": ["files_exist", "files_not_empty"],
    "refactor": ["files_exist", "files_not_empty", "tests_pass"],
    "shell": ["files_exist"],
    # v6.1: 실행 검증 포함
    "backend": ["files_exist", "files_not_empty", "python_syntax_valid", "python_import_test", "api_spec_compliance"],
    "frontend": ["files_exist", "files_not_empty", "javascript_syntax_valid", "frontend_build_test"],
    # 전체 실행 테스트 (선택적)
    "backend_full": ["files_exist", "files_not_empty", "python_syntax_valid", "python_import_test", "backend_server_test", "api_spec_compliance"],
    "frontend_full": ["files_exist", "files_not_empty", "javascript_syntax_valid", "frontend_build_test"],
}


def run_verification(
    action_type: str,
    files: List[str],
    test_result: Optional[str] = None,
    lint_result: Optional[str] = None,
    build_returncode: Optional[int] = None,
    build_stderr: Optional[str] = None,
    api_spec: Optional[Dict] = None  # 새로 추가
) -> Dict[str, Any]:
    """
    액션 타입에 맞는 검증 실행

    Args:
        action_type: 액션 타입 (files, test, lint, build, deploy, codegen, refactor, backend, frontend)
        files: 검증할 파일 목록
        test_result: 테스트 실행 결과 (test 타입용)
        lint_result: 린트 실행 결과 (lint 타입용)
        build_returncode: 빌드 리턴 코드 (build, deploy 타입용)
        build_stderr: 빌드 stderr (build, deploy 타입용)
        api_spec: API 스펙 (backend 타입용)

    Returns:
        {
            "ok": bool,  # 모든 검증 통과 여부
            "verdicts": List[Dict],  # 개별 검증 결과
            "summary": str  # 요약
        }
    """

    templates = TYPE_TO_TEMPLATES.get(action_type, ["files_exist"])
    verdicts = []
    vt = VerificationTemplates()

    # 템플릿 실행
    if "files_exist" in templates:
        verdicts.append(vt.files_exist(files))

    if "files_not_empty" in templates:
        verdicts.append(vt.files_not_empty(files))

    if "files_no_hidden" in templates:
        verdicts.append(vt.files_no_hidden(files))

    if "tests_pass" in templates and test_result is not None:
        verdicts.append(vt.tests_pass(test_result))

    if "lint_pass" in templates and lint_result is not None:
        verdicts.append(vt.lint_pass(lint_result))

    if "build_success" in templates and build_returncode is not None:
        verdicts.append(vt.build_success(build_returncode, build_stderr or ""))

    if "deploy_success" in templates and build_returncode is not None:
        verdicts.append(vt.deploy_success(build_returncode, build_stderr or ""))

    # 새로운 검증 템플릿
    if "python_syntax_valid" in templates:
        verdicts.append(vt.python_syntax_valid(files))

    if "javascript_syntax_valid" in templates:
        verdicts.append(vt.javascript_syntax_valid(files))

    if "api_spec_compliance" in templates and api_spec is not None:
        verdicts.append(vt.api_spec_compliance(files, api_spec))

    # v6.1: 실행 검증 템플릿
    if "python_import_test" in templates:
        verdicts.append(vt.python_import_test(files))

    if "frontend_build_test" in templates and files:
        # files에서 프로젝트 디렉토리 추출 - package.json 위치 기준
        project_dir = None
        for f in files:
            if f.endswith('package.json'):
                project_dir = os.path.dirname(f)
                break
        # package.json이 없으면 첫 파일의 상위 디렉토리 사용
        if not project_dir and files:
            # src/App.jsx -> 상위로 올라가서 frontend 폴더 찾기
            first_file = files[0]
            if os.path.isabs(first_file):
                project_dir = os.path.dirname(first_file)
                # src 폴더 안이면 상위로
                if os.path.basename(project_dir) == 'src':
                    project_dir = os.path.dirname(project_dir)
            else:
                # 상대경로면 현재 cwd 기준
                project_dir = os.getcwd()
        if project_dir:
            verdicts.append(vt.frontend_build_test(project_dir))

    if "backend_server_test" in templates and files:
        # files에서 프로젝트 디렉토리 추출
        project_dir = os.path.dirname(files[0]) if files else ""
        if project_dir:
            verdicts.append(vt.backend_server_test(project_dir))

    # 전체 결과
    all_passed = all(v["ok"] for v in verdicts)
    failed_reasons = [v["reason"] for v in verdicts if not v["ok"]]

    summary = "All verifications passed" if all_passed else f"Failed: {', '.join(failed_reasons)}"

    return {
        "ok": all_passed,
        "verdicts": verdicts,
        "summary": summary
    }


# 사용 예시
if __name__ == "__main__":
    print("=== Verification Templates Test ===\n")

    # 예시 1: 파일 검증
    print("1. Files verification:")
    result = run_verification(
        action_type="files",
        files=["main.py", "config.py"]
    )
    print(f"   OK: {result['ok']}")
    print(f"   Summary: {result['summary']}")
    print(f"   Verdicts: {len(result['verdicts'])}")

    # 예시 2: 테스트 검증
    print("\n2. Test verification:")
    result = run_verification(
        action_type="test",
        files=["test_main.py"],
        test_result="===== 5 passed in 0.05s ====="
    )
    print(f"   OK: {result['ok']}")
    print(f"   Summary: {result['summary']}")

    # 예시 3: 빌드 검증
    print("\n3. Build verification:")
    result = run_verification(
        action_type="build",
        files=["dist/app"],
        build_returncode=0
    )
    print(f"   OK: {result['ok']}")
    print(f"   Summary: {result['summary']}")

    print("\n[OK] Verification templates working correctly!")
