import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, User, Loader2 } from "lucide-react";
import { getErrorMessage, sendChatMessage } from "@/services/api";

export const Route = createFileRoute("/app/chat")({
  component: ChatPage,
});

type Msg = { role: "user" | "ai"; content: string };

const suggestions = [
  "Explain Dynamic Programming",
  "Take my mock interview",
  "Generate revision notes",
];

function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "ai",
      content:
        "Hi! I'm your AI prep buddy. Ask me anything — concepts, mock interviews, or revision notes.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, loading]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError("");
    setMessages((m) => [...m, { role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendChatMessage(trimmed);
      setMessages((m) => [...m, { role: "ai", content: data.answer || "No response received." }]);
    } catch (err) {
      setError(getErrorMessage(err));
      setMessages((m) => [
        ...m,
        { role: "ai", content: "Sorry, I couldn't process that request. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] max-w-3xl mx-auto">
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
            {m.role === "ai" && (
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 grid place-items-center shrink-0">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-foreground"
              }`}
            >
              {m.content}
            </div>
            {m.role === "user" && (
              <div className="h-8 w-8 rounded-full bg-foreground/10 grid place-items-center shrink-0">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 grid place-items-center shrink-0">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div className="rounded-2xl px-4 py-2.5 text-sm bg-muted text-muted-foreground inline-flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Thinking...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="border-t pt-3 space-y-2">
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 text-rose-700 px-3 py-2 text-xs">
            {error}
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              disabled={loading}
              className="text-xs px-3 py-1.5 rounded-full border hover:bg-muted disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything about your prep..."
            disabled={loading}
            className="flex-1 h-11 rounded-xl border bg-background px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="h-11 w-11 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white grid place-items-center hover:opacity-90 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </form>
      </div>
    </div>
  );
}
