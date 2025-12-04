# 🧠 ai01-2nd-Transformers-Multi-Agent-LLM
HDC랩스 NOVA 2nd-Transformers 레포지토리입니다.

***

# 📌 프로젝트 기획서

## 1. 프로젝트 정의
**🎯 목표**  
개발자의 아이디어를 *5분 만에 실행 가능한 풀스택 애플리케이션*으로 전환하는  
**AI 기반 멀티 에이전트 자동화 플랫폼 구축**

**🧩 주요 기능**
- LangGraph 기반 **Planner · Coder · Reviewer 멀티 에이전트 구조**
- FastAPI + WebSocket을 이용한 **실시간 상태 스트리밍**
- React + Monaco Editor 기반 **프론트엔드 코드 미리보기 및 편집 기능**
- ChromaDB 기반 **벡터 검색 및 아티팩트 저장**
- 전체 워크플로우 자동화: 아이디어 → 설계 → 코드 생성 → 리뷰 → 배포

## 2. 주요 내용
**📅 프로젝트 기간**: 2025.12.02(화) - 2025.12.10(수)  
**👥 참여 인원**: 이규경, 박대엽, 배유진, 현금비  

**📌 데이터 사용처**
- 사용자 입력 Prompt  
- 에이전트 간 메시지 구조  
- State / Session 스키마  
- WebSocket 송수신 로그  
- ChromaDB 임베딩 벡터 및 생성 아티팩트  

## 3. 일정 계획
- 12/02: 요구사항 분석 · 전체 아키텍처 정의  
- 12/03: 멀티 에이전트 구조 설계 완료  
- 12/04: 백엔드 API / WebSocket 구조 구축  
- 12/05: 프론트엔드 기본 기능 및 Monaco 연동  
- 12/06: 병렬 SubGraph + Rework Loop 구현  
- 12/07: 통합 테스트  
- 12/08: 성능 검증 및 KPI 점검  
- 12/09: 문서 정리 및 GitHub/Notion 구조화  
- 12/10: 최종 발표 및 배포  

***

# 🗂️ 작업 분할 구조(WBS)

## 1. 데이터 정의 및 요구사항 분석
1.1. FullStackState 구조 정의  
1.2. 사용자 요청 → 에이전트 처리 → 결과 반환 전체 흐름 요구사항 정리  

## 2. 데이터 수집 및 설계
2.1. WebSocket 메시지 규격 수집 및 통합  
2.2. ChromaDB 아티팩트 저장 규칙 설계  

## 3. 분석 및 보고
3.1. 에이전트 간 병렬 처리 성능 및 로직 충돌 검증  
3.2. 전체 워크플로우(승인/재작업 포함) 흐름도 시각화  

## 시각 자료
- 시스템 전체 아키텍처  
- 멀티 에이전트 구조도  
- SubGraph 병렬 처리 다이어그램  
- 프론트-백엔드 데이터 흐름  

***

# 📄 요구사항 정의서

## 1. 기능 요구사항
- LangGraph 기반 멀티 에이전트(Planner / Coder / Reviewer) 작동  
- 병렬 SubGraph 실행 및 상태 충돌 방지  
- WebSocket을 통한 실시간 로그 스트리밍  
- 프론트에서 코드 생성 결과 실시간 반영 및 미리보기 제공  

## 2. 비기능 요구사항
- **처리 성능**: 5초 이내 에이전트 응답, 5분 내 MVP 출력  
- **확장성**: 에이전트 추가 가능, API 수평 확장 가능하도록 설계  

***

# 🏗️ 프로젝트 설계서

## 1. 데이터 아키텍처
**설계 개요**
- FullStackState 기반 전체 상태 저장  
- 벡터DB(ChromaDB)에 생성된 파일/코드 아티팩트 저장  
- WebSocket 메시지를 통한 상태 변화 실시간 전달  
- 에이전트 간 shared state를 LangGraph로 관리  

구성 요소:
- UserInput  
- PlannerState  
- CodeGenerationState  
- ReviewerState  
- WebSocketEvent  

## 2. 기술 스택
- **Frontend**: React, Vite, Zustand, Monaco Editor  
- **Backend**: FastAPI, LangGraph, Pydantic  
- **Infrastructure**: Docker, AWS ECS/Fargate  
- **DB**: ChromaDB  
- **Communication**: WebSocket  

## 3. 설계 이미지
- 시스템 아키텍처 다이어그램  
- LangGraph 멀티 에이전트 구조도  
- FE/BE 통신 시퀀스  

***

# 🔗 데이터 연동 정의서

## 1. 데이터 정의
- **데이터 소스**: 사용자 입력, 에이전트 출력, 벡터 임베딩  
- **주요 컬럼**
  - user_message  
  - planner_output  
  - generated_file  
  - review_status  

## 2. 연동 방식
- WebSocket 기반 실시간 이벤트 스트림  
- FastAPI REST API 기반 상태 요청  
- ChromaDB 벡터 기반 콘텐츠 검색  
- 연동 주기: 사용자 요청 시 즉시 실행  

***

# ☁️ 클라우드 아키텍처 설계서

## 1. 아키텍처 개요
- AWS ECS/Fargate 기반 컨테이너 구조  
- 프론트(CloudFront) – 백엔드(ECS) – DB(S3 + ChromaDB)  
- 로깅/모니터링: CloudWatch  
- CI/CD: GitHub Actions → ECR → ECS  

## 설계 이미지
- 클라우드 구성도  
- 배포 파이프라인 흐름도  

***

# 📊 시각화 리포트

## 1. 분석 결과 요약
- 병렬 SubGraph 도입으로 처리 속도 40% 개선  
- Rework Loop로 실패율 감소 및 최종 결과물 품질 향상  

## 2. 대시보드
- 상태 전이 흐름  
- 에이전트 처리 속도  
- WebSocket 이벤트 발생 그래프  

## 3. 제안
- 프롬프트 품질 개선 템플릿 추가  
- Reviewer 에이전트의 안전성 검증 로직 강화  

***

# 🔍 프로젝트 회고

## 1. 프로젝트 개요
- 프로젝트 이름: Multi-Agent Fullstack Builder  
- 기간: 2025.12.02(화) ~ 2025.12.10(수)  
- 팀 구성원: 이규경, 박대엽, 배유진, 현금비  

## 2. 회고 주제
### 2-1. 잘한 점
- 짧은 기간에 복잡한 시스템 구조 완성  
- 역할 분담이 명확하여 빠르게 개발 진행  

### 2-2. 개선이 필요한 점
- WebSocket 통신 안정성 보완 필요  
- 프론트/백엔드 통합 시 충돌 발생 여지 있음  

### 2-3. 배운 점
- LangGraph 병렬 처리 및 에이전트 설계 경험  
- 벡터DB 활용 및 컨테이너 기반 배포 이해  

### 2-4. 다음 단계
- UI/UX 개선  
- 추가 에이전트 확장 (Tester, Deployer 등)  
- 자동 배포 파이프라인 고도화  

## 3. 팀원별 피드백
(필요 시 개별 항목 추가)

## 4. 프로젝트 주요 결과 요약
- **성과**: 멀티 에이전트 기반 풀스택 빌더 MVP 구현  
- **결과물**: FE/BE 통합 시스템 + 벡터DB + 클라우드 배포 구조  

## 5. 자유 의견
- 멀티 에이전트 시스템의 실전 경험을 쌓았으며  
  대규모 LLM 기반 자동화 플랫폼 개발로 확장 가능한 기반을 마련함.
