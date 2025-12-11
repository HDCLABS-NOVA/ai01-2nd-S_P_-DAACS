/**
 * DAACS API Client
 * Nova-Canvas에서 DAACS API 서버를 호출하기 위한 클라이언트
 * Vite proxy를 통해 /api → localhost:8001로 프록시됨
 */

export interface Project {
    id: string;
    goal: string;
    status: "created" | "planning" | "running" | "completed" | "failed" | "stopped";
    created_at: string;
    iteration: number;
    needs_backend: boolean;
    needs_frontend: boolean;
    plan: string;
}

export interface LogEntry {
    timestamp: string;
    node: string;
    message: string;
    level: string;
}

export interface ProjectFiles {
    backend_files: string[];
    frontend_files: string[];
}

export interface ProjectConfig {
    orchestrator_model?: string;
    backend_model?: string;
    frontend_model?: string;
    max_iterations?: number;
}

// 프로젝트 생성
export async function createProject(goal: string, config?: ProjectConfig): Promise<Project> {
    const response = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal, config }),
    });

    if (!response.ok) {
        throw new Error("Failed to create project");
    }

    return response.json();
}

// 프로젝트 목록 조회
export async function listProjects(): Promise<Project[]> {
    const response = await fetch("/api/projects");
    if (!response.ok) {
        throw new Error("Failed to fetch projects");
    }
    return response.json();
}

// 프로젝트 상태 조회
export async function getProject(projectId: string): Promise<Project> {
    const response = await fetch(`/api/projects/${projectId}`);
    if (!response.ok) {
        throw new Error("Failed to fetch project");
    }
    return response.json();
}

// 프로젝트 로그 조회
export async function getProjectLogs(projectId: string): Promise<LogEntry[]> {
    const response = await fetch(`/api/projects/${projectId}/logs`);
    if (!response.ok) {
        throw new Error("Failed to fetch logs");
    }
    return response.json();
}

// 프로젝트 파일 목록 조회
export async function getProjectFiles(projectId: string): Promise<ProjectFiles> {
    const response = await fetch(`/api/projects/${projectId}/files`);
    if (!response.ok) {
        throw new Error("Failed to fetch files");
    }
    return response.json();
}

// 파일 내용 조회
export async function getFileContent(projectId: string, file: string, type: "backend" | "frontend"): Promise<string> {
    const response = await fetch(`/api/projects/${projectId}/files/content?file=${encodeURIComponent(file)}&type=${type}`);
    if (!response.ok) {
        throw new Error("Failed to fetch file content");
    }
    const data = await response.json();
    return data.content;
}

// 프로젝트 중지
export async function stopProject(projectId: string): Promise<void> {
    const response = await fetch(`/api/projects/${projectId}/stop`, {
        method: "POST",
    });
    if (!response.ok) {
        throw new Error("Failed to stop project");
    }
}

// ==================== 프로젝트 실행 API ====================

export interface RunStatus {
    backend: { running: boolean; port: number | null };
    frontend: { running: boolean; port: number | null };
}

export interface RunResult {
    backend_port: number | null;
    frontend_port: number | null;
    status: string;
}

// 프로젝트 실행
export async function runProject(projectId: string): Promise<RunResult> {
    const response = await fetch(`/api/projects/${projectId}/run`, {
        method: "POST",
    });
    if (!response.ok) {
        throw new Error("Failed to run project");
    }
    return response.json();
}

// 프로젝트 실행 상태 조회
export async function getRunStatus(projectId: string): Promise<RunStatus> {
    const response = await fetch(`/api/projects/${projectId}/run/status`);
    if (!response.ok) {
        throw new Error("Failed to get run status");
    }
    return response.json();
}

// 프로젝트 실행 중지
export async function stopRun(projectId: string): Promise<void> {
    const response = await fetch(`/api/projects/${projectId}/run/stop`, {
        method: "POST",
    });
    if (!response.ok) {
        throw new Error("Failed to stop run");
    }
}

// WebSocket 로그 스트리밍 연결
export function connectToLogs(
    projectId: string,
    onLog: (log: LogEntry) => void,
    onError?: (error: Event) => void
): WebSocket {
    // Use relative WebSocket path (proxied by Vite)
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/projects/${projectId}/logs`);

    ws.onmessage = (event) => {
        try {
            const log = JSON.parse(event.data);
            onLog(log);
        } catch (e) {
            console.error("Failed to parse log:", e);
        }
    };

    ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        if (onError) onError(error);
    };

    return ws;
}

// 파일 내용 업데이트 (저장)
export async function updateFileContent(
    projectId: string,
    file: string,
    type: "backend" | "frontend",
    content: string
): Promise<void> {
    const response = await fetch(`/api/projects/${projectId}/files?file=${encodeURIComponent(file)}&type=${type}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
    });
    if (!response.ok) {
        throw new Error("Failed to update file");
    }
}

// 프로젝트 다운로드 (ZIP)
export async function downloadProject(projectId: string): Promise<void> {
    const response = await fetch(`/api/projects/${projectId}/download`);
    if (!response.ok) {
        throw new Error("Failed to download project");
    }

    // Blob으로 다운로드
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `project_${projectId}.zip`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}



