import React, { useEffect, useRef, useState } from "react";
import { CATEGORIES } from "@/lib/categories";
import { useI18n } from "@/context/I18nContext";
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronLeft } from "lucide-react";

export default function CategoryFilters({ active, unavailable = new Set(), onToggle, onAll }) {
  const { lang, t } = useI18n();
  const availableCount = CATEGORIES.filter((category) => !unavailable.has(category.key)).length;
  const allOn = active.size === 0 || active.size === availableCount;
  const scrollerRef = useRef(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  const measure = () => {
    const el = scrollerRef.current;
    if (!el) return;
    setCanLeft(el.scrollLeft > 4);
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  };

  useEffect(() => {
    measure();
    const el = scrollerRef.current;
    if (!el) return;
    const onScroll = () => measure();
    el.addEventListener("scroll", onScroll, { passive: true });
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    const t1 = setTimeout(measure, 60);
    const t2 = setTimeout(measure, 300);
    window.addEventListener("resize", measure);
    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener("resize", measure);
    };
  }, [lang]);

  const scrollBy = (dir) => {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.max(120, el.clientWidth * 0.6), behavior: "smooth" });
  };

  return (
    <div className="relative w-full min-w-0">
      <div
        ref={scrollerRef}
        className="flex gap-2 overflow-x-auto nice-scroll pb-1 pr-7 w-full"
        data-testid="category-filter-bar"
        role="toolbar"
        aria-label="Category filter"
        style={{ scrollbarWidth: "none" }}
      >
        <Button
          type="button"
          onClick={onAll}
          data-testid="cat-filter-all"
          aria-pressed={allOn}
          variant={allOn ? "default" : "secondary"}
          className={`rounded-full h-9 px-4 shrink-0 ${
            allOn
              ? "bg-zinc-900 text-white hover:bg-zinc-800"
              : "bg-white/80 text-zinc-800 hover:bg-white"
          }`}
        >
          {t("all")}
        </Button>
        {CATEGORIES.map((c) => {
          const Icon = c.icon;
          const on = active.has(c.key);
          const isUnavailable = unavailable.has(c.key);
          return (
            <Button
              type="button"
              key={c.key}
              data-testid={`cat-filter-${c.key}`}
              aria-pressed={on}
              aria-label={
                isUnavailable
                  ? `${lang === "zh" ? c.labelZh : c.labelEn}: ${t("category_unavailable")}`
                  : undefined
              }
              title={isUnavailable ? t("category_unavailable") : undefined}
              disabled={isUnavailable}
              onClick={() => onToggle(c.key)}
              variant="secondary"
              className={`rounded-full h-9 px-3 shrink-0 border transition-colors ${
                isUnavailable
                  ? "bg-zinc-100/80 border-zinc-200 text-zinc-400 opacity-70"
                  : on
                  ? "bg-white border-transparent shadow-sm"
                  : "bg-white/70 border-white/60 hover:bg-white"
              }`}
              style={on ? { boxShadow: `0 0 0 2px ${c.color}33 inset` } : undefined}
            >
              <Icon size={16} style={{ color: c.color }} aria-hidden="true" />
              <span className="ml-1.5 text-sm font-medium text-zinc-800">
                {lang === "zh" ? c.labelZh : c.labelEn}
              </span>
            </Button>
          );
        })}
      </div>

      {canLeft && (
        <button
          type="button"
          data-testid="cat-scroll-left"
          onClick={() => scrollBy(-1)}
          aria-label="scroll left"
          className="absolute left-0 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-white border border-zinc-200 shadow grid place-items-center hover:bg-zinc-50"
          style={{ marginTop: "-2px" }}
        >
          <ChevronLeft size={14} className="text-zinc-700" />
        </button>
      )}
      {canRight && (
        <button
          type="button"
          data-testid="cat-scroll-right"
          onClick={() => scrollBy(1)}
          aria-label="scroll right"
          className="absolute right-0 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-white border border-zinc-200 shadow grid place-items-center hover:bg-zinc-50"
          style={{ marginTop: "-2px" }}
        >
          <ChevronRight size={14} className="text-zinc-700" />
        </button>
      )}

      {/* Fade edge hint when there is content to the right */}
      {canRight && (
        <div
          className="pointer-events-none absolute top-0 bottom-1 right-7 w-6 bg-gradient-to-l from-white to-transparent"
          aria-hidden="true"
        />
      )}
    </div>
  );
}
