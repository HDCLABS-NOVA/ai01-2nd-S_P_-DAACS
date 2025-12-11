import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Sparkles, ArrowRight, Plus, FolderOpen, Loader2, Zap, Code2, Layers, Settings } from "lucide-react";
import { createProject, listProjects, type Project, type ProjectConfig } from "@/lib/daacsApi";

export default function Home() {
  const [requirement, setRequirement] = useState("");
  const [, setLocation] = useLocation();
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [projectsLoading, setProjectsLoading] = useState(true);

  // 프로젝트 설정 상태
  const [config, setConfig] = useState<ProjectConfig>({
    orchestrator_model: "gpt-5.1-codex-max",
    backend_model: "gpt-5.1-codex-max",
    frontend_model: "gpt-5.1-codex-max",
    max_iterations: 10
  });

  // 프로젝트 목록 로드
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const data = await listProjects();
        setProjects(data);
      } catch (error) {
        console.log("DAACS API not available yet");
      } finally {
        setProjectsLoading(false);
      }
    };
    fetchProjects();
  }, []);

  const handleStart = async () => {
    if (requirement.trim() && !isLoading) {
      setIsLoading(true);
      try {
        const project = await createProject(requirement.trim(), config);
        setLocation(`/workspace/${project.id}`);
      } catch (error) {
        console.error("Failed to create project:", error);
        alert("DAACS API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.");
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && e.metaKey && requirement.trim()) {
      handleStart();
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="flex items-center justify-between gap-4 px-6 py-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <img src="/favicon.png" alt="DAACS" className="w-8 h-8 rounded-md" />
          <span className="text-xl font-semibold tracking-tight">Transformers</span>
        </div>
        <div className="flex items-center gap-3">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" size="icon" title="프로젝트 설정">
                <Settings className="w-4 h-4" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>프로젝트 설정</DialogTitle>
              </DialogHeader>
              <div className="space-y-6 py-4">
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-muted-foreground">AI 모델 설정</h4>

                  <div className="space-y-2">
                    <Label>Orchestrator Model</Label>
                    <Select
                      value={config.orchestrator_model}
                      onValueChange={(val) => setConfig({ ...config, orchestrator_model: val })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gpt-5.1-codex-max">gpt-5.1-codex-max (OpenAI)</SelectItem>
                        <SelectItem value="claude-sonnet-4.5">Claude Sonnet 4.5 (Anthropic)</SelectItem>
                        <SelectItem value="gemini-3-pro-high">Gemini 3 Pro High (Google)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Backend Model</Label>
                    <Select
                      value={config.backend_model}
                      onValueChange={(val) => setConfig({ ...config, backend_model: val })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gpt-5.1-codex-max">gpt-5.1-codex-max (OpenAI)</SelectItem>
                        <SelectItem value="claude-sonnet-4.5">Claude Sonnet 4.5 (Anthropic)</SelectItem>
                        <SelectItem value="gemini-3-pro-high">Gemini 3 Pro High (Google)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Frontend Model</Label>
                    <Select
                      value={config.frontend_model}
                      onValueChange={(val) => setConfig({ ...config, frontend_model: val })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gpt-5.1-codex-max">gpt-5.1-codex-max (OpenAI)</SelectItem>
                        <SelectItem value="claude-sonnet-4.5">Claude Sonnet 4.5 (Anthropic)</SelectItem>
                        <SelectItem value="gemini-3-pro-high">Gemini 3 Pro High (Google)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-4 pt-4 border-t border-border/50">
                  <h4 className="text-sm font-medium text-muted-foreground">실행 설정</h4>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <Label>최대 반복 횟수 (Max Iterations)</Label>
                      <span className="text-sm font-medium bg-muted px-2 py-1 rounded">
                        {config.max_iterations}회
                      </span>
                    </div>
                    <Slider
                      value={[config.max_iterations || 10]}
                      min={1}
                      max={20}
                      step={1}
                      onValueChange={(vals) => setConfig({ ...config, max_iterations: vals[0] })}
                    />
                  </div>
                </div>
              </div>
            </DialogContent>
          </Dialog>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center px-4 py-12">
        <div className="w-full max-w-4xl mx-auto space-y-8">
          {/* Hero Section */}
          <div className="text-center space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-medium">
              <Sparkles className="w-4 h-4" />
              <span>DAACS AI 엔진</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
              아이디어를{" "}
              <span className="bg-gradient-to-r from-primary to-blue-400 bg-clip-text text-transparent">
                현실로
              </span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-xl mx-auto">
              만들고 싶은 것을 자연어로 설명하세요.
              DAACS가 플랜을 세우고, 코드를 생성하고, 함께 개발합니다.
            </p>
          </div>

          {/* Input Area */}
          <div className="relative">
            <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 via-blue-500/20 to-purple-500/20 rounded-xl blur-xl opacity-50" />
            <div className="relative bg-card border border-border rounded-xl p-1">
              <Textarea
                value={requirement}
                onChange={(e) => setRequirement(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="프로젝트를 설명해주세요... 예: 사용자가 할 일 목록을 관리할 수 있는 웹 앱을 만들고 싶어요. 할 일 추가, 삭제, 완료 표시 기능이 필요합니다."
                className="min-h-36 resize-none border-0 text-base focus-visible:ring-0 bg-transparent"
                data-testid="input-new-requirement"
                disabled={isLoading}
              />
              <div className="flex items-center justify-between px-3 py-2 border-t border-border/50">
                <span className="text-xs text-muted-foreground">
                  {requirement.length} 자
                </span>
                <Button
                  onClick={handleStart}
                  disabled={!requirement.trim() || isLoading}
                  className="gap-2"
                  data-testid="button-create-project"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>생성 중...</span>
                    </>
                  ) : (
                    <>
                      <span>시작하기</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* Feature Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
            <FeatureCard
              icon={<Zap className="w-5 h-5" />}
              title="빠른 플랜 생성"
              description="DAACS가 요구사항을 분석하고 개발 플랜을 즉시 제안합니다."
            />
            <FeatureCard
              icon={<Code2 className="w-5 h-5" />}
              title="실시간 코드 생성"
              description="대화를 통해 코드를 생성하고 수정하며 라이브러리에 저장합니다."
            />
            <FeatureCard
              icon={<Layers className="w-5 h-5" />}
              title="통합 워크스페이스"
              description="플랜, 로그, API, 구조를 한 곳에서 관리하고 미리보기로 확인합니다."
            />
          </div>

          {/* Recent Projects */}
          {projects && projects.length > 0 && (
            <div className="space-y-4 pt-4">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-5 h-5 text-muted-foreground" />
                <h2 className="text-lg font-semibold">최근 프로젝트</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {projects.slice(0, 6).map((project) => (
                  <button
                    key={project.id}
                    onClick={() => setLocation(`/workspace/${project.id}`)}
                    className="p-4 rounded-lg bg-card border border-border/50 text-left space-y-2 hover:bg-muted/50 transition-colors"
                    data-testid={`button-project-${project.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium truncate">{project.id}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${project.status === 'completed' ? 'bg-green-500/20 text-green-500' :
                        project.status === 'running' ? 'bg-blue-500/20 text-blue-500' :
                          project.status === 'failed' ? 'bg-red-500/20 text-red-500' :
                            'bg-muted text-muted-foreground'
                        }`}>
                        {project.status}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {project.goal}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>반복: {project.iteration}</span>
                      {project.needs_backend && <span className="px-2 py-0.5 rounded-full bg-muted">Backend</span>}
                      {project.needs_frontend && <span className="px-2 py-0.5 rounded-full bg-muted">Frontend</span>}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {projectsLoading && (
            <div className="space-y-4 pt-4">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-5 h-5 text-muted-foreground" />
                <h2 className="text-lg font-semibold">최근 프로젝트</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2].map((i) => (
                  <div
                    key={i}
                    className="p-4 rounded-lg bg-card border border-border/50 space-y-2 animate-pulse"
                  >
                    <div className="h-5 w-3/4 bg-muted rounded" />
                    <div className="h-4 w-full bg-muted rounded" />
                    <div className="h-4 w-2/3 bg-muted rounded" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="py-6 text-center text-sm text-muted-foreground border-t border-border/50">
        <p>Transformers - AI와 함께하는 개발 협업 플랫폼</p>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="p-4 rounded-lg bg-card border border-border/50 space-y-2 hover:bg-muted/30 transition-colors">
      <div className="w-10 h-10 rounded-md bg-primary/10 flex items-center justify-center text-primary">
        {icon}
      </div>
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
