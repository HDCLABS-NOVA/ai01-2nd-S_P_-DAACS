import { useState } from "react";
import type { Project, Plan, Log, CodeSnippet } from "@shared/schema";
import type { WorkspaceTab } from "@/pages/Workspace";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Clock,
  Plug,
  FolderTree,
  Settings,
  Code2,
  ChevronRight,
  Copy,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface WorkspacePanelProps {
  activeTab: WorkspaceTab;
  setActiveTab: (tab: WorkspaceTab) => void;
  project: Project;
  plans: Plan[];
  logs: Log[];
  codeSnippets: CodeSnippet[];
}

const menuItems: { id: WorkspaceTab; label: string; icon: React.ElementType }[] = [
  { id: "overview", label: "Overview / Plan", icon: FileText },
  { id: "logs", label: "Logs", icon: Clock },
  { id: "api", label: "API", icon: Plug },
  { id: "structure", label: "Structure", icon: FolderTree },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "code-library", label: "Code Library", icon: Code2 },
];

export function WorkspacePanel({
  activeTab,
  setActiveTab,
  project,
  plans,
  logs,
  codeSnippets,
}: WorkspacePanelProps) {
  return (
    <div className="flex-1 flex min-w-[400px] border-r border-border/50">
      <div className="w-56 flex flex-col border-r border-border/50 bg-sidebar shrink-0">
        <div className="h-12 px-4 flex items-center border-b border-border/50">
          <h2 className="text-sm font-semibold">Workspace</h2>
        </div>
        <nav className="flex-1 p-2">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                activeTab === item.id
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover-elevate"
              )}
              data-testid={`tab-${item.id}`}
            >
              <item.icon className="w-4 h-4" />
              <span>{item.label}</span>
              {item.id === "code-library" && codeSnippets.length > 0 && (
                <Badge variant="secondary" className="ml-auto text-xs">
                  {codeSnippets.length}
                </Badge>
              )}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="h-12 px-4 flex items-center border-b border-border/50">
          <h3 className="text-sm font-semibold">
            {menuItems.find((m) => m.id === activeTab)?.label}
          </h3>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-4">
            {activeTab === "overview" && (
              <OverviewContent project={project} plans={plans} />
            )}
            {activeTab === "logs" && <LogsContent logs={logs} />}
            {activeTab === "api" && <ApiContent />}
            {activeTab === "structure" && <StructureContent project={project} />}
            {activeTab === "settings" && <SettingsContent project={project} />}
            {activeTab === "code-library" && (
              <CodeLibraryContent codeSnippets={codeSnippets} />
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}

function OverviewContent({ project, plans }: { project: Project; plans: Plan[] }) {
  const latestPlan = plans.length > 0 ? plans[plans.length - 1] : null;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-muted-foreground">요구사항</h4>
        <p className="text-sm bg-muted/50 p-3 rounded-md">{project.requirement}</p>
      </div>

      {latestPlan ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-muted-foreground">
              개발 플랜 (v{latestPlan.version})
            </h4>
            <Badge variant="outline" className="text-xs">
              {new Date(latestPlan.createdAt!).toLocaleDateString("ko-KR")}
            </Badge>
          </div>
          <div className="text-sm bg-card border border-border/50 p-4 rounded-md whitespace-pre-wrap">
            {latestPlan.content}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">아직 개발 플랜이 없습니다.</p>
          <p className="text-xs mt-1">DAACS와 대화하여 플랜을 생성해보세요.</p>
        </div>
      )}
    </div>
  );
}

function LogsContent({ logs }: { logs: Log[] }) {
  if (logs.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p className="text-sm">아직 로그가 없습니다.</p>
        <p className="text-xs mt-1">활동 기록이 여기에 표시됩니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {logs.map((log) => (
        <div
          key={log.id}
          className="p-3 rounded-md bg-card border border-border/50"
        >
          <div className="flex items-center justify-between mb-2">
            <Badge variant="outline" className="text-xs">
              {log.type}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {new Date(log.createdAt!).toLocaleString("ko-KR")}
            </span>
          </div>
          <p className="text-sm">{log.content}</p>
        </div>
      ))}
    </div>
  );
}

function ApiContent() {
  return (
    <div className="text-center py-8 text-muted-foreground">
      <Plug className="w-12 h-12 mx-auto mb-3 opacity-50" />
      <p className="text-sm">API 엔드포인트</p>
      <p className="text-xs mt-1">프로젝트에서 사용하는 API가 여기에 표시됩니다.</p>
    </div>
  );
}

function StructureContent({ project }: { project: Project }) {
  return (
    <div className="space-y-4">
      <div className="text-sm">
        <div className="flex items-center gap-2 py-1">
          <FolderTree className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">{project.name}</span>
        </div>
        <div className="ml-6 space-y-1 text-muted-foreground">
          <div className="flex items-center gap-2 py-1">
            <ChevronRight className="w-3 h-3" />
            <span>src/</span>
          </div>
          <div className="flex items-center gap-2 py-1">
            <ChevronRight className="w-3 h-3" />
            <span>components/</span>
          </div>
          <div className="flex items-center gap-2 py-1">
            <ChevronRight className="w-3 h-3" />
            <span>pages/</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsContent({ project }: { project: Project }) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">프로젝트 이름</label>
        <p className="text-sm text-muted-foreground">{project.name}</p>
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">LLM 모델</label>
        <p className="text-sm text-muted-foreground">{project.llmModel || "미설정"}</p>
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">개발 영역</label>
        <p className="text-sm text-muted-foreground">{project.developmentArea || "미설정"}</p>
      </div>
    </div>
  );
}

function CodeLibraryContent({ codeSnippets }: { codeSnippets: CodeSnippet[] }) {
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const handleCopy = async (content: string, id: number) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (codeSnippets.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Code2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p className="text-sm">코드 라이브러리가 비어있습니다.</p>
        <p className="text-xs mt-1">DAACS가 생성한 코드가 여기에 저장됩니다.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {codeSnippets.map((snippet) => (
        <div
          key={snippet.id}
          className="p-4 rounded-md bg-card border border-border/50 space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs font-mono">
                {snippet.language}
              </Badge>
              <span className="text-sm font-medium truncate">{snippet.filename}</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleCopy(snippet.content, snippet.id)}
              data-testid={`button-copy-code-${snippet.id}`}
            >
              {copiedId === snippet.id ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </Button>
          </div>
          {snippet.description && (
            <p className="text-xs text-muted-foreground">{snippet.description}</p>
          )}
          <pre className="text-xs font-mono bg-muted/50 p-3 rounded overflow-x-auto">
            <code className="line-clamp-4">{snippet.content}</code>
          </pre>
        </div>
      ))}
    </div>
  );
}
