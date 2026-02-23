import { FormEvent, useMemo, useState } from "react";

type ChatRole = "user" | "assistant";

interface ChatMessage {
  role: ChatRole;
  content: string;
}

interface ChatResponse {
  mode: "playful" | "serious" | "high_risk";
  answer: string;
  facts_used: string[];
}

export default function Index() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [dogJumping, setDogJumping] = useState(false);

  const canSend = useMemo(
    () => input.trim().length > 0 && !loading,
    [input, loading],
  );

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const userText = input.trim();
    if (!userText || loading) return;

    const history = [...messages];
    const userMessage: ChatMessage = { role: "user", content: userText };
    setMessages([...history, userMessage]);
    setInput("");
    setLoading(true);
    setDogJumping(true);

    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_text: userText, history }),
      });

      const data = (await response.json()) as ChatResponse;
      setMessages((current) => [
        ...current,
        { role: "assistant", content: data.answer },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "Ik kan het model nu niet bereiken. Start Ollama en probeer opnieuw.",
        },
      ]);
    } finally {
      setLoading(false);
      window.setTimeout(() => setDogJumping(false), 1200);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-200 px-3 py-8">
      <section className="relative w-[340px] max-w-full">
        <div
          className="relative rounded-[30px] border-[8px] border-lime-700 bg-lime-400 px-4 pt-7 pb-6"
          style={{ clipPath: "polygon(7% 0,93% 0,100% 7%,100% 93%,93% 100%,7% 100%,0 93%,0 7%)" }}
        >
          <div className="mx-auto mb-4 w-fit rounded-full bg-lime-100 px-3 py-1 text-[10px] font-bold tracking-wide text-purple-700">
            MONSTER-BOT v2.0
          </div>

          <div className="rounded-[26px] border-[6px] border-slate-500 bg-slate-100 p-4 shadow-inner">
            <div className="mx-auto mb-3 flex w-28 items-center justify-center rounded-sm bg-cyan-100 py-2">
              <div
                className={`text-4xl origin-bottom ${dogJumping ? "animate-[dogHop_0.45s_ease-in-out_infinite]" : ""}`}
                aria-label="Dog avatar"
                role="img"
              >
                🐶
              </div>
            </div>

            <p className="mb-2 text-center text-xs font-bold tracking-wider text-slate-700">
              SPARKY
            </p>

            <div className="h-[220px] overflow-y-auto rounded-xl bg-white/70 p-2 space-y-2">
              {messages.length === 0 && (
                <p className="rounded-xl bg-slate-100 p-2 text-sm text-slate-700">
                  Hi there! Ik ben Sparky. Vraag maar iets 😊
                </p>
              )}

              {messages.map((message, index) => (
                <article
                  key={`${message.role}-${index}`}
                  className={`rounded-xl px-3 py-2 text-sm leading-snug ${
                    message.role === "user"
                      ? "ml-8 bg-purple-600 text-white"
                      : "mr-8 bg-slate-100 text-slate-700"
                  }`}
                >
                  {message.content}
                </article>
              ))}

              {loading && (
                <p className="mr-8 rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-600">
                  Sparky denkt even...
                </p>
              )}
            </div>

            <form onSubmit={onSubmit} className="mt-3 flex items-center gap-2">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask me anything..."
                className="flex-1 rounded-full border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-purple-500"
              />
              <button
                type="submit"
                disabled={!canSend}
                className="h-10 w-10 rounded-full bg-purple-600 text-lg text-white disabled:opacity-40"
                aria-label="Verstuur"
              >
                ➤
              </button>
            </form>
          </div>

          <div className="mt-6 flex items-center justify-around text-purple-700">
            {[
              { icon: "ⓘ", label: "ABOUT" },
              { icon: "↻", label: "STATUS" },
              { icon: "◍", label: "PRIVACY" },
            ].map((item) => (
              <div key={item.label} className="flex flex-col items-center">
                <button className="mb-1 h-12 w-12 rounded-full bg-purple-600 text-xl text-white shadow-lg shadow-purple-700/40">
                  {item.icon}
                </button>
                <span className="text-[10px] font-bold tracking-wide">{item.label}</span>
              </div>
            ))}
          </div>

          <div className="mt-4 flex justify-around">
            <div className="h-8 w-14 rounded-full bg-purple-600" />
            <div className="h-8 w-14 rounded-full bg-purple-600" />
          </div>
        </div>
      </section>

      <style>{`
        @keyframes dogHop {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
      `}</style>
    </main>
  );
}
