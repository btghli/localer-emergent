import React, { useEffect, useRef, useState } from "react";
import { useI18n } from "@/context/I18nContext";
import { useAuth } from "@/context/AuthContext";
import { contentApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Loader2, Volume2, Square } from "lucide-react";
import { speak, stop as ttsStop } from "@/lib/tts";
import { toast } from "sonner";

export default function AskLocalerPanel({ item }) {
  const { lang, t } = useI18n();
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [thread, setThread] = useState([]); // {role: 'user'|'ai', text, sourceUrl?}
  const [loading, setLoading] = useState(false);
  const [speaking, setSpeaking] = useState(null); // index speaking
  const scrollRef = useRef(null);

  useEffect(() => {
    setThread([]);
    setQ("");
  }, [item?.id]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [thread, loading]);

  const askSomething = async (text) => {
    const question = (text ?? q).trim();
    if (!question || loading) return;
    setQ("");
    setThread((th) => [...th, { role: "user", text: question }]);
    setLoading(true);
    try {
      const r = await contentApi.ask(item, question, lang);
      setThread((th) => [...th, { role: "ai", text: r.answer, sourceUrl: r.sourceUrl }]);
    } catch (e) {
      toast.error(t("ai_error"));
    } finally {
      setLoading(false);
    }
  };

  const toggleSpeak = (idx, text) => {
    if (speaking === idx) {
      ttsStop();
      setSpeaking(null);
      return;
    }
    ttsStop();
    speak(text, { lang, voiceName: user?.tts_voice });
    setSpeaking(idx);
    const check = setInterval(() => {
      if (!window.speechSynthesis?.speaking) {
        setSpeaking(null);
        clearInterval(check);
      }
    }, 400);
  };

  const suggested = [t("q1"), t("q2"), t("q3")];

  return (
    <div className="rounded-2xl bg-zinc-50 border border-zinc-200/60 p-3">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles size={16} className="text-zinc-700" aria-hidden="true" />
        <h4 className="font-display font-semibold text-sm text-zinc-900">{t("ask_localer")}</h4>
      </div>

      {thread.length === 0 && (
        <div className="mb-2">
          <p className="text-[11px] uppercase tracking-wide font-semibold text-zinc-500 mb-1.5">
            {t("suggested_questions")}
          </p>
          <div className="flex flex-wrap gap-1.5" data-testid="suggested-questions">
            {suggested.map((s, i) => (
              <button
                type="button"
                key={i}
                data-testid={`suggested-q-${i}`}
                onClick={() => askSomething(s)}
                disabled={loading}
                className="rounded-full px-3 py-1 text-xs bg-white border border-zinc-200 hover:border-zinc-900 hover:text-zinc-900 text-zinc-700 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div ref={scrollRef} className="max-h-60 overflow-auto nice-scroll space-y-2 pr-1">
        {thread.map((m, i) => (
          <div
            key={i}
            data-testid={`chat-msg-${i}`}
            className={`text-sm leading-relaxed rounded-xl px-3 py-2 ${
              m.role === "user"
                ? "bg-zinc-900 text-white ml-6"
                : "bg-white border border-zinc-200 text-zinc-800 mr-6"
            }`}
          >
            {m.text}
            {m.role === "ai" && (
              <div className="mt-1.5 flex items-center gap-3 text-[11px] text-zinc-500">
                <button
                  type="button"
                  data-testid={`chat-tts-${i}`}
                  onClick={() => toggleSpeak(i, m.text)}
                  className="inline-flex items-center gap-1 hover:text-zinc-900"
                >
                  {speaking === i ? (
                    <>
                      <Square size={12} /> {t("stop")}
                    </>
                  ) : (
                    <>
                      <Volume2 size={12} /> {t("listen")}
                    </>
                  )}
                </button>
                {m.sourceUrl && (
                  <a
                    href={m.sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-zinc-900"
                  >
                    {t("source")}
                  </a>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="text-sm text-zinc-600 inline-flex items-center gap-1.5 mr-6 bg-white border border-zinc-200 rounded-xl px-3 py-2">
            <Loader2 size={14} className="animate-spin" /> {t("thinking")}
          </div>
        )}
      </div>

      <div className="mt-2 flex items-end gap-2">
        <Textarea
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("ask_placeholder")}
          data-testid="ask-input"
          rows={1}
          className="min-h-[40px] max-h-28 resize-none rounded-xl bg-white border-zinc-200"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              askSomething();
            }
          }}
        />
        <Button
          type="button"
          onClick={() => askSomething()}
          disabled={loading || !q.trim()}
          data-testid="ask-send-btn"
          className="rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white h-10"
        >
          {t("send")}
        </Button>
      </div>

      <p className="mt-2 text-[11px] text-zinc-500">{t("ai_disclaimer")}</p>
    </div>
  );
}
