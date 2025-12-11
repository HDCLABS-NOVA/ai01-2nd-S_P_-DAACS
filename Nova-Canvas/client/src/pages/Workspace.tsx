import { useState, useEffect, useRef } from "react";
import { useRoute, useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { getProject, getProjectLogs, getProjectFiles, getFileContent, updateFileContent, downloadProject, connectToLogs, runProject, getRunStatus, stopRun, type Project, type LogEntry, type RunStatus } from "@/lib/daacsApi";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ArrowLeft, RefreshCw, Sparkles, FileCode, FolderTree, Activity, CheckCircle, XCircle, Loader2, Code, Play, Square, ExternalLink, Download, Edit, Save } from "lucide-react";

export default function Workspace() {
  const [, params] = useRoute("/workspace/:id");
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const projectId = params?.id || "";

  const [project, setProject] = useState<Project | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [files, setFiles] = useState<{ backend_files: string[]; frontend_files: string[] }>({ backend_files: [], frontend_files: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("files");
  const [folderTab, setFolderTab] = useState<"backend" | "frontend">("backend");
  const [selectedFile, setSelectedFile] = useState<{ name: string; type: "backend" | "frontend"; content: string } | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // 프로젝트 로드 및 WebSocket 연결
  useEffect(() => {
    if (!projectId) return;

    const loadProject = async () => {
      try {
        const data = await getProject(projectId);
        setProject(data);
        setIsLoading(false);
      } catch (error) {
        toast({
          title: "오류",
          description: "프로젝트를 불러올 수 없습니다",
          variant: "destructive",
        });
        setIsLoading(false);
      }
    };

    loadProject();

    // WebSocket 연결
    try {
      wsRef.current = connectToLogs(projectId, (log) => {
        setLogs((prev) => [...prev, log]);
      });
    } catch (error) {
      console.error("WebSocket connection failed:", error);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [projectId, toast]);

  // 주기적으로 프로젝트 상태 업데이트
  useEffect(() => {
    if (!projectId) return;

    const interval = setInterval(async () => {
      try {
        const data = await getProject(projectId);
        setProject(data);

        const filesData = await getProjectFiles(projectId);
        setFiles(filesData);
      } catch (error) {
        console.error("Failed to refresh project:", error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [projectId]);

  // 로그 자동 스크롤
  useEffect(() => {
    if (activeTab === "logs") {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, activeTab]);

  const handleRefresh = async () => {
    try {
      const data = await getProject(projectId);
      setProject(data);

      const logsData = await getProjectLogs(projectId);
      setLogs(logsData);

      const filesData = await getProjectFiles(projectId);
      setFiles(filesData);

      toast({ title: "새로고침 완료", description: "프로젝트 정보가 업데이트되었습니다" });
    } catch (error) {
      toast({ title: "오류", description: "새로고침 실패", variant: "destructive" });
    }
  };

  const handleFileClick = async (file: string, type: "backend" | "frontend") => {
    setFileLoading(true);
    try {
      const content = await getFileContent(projectId, file, type);
      setSelectedFile({ name: file, type, content });
    } catch (error) {
      toast({ title: "오류", description: "파일 내용을 불러올 수 없습니다", variant: "destructive" });
    } finally {
      setFileLoading(false);
    }
  };

  const handleFileSave = async () => {
    if (!selectedFile) return;

    setIsSaving(true);
    try {
      await updateFileContent(projectId, selectedFile.name, selectedFile.type, editedContent);
      setSelectedFile({ ...selectedFile, content: editedContent });
      setIsEditing(false);
      toast({ title: "저장 완료", description: `${selectedFile.name} 파일이 저장되었습니다` });
    } catch (error) {
      toast({ title: "오류", description: "파일 저장 실패", variant: "destructive" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      await downloadProject(projectId);
      toast({ title: "다운로드 시작", description: "프로젝트 ZIP 파일이 다운로드됩니다" });
    } catch (error) {
      toast({ title: "오류", description: "다운로드 실패", variant: "destructive" });
    } finally {
      setIsDownloading(false);
    }
  };

  const currentFiles = folderTab === "backend" ? files.backend_files : files.frontend_files;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-muted-foreground">프로젝트 로딩 중...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-muted-foreground">프로젝트를 찾을 수 없습니다</p>
          <Button onClick={() => setLocation("/")}>홈으로 돌아가기</Button>
        </div>
      </div>
    );
  }

  const getStatusIcon = () => {
    switch (project.status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "failed":
      case "stopped":
        return <XCircle className="w-5 h-5 text-red-500" />;
      case "running":
      case "planning":
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Activity className="w-5 h-5 text-muted-foreground" />;
    }
  };

  const getStatusLabel = () => {
    switch (project.status) {
      case "completed": return "완료";
      case "failed": return "실패";
      case "stopped": return "중지됨";
      case "running": return "실행 중";
      case "planning": return "계획 중";
      case "created": return "생성됨";
      default: return project.status;
    }
  };

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between gap-4 px-6 py-3 border-b border-border/50 shrink-0">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setLocation("/")}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <span className="font-semibold">{project.id}</span>
          </div>
          <div className="flex items-center gap-2">
            {getStatusIcon()}
            <span className="text-sm text-muted-foreground">{getStatusLabel()}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">반복: {project.iteration}</span>
          <Button variant="outline" size="sm" onClick={handleDownload} disabled={isDownloading}>
            {isDownloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
            다운로드
          </Button>
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className="w-4 h-4 mr-2" />
            새로고침
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Project Info + Logs */}
        <div className="w-72 border-r border-border/50 shrink-0 flex flex-col overflow-hidden">
          {/* Project Info - Scrollable */}
          <ScrollArea className="flex-shrink-0 max-h-[40%]">
            <div className="p-4 border-b border-border/50">
              <h3 className="font-semibold mb-2">목표</h3>
              <p className="text-sm text-muted-foreground">{project.goal}</p>
            </div>

            {project.plan && (
              <div className="p-4 border-b border-border/50">
                <h3 className="font-semibold mb-2">계획</h3>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap line-clamp-4">{project.plan}</p>
              </div>
            )}

            <div className="p-4 border-b border-border/50">
              <h3 className="font-semibold mb-3">구성 요소</h3>
              <div className="space-y-2">
                <div className={`flex items-center gap-2 p-2 rounded-lg ${project.needs_backend ? 'bg-green-500/10' : 'bg-muted/50'}`}>
                  <FileCode className="w-4 h-4" />
                  <span className="text-sm">백엔드</span>
                  {project.needs_backend && <CheckCircle className="w-4 h-4 text-green-500 ml-auto" />}
                </div>
                <div className={`flex items-center gap-2 p-2 rounded-lg ${project.needs_frontend ? 'bg-green-500/10' : 'bg-muted/50'}`}>
                  <FolderTree className="w-4 h-4" />
                  <span className="text-sm">프론트엔드</span>
                  {project.needs_frontend && <CheckCircle className="w-4 h-4 text-green-500 ml-auto" />}
                </div>
              </div>
            </div>
          </ScrollArea>

          {/* Real-time Logs - Takes remaining space */}
          <div className="flex-1 flex flex-col overflow-hidden border-t border-border/50">
            <div className="px-4 py-2 flex items-center justify-between bg-muted/30 shrink-0">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary" />
                <h3 className="font-semibold text-sm">실시간 로그</h3>
              </div>
              <span className="text-xs text-muted-foreground">{logs.length}개</span>
            </div>
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-1">
                {logs.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4 text-xs">로그 대기 중...</p>
                ) : (
                  logs.slice(-50).map((log, index) => (
                    <div
                      key={index}
                      className={`p-2 rounded text-xs font-mono ${log.level === 'error' ? 'bg-red-500/10 border-l-2 border-red-500' :
                        log.node === 'orchestrator' ? 'bg-blue-500/5 border-l-2 border-blue-500' :
                          log.node === 'backend' ? 'bg-green-500/5 border-l-2 border-green-500' :
                            log.node === 'frontend' ? 'bg-purple-500/5 border-l-2 border-purple-500' :
                              'bg-muted/30 border-l-2 border-muted'
                        }`}
                    >
                      <div className="flex items-center gap-1 mb-0.5 text-muted-foreground">
                        <span className="text-[10px]">
                          {new Date(log.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        <span className={`text-[10px] ${log.node === 'orchestrator' ? 'text-blue-400' :
                          log.node === 'backend' ? 'text-green-400' :
                            log.node === 'frontend' ? 'text-purple-400' :
                              'text-muted-foreground'
                          }`}>
                          [{log.node}]
                        </span>
                      </div>
                      <p className="text-foreground/80 break-words">{log.message}</p>
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* Right Panel - Tabs (Files, Preview only) */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <Tabs value={activeTab === "logs" ? "files" : activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="w-full justify-start rounded-none border-b border-border/50 bg-transparent px-4 shrink-0">
              <TabsTrigger value="files" className="data-[state=active]:bg-muted">
                <FolderTree className="w-4 h-4 mr-2" />
                파일
              </TabsTrigger>
              <TabsTrigger value="preview" className="data-[state=active]:bg-muted">
                <Play className="w-4 h-4 mr-2" />
                미리보기
              </TabsTrigger>
            </TabsList>


            <TabsContent value="files" className="flex-1 m-0 p-0 overflow-hidden flex flex-col">
              {/* Folder Tabs */}
              <div className="flex border-b border-border/50 px-4 shrink-0">
                <button
                  onClick={() => setFolderTab("backend")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${folderTab === "backend"
                    ? "border-green-500 text-green-500"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                >
                  <FileCode className="w-4 h-4" />
                  백엔드 ({files.backend_files.length})
                </button>
                <button
                  onClick={() => setFolderTab("frontend")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${folderTab === "frontend"
                    ? "border-purple-500 text-purple-500"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                >
                  <FolderTree className="w-4 h-4" />
                  프론트엔드 ({files.frontend_files.length})
                </button>
              </div>

              <div className="flex-1 flex overflow-hidden">
                {/* File List */}
                <div className="w-64 border-r border-border/50 overflow-hidden">
                  <ScrollArea className="h-full">
                    <div className="p-4 space-y-1">
                      {currentFiles.length === 0 ? (
                        <p className="text-muted-foreground text-center py-8 text-sm">파일 없음</p>
                      ) : (
                        currentFiles.map((file, index) => (
                          <button
                            key={index}
                            onClick={() => handleFileClick(file, folderTab)}
                            className={`w-full text-left p-2 rounded text-sm font-mono truncate hover:bg-muted ${selectedFile?.name === file && selectedFile?.type === folderTab ? "bg-muted text-primary" : "text-muted-foreground"
                              }`}
                          >
                            {file}
                          </button>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                </div>

                {/* File Content */}
                <div className="flex-1 flex flex-col overflow-hidden bg-card p-4">
                  {selectedFile ? (
                    <div className="flex-1 flex flex-col overflow-hidden rounded-lg shadow-lg">
                      <div className="px-4 py-2 border-b border-border/50 flex items-center justify-between bg-background shrink-0">
                        <div className="flex items-center gap-2">
                          <Code className="w-4 h-4 text-muted-foreground" />
                          <span className="font-mono text-sm">{selectedFile.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-1 rounded ${selectedFile.type === "backend" ? "bg-green-500/20 text-green-500" : "bg-purple-500/20 text-purple-500"}`}>
                            {selectedFile.type}
                          </span>
                          {isEditing ? (
                            <>
                              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setIsEditing(false)}>
                                <XCircle className="w-4 h-4" />
                              </Button>
                              <Button variant="ghost" size="icon" className="h-6 w-6 text-green-500" onClick={handleFileSave} disabled={isSaving}>
                                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                              </Button>
                            </>
                          ) : (
                            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => {
                              setEditedContent(selectedFile.content);
                              setIsEditing(true);
                            }}>
                              <Edit className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                      {isEditing ? (
                        <textarea
                          className="flex-1 w-full h-full p-4 font-mono text-sm bg-zinc-900 text-zinc-100 resize-none focus:outline-none"
                          value={editedContent}
                          onChange={(e) => setEditedContent(e.target.value)}
                          spellCheck={false}
                        />
                      ) : (
                        <ScrollArea className="flex-1 overflow-auto bg-zinc-900">
                          <pre className="p-4 font-mono text-sm whitespace-pre overflow-x-auto text-zinc-100">
                            <code>{selectedFile.content}</code>
                          </pre>
                        </ScrollArea>
                      )}
                    </div>
                  ) : (
                    <div className="flex-1 flex items-center justify-center text-muted-foreground bg-zinc-900/50 rounded-lg">
                      {fileLoading ? (
                        <Loader2 className="w-6 h-6 animate-spin" />
                      ) : (
                        <div className="text-center space-y-3">
                          <Code className="w-12 h-12 mx-auto opacity-30" />
                          <p className="text-sm">파일을 선택하여 내용을 확인하세요</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="preview" className="flex-1 m-0 p-0 h-full flex flex-col overflow-hidden">
              <div className="flex items-center gap-4 p-4 border-b border-border/50 bg-background">
                <Button
                  onClick={async () => {
                    setIsStarting(true);
                    try {
                      await runProject(projectId);
                      toast({ title: "실행 시작", description: "프로젝트 서버를 시작하고 있습니다..." });
                      // 3초 후 상태 확인
                      setTimeout(async () => {
                        const status = await getRunStatus(projectId);
                        setRunStatus(status);
                        setIsStarting(false);
                      }, 3000);
                    } catch (error) {
                      toast({ title: "오류", description: "프로젝트 실행 실패", variant: "destructive" });
                      setIsStarting(false);
                    }
                  }}
                  disabled={isStarting || (runStatus?.backend?.running || runStatus?.frontend?.running)}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {isStarting ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  실행
                </Button>
                <Button
                  variant="outline"
                  onClick={async () => {
                    try {
                      await stopRun(projectId);
                      setRunStatus(null);
                      toast({ title: "중지됨", description: "프로젝트 서버가 중지되었습니다" });
                    } catch (error) {
                      toast({ title: "오류", description: "중지 실패", variant: "destructive" });
                    }
                  }}
                  disabled={!runStatus?.backend?.running && !runStatus?.frontend?.running}
                >
                  <Square className="w-4 h-4 mr-2" />
                  중지
                </Button>
                <div className="flex-1" />
                <div className="flex items-center gap-3 text-sm">
                  <div className={`flex items-center gap-1 ${runStatus?.backend?.running ? 'text-green-500' : 'text-muted-foreground'}`}>
                    <div className={`w-2 h-2 rounded-full ${runStatus?.backend?.running ? 'bg-green-500' : 'bg-muted'}`} />
                    백엔드 {runStatus?.backend?.port && `(:${runStatus.backend.port})`}
                  </div>
                  <div className={`flex items-center gap-1 ${runStatus?.frontend?.running ? 'text-purple-500' : 'text-muted-foreground'}`}>
                    <div className={`w-2 h-2 rounded-full ${runStatus?.frontend?.running ? 'bg-purple-500' : 'bg-muted'}`} />
                    프론트엔드 {runStatus?.frontend?.port && `(:${runStatus.frontend.port})`}
                  </div>
                </div>
              </div>

              <div className="flex-1 flex p-4">
                {runStatus?.frontend?.running ? (
                  <iframe
                    src={`http://localhost:${runStatus.frontend.port}`}
                    className="flex-1 border-none bg-white rounded-lg shadow-lg"
                    title="프로젝트 미리보기"
                  />
                ) : runStatus?.backend?.running ? (
                  <div className="flex-1 flex items-center justify-center bg-muted/20">
                    <div className="text-center space-y-4 p-8">
                      <CheckCircle className="w-16 h-16 mx-auto text-green-500" />
                      <h3 className="text-lg font-semibold">백엔드 서버 실행 중</h3>
                      <p className="text-sm text-muted-foreground">
                        API 서버가 포트 {runStatus.backend.port}에서 실행 중입니다
                      </p>
                      <a
                        href={`http://localhost:${runStatus.backend.port}/docs`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-primary hover:underline"
                      >
                        <ExternalLink className="w-4 h-4" />
                        API 문서 열기
                      </a>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center bg-zinc-900/80">
                    <div className="text-center space-y-4 p-8">
                      <Play className="w-20 h-20 mx-auto text-zinc-600" />
                      <h3 className="text-xl font-semibold text-zinc-200">프로젝트 실행</h3>
                      <p className="text-sm text-zinc-400 max-w-md">
                        위의 "실행" 버튼을 클릭하면 생성된 프로젝트의 서버가 시작되고<br />
                        여기서 결과를 확인할 수 있습니다.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

