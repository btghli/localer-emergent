import React, { useEffect, useRef, useState } from "react";
import { Search, X, Loader2, LocateFixed } from "lucide-react";
import { Input } from "@/components/ui/input";
import { contentApi } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

export default function SearchBar({ onPick, onRecenter, showRecenter = true }) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const timerRef = useRef(null);
  const containerRef = useRef(null);
  const requestRef = useRef(0);
  const skipNextSearchRef = useRef(false);

  useEffect(() => {
    const query = q.trim();
    clearTimeout(timerRef.current);

    // Selecting a result writes its label into the input. Do not immediately
    // search that label again and reopen the menu.
    if (skipNextSearchRef.current) {
      skipNextSearchRef.current = false;
      setResults([]);
      setOpen(false);
      setLoading(false);
      setSearched(false);
      return;
    }

    if (!query) {
      requestRef.current += 1;
      setResults([]);
      setOpen(false);
      setLoading(false);
      setSearched(false);
      setActiveIndex(-1);
      return;
    }

    setLoading(true);
    setSearched(false);
    setActiveIndex(-1);
    timerRef.current = setTimeout(async () => {
      const requestId = ++requestRef.current;
      try {
        const r = await contentApi.geocode(query);
        if (requestId !== requestRef.current) return;
        setResults(r || []);
        setOpen(true);
      } catch {
        if (requestId !== requestRef.current) return;
        setResults([]);
        setOpen(true);
      } finally {
        if (requestId === requestRef.current) {
          setLoading(false);
          setSearched(true);
        }
      }
    }, 350);
    return () => {
      clearTimeout(timerRef.current);
      requestRef.current += 1;
    };
  }, [q]);

  useEffect(() => {
    const h = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const pick = (r) => {
    skipNextSearchRef.current = true;
    setOpen(false);
    setResults([]);
    setActiveIndex(-1);
    setQ(r.display_name);
    onPick({ lat: r.lat, lng: r.lng, label: r.display_name });
  };

  const onKeyDown = (e) => {
    if (e.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (!results.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActiveIndex((i) => (i + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      setActiveIndex((i) => (i <= 0 ? results.length - 1 : i - 1));
    } else if (e.key === "Enter" && open && activeIndex >= 0) {
      e.preventDefault();
      pick(results[activeIndex]);
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative pointer-events-auto flex items-center gap-2"
      data-testid="search-container"
    >
      <div className="relative flex-1 min-w-0">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
          aria-hidden="true"
        />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={t("search_placeholder")}
          className="pl-9 pr-9 h-11 text-sm rounded-full bg-white/90 backdrop-blur-xl border-white/60 shadow-[0_8px_30px_rgba(0,0,0,0.08)] focus-visible:ring-zinc-900 truncate placeholder:truncate"
          data-testid="global-search-input"
          aria-label={t("search_placeholder")}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls="location-search-results"
          aria-activedescendant={activeIndex >= 0 ? `location-result-${activeIndex}` : undefined}
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
              requestRef.current += 1;
              setQ("");
              setResults([]);
              setOpen(false);
              setLoading(false);
              setSearched(false);
              setActiveIndex(-1);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-zinc-100"
            aria-label="clear"
          >
            <X size={14} className="text-zinc-500" />
          </button>
        )}
      </div>
      {showRecenter && onRecenter && (
        <button
          type="button"
          onClick={onRecenter}
          data-testid="searchbar-recenter-btn"
          aria-label={t("recenter")}
          title={t("recenter")}
          className="shrink-0 w-11 h-11 rounded-full bg-white/90 backdrop-blur-xl border border-white/60 shadow-[0_8px_30px_rgba(0,0,0,0.08)] grid place-items-center hover:bg-white text-zinc-800 transition-colors"
        >
          <LocateFixed size={16} />
        </button>
      )}

      {open && results.length > 0 && (
        <ul
          id="location-search-results"
          role="listbox"
          className="absolute left-0 right-0 top-full mt-2 max-h-80 overflow-auto nice-scroll rounded-2xl bg-white/95 backdrop-blur-xl border border-white/60 shadow-xl p-1 z-50"
          data-testid="search-results"
        >
          {results.map((r, i) => (
            <li
              key={`${r.lat}-${r.lng}-${i}`}
              id={`location-result-${i}`}
              role="option"
              aria-selected={activeIndex === i}
            >
              <button
                type="button"
                data-testid={`search-result-${i}`}
                onClick={() => pick(r)}
                onMouseEnter={() => setActiveIndex(i)}
                className={`w-full text-left px-3 py-2 rounded-xl text-sm text-zinc-800 transition-colors ${
                  activeIndex === i ? "bg-zinc-100" : "hover:bg-zinc-100"
                }`}
              >
                {r.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}

      {open && searched && !loading && q.trim() && results.length === 0 && (
        <div
          role="status"
          className="absolute left-0 right-0 top-full mt-2 rounded-2xl bg-white/95 backdrop-blur-xl border border-white/60 shadow-xl px-4 py-3 z-50 text-sm text-zinc-600"
        >
          {t("search_no_results")}
        </div>
      )}
    </div>
  );
}
