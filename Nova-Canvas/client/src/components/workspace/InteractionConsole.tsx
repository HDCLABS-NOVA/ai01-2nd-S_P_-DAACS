import { useRef, useEffect } from "react";
import type { Message } from "@shared/schema";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Sparkles, User } from "lucide-react";
import { cn } from "@/lib/utils";

interface InteractionConsoleProps {
  messages: Message[];
  inputValue: string;
  setInputValue: (value: string) => void;
  onSendMessage: () => void;
  isDaacsTyping: boolean;
  isPending: boolean;
}

export function InteractionConsole({
  messages,
  inputValue,
  setInputValue,
  onSendMessage,
  isDaacsTyping,
  isPending,
}: InteractionConsoleProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isDaacsTyping]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  };

  return (
    <div className="w-80 flex flex-col border-r border-border/50 bg-sidebar shrink-0">
      <div className="h-12 px-4 flex items-center border-b border-border/50">
        <h2 className="text-sm font-semibold">Interaction Console</h2>
      </div>

      <ScrollArea className="flex-1" ref={scrollRef}>
        <div className="p-4 space-y-4">
          {messages.map((message, index) => (
            <MessageBubble key={message.id || index} message={message} />
          ))}
          
          {isDaacsTyping && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <Sparkles className="w-4 h-4 text-primary-foreground" />
              </div>
              <div className="flex-1 p-3 rounded-lg bg-card border border-border/50">
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-muted-foreground animate-pulse" />
                  <div className="w-2 h-2 rounded-full bg-muted-foreground animate-pulse delay-75" />
                  <div className="w-2 h-2 rounded-full bg-muted-foreground animate-pulse delay-150" />
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-3 border-t border-border/50">
        <div className="relative">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="메시지를 입력하세요..."
            className="min-h-20 max-h-32 resize-none pr-12 text-sm"
            disabled={isPending}
            data-testid="input-chat-message"
          />
          <Button
            size="icon"
            className="absolute right-2 bottom-2"
            onClick={onSendMessage}
            disabled={!inputValue.trim() || isPending}
            data-testid="button-send-message"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex items-start gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
          isUser ? "bg-secondary" : "bg-primary"
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-secondary-foreground" />
        ) : (
          <Sparkles className="w-4 h-4 text-primary-foreground" />
        )}
      </div>
      <div
        className={cn(
          "flex-1 p-3 rounded-lg text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-card border border-border/50"
        )}
      >
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {message.createdAt && (
          <p
            className={cn(
              "text-xs mt-2",
              isUser ? "text-primary-foreground/70" : "text-muted-foreground"
            )}
          >
            {new Date(message.createdAt).toLocaleTimeString("ko-KR", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
      </div>
    </div>
  );
}
