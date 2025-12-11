import { useLocation } from "wouter";
import type { Project } from "@shared/schema";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserMenu } from "@/components/UserMenu";
import { Button } from "@/components/ui/button";
import { Sparkles, ChevronLeft, Share2 } from "lucide-react";

interface WorkspaceHeaderProps {
  project: Project;
}

export function WorkspaceHeader({ project }: WorkspaceHeaderProps) {
  const [, setLocation] = useLocation();

  return (
    <header className="h-14 flex items-center justify-between gap-4 px-4 border-b border-border/50 bg-background shrink-0">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setLocation("/")}
          data-testid="button-back-home"
        >
          <ChevronLeft className="w-5 h-5" />
        </Button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-primary-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold truncate max-w-[200px] md:max-w-[300px]">
              {project.name}
            </span>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {project.llmModel && <span>{project.llmModel}</span>}
              {project.llmModel && project.developmentArea && <span>·</span>}
              {project.developmentArea && <span>{project.developmentArea}</span>}
            </div>
          </div>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" className="gap-2" data-testid="button-share">
          <Share2 className="w-4 h-4" />
          <span className="hidden sm:inline">공유</span>
        </Button>
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
