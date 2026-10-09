import React, { useEffect, useRef, useState } from "react";
import { Search, X, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { contentApi } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

export default function SearchBar({ onPick }) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      try {
        const r = await contentApi.geocode(q.trim());
        setResults(r || []);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 350);
    return () => clearTimeout(timerRef.current);
  }, [q]);

  useEffect(() => {
    const h = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const pick = (r) => {
    setOpen(false);
    setQ(r.display_name);
    onPick({ lat: r.lat, lng: r.lng, label: r.display_name });
  };

  return (
    <div
      ref={containerRef}
      className="relative pointer-events-auto"
      data-testid="search-container"
    >
      <div className="relative">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
          aria-hidden="true"
        />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder={t("search_placeholder")}
          className="pl-9 pr-9 h-11 rounded-full bg-white/90 backdrop-blur-xl border-white/60 shadow-[0_8px_30px_rgba(0,0,0,0.08)] focus-visible:ring-zinc-900"
          data-testid="global-search-input"
          aria-label={t("search_placeholder")}
        />
        {loading && (
          <Loader2
            size={16}
            className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-zinc-500"
          />
        )}
        {!loading && q && (
          <button
            type="button"
            data-testid="search-clear-btn"
            onClick={() => {
              setQ("");
              setResults([]);
              setOpen(false);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-zinc-100"
            aria-label="clear"
          >
            <X size={14} className="text-zinc-500" />
          </button>
        )}
      </div>

      {open && results.length > 0 && (
        <ul
          className="absolute left-0 right-0 mt-2 max-h-80 overflow-auto nice-scroll rounded-2xl bg-white/95 backdrop-blur-xl border border-white/60 shadow-xl p-1 z-50"
          data-testid="search-results"
        >
          {results.map((r, i) => (
            <li key={`${r.lat}-${r.lng}-${i}`}>
              <button
                type="button"
                data-testid={`search-result-${i}`}
                onClick={() => pick(r)}
                className="w-full text-left px-3 py-2 rounded-xl hover:bg-zinc-100 text-sm text-zinc-800"
              >
                {r.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
