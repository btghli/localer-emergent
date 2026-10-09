import React from "react";
import { CATEGORIES } from "@/lib/categories";
import { useI18n } from "@/context/I18nContext";
import { Button } from "@/components/ui/button";

export default function CategoryFilters({ active, onToggle, onAll }) {
  const { lang, t } = useI18n();
  const allOn = active.size === 0 || active.size === CATEGORIES.length;

  return (
    <div
      className="flex gap-2 overflow-x-auto nice-scroll pb-1"
      data-testid="category-filter-bar"
      role="toolbar"
      aria-label="Category filter"
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
        return (
          <Button
            type="button"
            key={c.key}
            data-testid={`cat-filter-${c.key}`}
            aria-pressed={on}
            onClick={() => onToggle(c.key)}
            variant="secondary"
            className={`rounded-full h-9 px-3 shrink-0 border transition-colors ${
              on
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
  );
}
