"""
DAACS v6.0 - Replanning Strategies
v5.0 재계획 전략을 v6.0 LangGraph로 마이그레이션
"""

from typing import Dict, List, Optional, Any


class ReplanningStrategies:
    """
    v5.0 재계획 전략을 v6.0 LangGraph로 마이그레이션

    실패 유형에 따라 적절한 next_actions를 제안
    """

    # 실패 유형 → 재계획 전략 매핑
    STRATEGIES = {
        "permission_denied": {
            "stop": True,
            "reason": "Permission error - requires manual intervention",
            "next_actions": [],
            "severity": "critical"
        },

        "tests_fail": {
            "stop": False,
            "reason": "Tests failed - retrying with verbose mode",
            "next_actions": [
                {"type": "test", "cmd": "pytest -v --tb=short", "client": "backend"},
                {"type": "shell", "cmd": "cat pytest.log", "client": "backend"}
            ],
            "severity": "medium"
        },

        "lint_fail": {
            "stop": False,
            "reason": "Lint errors - attempting auto-fix",
            "next_actions": [
                {"type": "lint", "cmd": "autopep8 --in-place --recursive .", "client": "backend"},
                {"type": "lint", "cmd": "black . --check", "client": "backend"},
                {"type": "lint", "cmd": "flake8 --count --statistics", "client": "backend"}
            ],
            "severity": "low"
        },

        "build_fail": {
            "stop": False,
            "reason": "Build failed - checking dependencies",
            "next_actions": [
                {"type": "shell", "cmd": "pip install --upgrade pip", "client": "backend"},
                {"type": "shell", "cmd": "pip install -r requirements.txt", "client": "backend"},
                {"type": "build", "cmd": "python setup.py build", "client": "backend"}
            ],
            "severity": "high"
        },

        "deploy_fail": {
            "stop": False,
            "reason": "Deployment failed - checking configuration",
            "next_actions": [
                {"type": "shell", "cmd": "docker build -t app . --no-cache", "client": "backend"},
                {"type": "deploy", "cmd": "docker run -p 8080:8080 app", "client": "backend"}
            ],
            "severity": "high"
        },

        "codegen_fail": {
            "stop": False,
            "reason": "Code generation incomplete - regenerating",
            "next_actions": [
                {"type": "codegen", "cmd": "Regenerate missing files with more details", "client": "backend"}
            ],
            "severity": "medium"
        },

        "refactor_fail": {
            "stop": False,
            "reason": "Refactoring broke tests - reverting",
            "next_actions": [
                {"type": "shell", "cmd": "git checkout HEAD -- .", "client": "backend"},
                {"type": "test", "cmd": "pytest", "client": "backend"}
            ],
            "severity": "high"
        },

        "verify_fail": {
            "stop": False,
            "reason": "Generic verification failure - retrying",
            "next_actions": [],
            "severity": "low"
        },
    }

    @staticmethod
    def get_strategy(failure_type: Optional[str]) -> Dict[str, Any]:
        """
        실패 유형에 맞는 전략 반환

        Args:
            failure_type: 실패 유형 (permission_denied, tests_fail, etc)

        Returns:
            재계획 전략 딕셔너리
        """
        if not failure_type:
            return {
                "stop": False,
                "reason": "Unknown failure - generic retry",
                "next_actions": [],
                "severity": "low"
            }

        return ReplanningStrategies.STRATEGIES.get(
            failure_type,
            {
                "stop": False,
                "reason": f"Unknown failure type: {failure_type}",
                "next_actions": [],
                "severity": "medium"
            }
        )

    @staticmethod
    def should_stop(
        failure_type: Optional[str],
        consecutive_failures: int,
        max_failures: int
    ) -> bool:
        """
        재계획을 중단해야 하는지 판단

        Args:
            failure_type: 실패 유형
            consecutive_failures: 연속 실패 횟수
            max_failures: 최대 실패 허용 횟수

        Returns:
            True if should stop, False otherwise
        """
        # 1. 권한 오류 → 즉시 중단
        strategy = ReplanningStrategies.get_strategy(failure_type)
        if strategy["stop"]:
            return True

        # 2. 연속 실패 상한 도달
        if consecutive_failures >= max_failures:
            return True

        # 3. 치명적 오류 (severity=critical)
        if strategy.get("severity") == "critical":
            return True

        return False

    @staticmethod
    def create_replan_response(
        failure_type: Optional[str],
        current_goal: str,
        consecutive_failures: int,
        max_failures: int,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        재계획 응답 생성

        Args:
            failure_type: 실패 유형
            current_goal: 현재 목표
            consecutive_failures: 연속 실패 횟수
            max_failures: 최대 실패 허용 횟수
            context: 추가 컨텍스트 (실패 상세 내용 등)

        Returns:
            재계획 응답 딕셔너리
        """
        strategy = ReplanningStrategies.get_strategy(failure_type)

        # 중단 여부 판단
        should_stop = ReplanningStrategies.should_stop(
            failure_type,
            consecutive_failures,
            max_failures
        )

        if should_stop:
            return {
                "stop": True,
                "reason": strategy["reason"],
                "next_goal": None,
                "next_actions": [],
                "needs_rework": False
            }

        # 재계획 계속
        return {
            "stop": False,
            "reason": strategy["reason"],
            "next_goal": current_goal,  # 목표는 유지
            "next_actions": strategy["next_actions"],
            "needs_rework": True,
            "severity": strategy.get("severity", "medium")
        }


def detect_failure_type(
    failure_summary: List[str],
    result: str
) -> Optional[str]:
    """
    실패 요약과 결과에서 실패 유형 감지

    Args:
        failure_summary: 실패 이유 목록
        result: 실행 결과 문자열

    Returns:
        감지된 실패 유형
    """
    # 권한 오류 패턴
    if any("permission" in s.lower() or "Operation not permitted" in s for s in failure_summary):
        return "permission_denied"
    if "rollout recorder" in result or "Operation not permitted" in result:
        return "permission_denied"

    # 테스트 실패
    if any("tests" in s.lower() or "FAILED" in s for s in failure_summary):
        return "tests_fail"

    # 린트 실패
    if any("lint" in s.lower() for s in failure_summary):
        return "lint_fail"

    # 빌드 실패
    if any("build" in s.lower() for s in failure_summary):
        return "build_fail"

    # 배포 실패
    if any("deploy" in s.lower() for s in failure_summary):
        return "deploy_fail"

    # 코드 생성 실패
    if any("missing files" in s.lower() or "empty files" in s.lower() for s in failure_summary):
        return "codegen_fail"

    # 리팩토링 실패
    if any("refactor" in s.lower() for s in failure_summary):
        return "refactor_fail"

    # 일반 검증 실패
    return "verify_fail"


# 사용 예시
if __name__ == "__main__":
    print("=== Replanning Strategies Test ===\n")

    # 예시 1: 테스트 실패
    print("1. Test failure:")
    response = ReplanningStrategies.create_replan_response(
        failure_type="tests_fail",
        current_goal="Create TODO app",
        consecutive_failures=1,
        max_failures=5
    )
    print(f"   Stop: {response['stop']}")
    print(f"   Reason: {response['reason']}")
    print(f"   Next Actions: {len(response['next_actions'])}")

    # 예시 2: 권한 오류
    print("\n2. Permission error:")
    response = ReplanningStrategies.create_replan_response(
        failure_type="permission_denied",
        current_goal="Create TODO app",
        consecutive_failures=1,
        max_failures=5
    )
    print(f"   Stop: {response['stop']}")
    print(f"   Reason: {response['reason']}")

    # 예시 3: 연속 실패 상한
    print("\n3. Max failures reached:")
    response = ReplanningStrategies.create_replan_response(
        failure_type="tests_fail",
        current_goal="Create TODO app",
        consecutive_failures=5,
        max_failures=5
    )
    print(f"   Stop: {response['stop']}")
    print(f"   Reason: {response['reason']}")

    # 예시 4: 실패 유형 감지
    print("\n4. Failure type detection:")
    failure_summary = ["Tests failed - check output", "Missing files: main.py"]
    failure_type = detect_failure_type(failure_summary, "")
    print(f"   Detected: {failure_type}")

    print("\n[OK] Replanning strategies working correctly!")
