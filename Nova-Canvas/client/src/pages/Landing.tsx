import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Sparkles, ArrowRight, Zap, Code2, Layers } from "lucide-react";

export default function Landing() {
  const [requirement, setRequirement] = useState("");
  const [, setLocation] = useLocation();

  const handleStart = () => {
    if (requirement.trim()) {
      sessionStorage.setItem("initialRequirement", requirement.trim());
      window.location.href = "/api/login";
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
          <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-semibold tracking-tight">Transformers</span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button
            variant="outline"
            onClick={() => (window.location.href = "/api/login")}
            data-testid="button-login-header"
          >
            로그인
          </Button>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-3xl mx-auto space-y-8">
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

          <div className="relative">
            <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 via-blue-500/20 to-purple-500/20 rounded-xl blur-xl opacity-50" />
            <div className="relative bg-card border border-border rounded-xl p-1">
              <Textarea
                value={requirement}
                onChange={(e) => setRequirement(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="프로젝트를 설명해주세요... 예: 사용자가 할 일 목록을 관리할 수 있는 웹 앱을 만들고 싶어요. 할 일 추가, 삭제, 완료 표시 기능이 필요합니다."
                className="min-h-48 resize-none border-0 text-base focus-visible:ring-0 bg-transparent"
                data-testid="input-requirement"
              />
              <div className="flex items-center justify-between px-3 py-2 border-t border-border/50">
                <span className="text-xs text-muted-foreground">
                  {requirement.length} 자
                </span>
                <Button
                  onClick={handleStart}
                  disabled={!requirement.trim()}
                  className="gap-2"
                  data-testid="button-start"
                >
                  <span>시작하기</span>
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8">
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
    <div className="p-4 rounded-lg bg-card border border-border/50 space-y-2 hover-elevate">
      <div className="w-10 h-10 rounded-md bg-primary/10 flex items-center justify-center text-primary">
        {icon}
      </div>
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
