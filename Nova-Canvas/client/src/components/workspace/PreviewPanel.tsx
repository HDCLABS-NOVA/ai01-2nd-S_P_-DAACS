import { useState, useEffect, useRef } from "react";
import type { Project, PreviewState } from "@shared/schema";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Monitor, Code2, RefreshCw, Maximize2, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

interface PreviewPanelProps {
  previewState: PreviewState | undefined;
  project: Project;
}

export function PreviewPanel({ previewState, project }: PreviewPanelProps) {
  const [activeView, setActiveView] = useState<"preview" | "code">("preview");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const handleRefresh = () => {
    setIsRefreshing(true);
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const generatePreviewHtml = () => {
    if (!previewState) {
      return `
        <!DOCTYPE html>
        <html lang="ko">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
              font-family: 'Inter', system-ui, sans-serif;
              min-height: 100vh;
              display: flex;
              align-items: center;
              justify-content: center;
              background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
              color: #e4e4e7;
            }
            .container {
              text-align: center;
              padding: 2rem;
            }
            .icon {
              width: 64px;
              height: 64px;
              margin: 0 auto 1.5rem;
              opacity: 0.5;
            }
            h1 { 
              font-size: 1.25rem;
              font-weight: 600;
              margin-bottom: 0.5rem;
            }
            p { 
              font-size: 0.875rem;
              color: #a1a1aa;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
            <h1>미리보기 준비 중</h1>
            <p>DAACS와 대화하여 UI를 생성해보세요.</p>
          </div>
        </body>
        </html>
      `;
    }

    return `
      <!DOCTYPE html>
      <html lang="ko">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          ${previewState.cssContent || ""}
        </style>
      </head>
      <body>
        ${previewState.htmlContent || ""}
        <script>
          ${previewState.jsContent || ""}
        </script>
      </body>
      </html>
    `;
  };

  return (
    <div className="flex-1 flex flex-col min-w-[500px]">
      <div className="h-12 px-4 flex items-center justify-between gap-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold">Preview</h2>
          {previewState?.updatedAt && (
            <span className="text-xs text-muted-foreground">
              마지막 업데이트:{" "}
              {new Date(previewState.updatedAt).toLocaleTimeString("ko-KR", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
            data-testid="button-refresh-preview"
          >
            <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
          </Button>
          <Button variant="ghost" size="icon" data-testid="button-fullscreen-preview">
            <Maximize2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {previewState?.description && (
        <div className="px-4 py-3 border-b border-border/50 bg-muted/30">
          <p className="text-sm text-muted-foreground">{previewState.description}</p>
        </div>
      )}

      <Tabs value={activeView} onValueChange={(v) => setActiveView(v as "preview" | "code")} className="flex-1 flex flex-col">
        <div className="px-4 py-2 border-b border-border/50">
          <TabsList className="h-8">
            <TabsTrigger value="preview" className="text-xs gap-1.5">
              <Monitor className="w-3.5 h-3.5" />
              미리보기
            </TabsTrigger>
            <TabsTrigger value="code" className="text-xs gap-1.5">
              <Code2 className="w-3.5 h-3.5" />
              코드
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="preview" className="flex-1 m-0 p-0">
          <div className="h-full bg-muted/30 p-4">
            <div className="h-full rounded-lg overflow-hidden border border-border/50 bg-white dark:bg-zinc-900">
              <iframe
                ref={iframeRef}
                srcDoc={generatePreviewHtml()}
                className="w-full h-full"
                sandbox="allow-scripts"
                title="Preview"
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="code" className="flex-1 m-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-4">
              {previewState?.htmlContent && (
                <CodeBlock title="HTML" language="html" content={previewState.htmlContent} />
              )}
              {previewState?.cssContent && (
                <CodeBlock title="CSS" language="css" content={previewState.cssContent} />
              )}
              {previewState?.jsContent && (
                <CodeBlock title="JavaScript" language="javascript" content={previewState.jsContent} />
              )}
              {!previewState?.htmlContent && !previewState?.cssContent && !previewState?.jsContent && (
                <div className="text-center py-8 text-muted-foreground">
                  <Code2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">아직 생성된 코드가 없습니다.</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function CodeBlock({
  title,
  language,
  content,
}: {
  title: string;
  language: string;
  content: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-md border border-border/50 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs font-mono">
            {language}
          </Badge>
          <span className="text-xs font-medium">{title}</span>
        </div>
        <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 text-xs">
          {copied ? "복사됨" : "복사"}
        </Button>
      </div>
      <pre className="p-4 text-xs font-mono overflow-x-auto bg-card">
        <code>{content}</code>
      </pre>
    </div>
  );
}
