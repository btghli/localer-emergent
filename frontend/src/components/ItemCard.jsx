import React from "react";
import { CAT_MAP, DEMO_IMAGES } from "@/lib/categories";
import { useI18n } from "@/context/I18nContext";
import { MapPin, Clock } from "lucide-react";

function fmtDistance(m, t) {
  if (m == null) return "—";
  if (m < 1000) return `${Math.round(m)} ${t("m")}`;
  return `${(m / 1000).toFixed(1)} ${t("km")}`;
}

function fmtDate(iso, lang) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(lang === "zh" ? "zh-CN" : "en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return null;
  }
}

export default function ItemCard({ item, selected, onClick }) {
  const { lang, t } = useI18n();
  const cat = CAT_MAP[item.category];
  const Icon = cat?.icon;
  const img = item.imageUrl || DEMO_IMAGES[item.category];
  const title = lang === "zh" && item.titleZh ? item.titleZh : item.title;
  const summary = lang === "zh" && item.summaryZh ? item.summaryZh : item.summary;
  const date = fmtDate(item.startsAt || item.publishedAt, lang);

  return (
    <button
      type="button"
      data-testid={`item-card-${item.id}`}
      onClick={() => onClick(item)}
      className={`w-full text-left rounded-2xl p-3 flex gap-3 transition-all duration-200
        bg-white/95 border ${
          selected
            ? "border-transparent shadow-[0_8px_26px_rgba(0,0,0,0.12)] -translate-y-0.5"
            : "border-white/70 hover:border-zinc-200 hover:-translate-y-0.5 hover:shadow-md"
        }`}
      style={selected ? { boxShadow: `0 0 0 2px ${cat.color}55, 0 8px 26px rgba(0,0,0,0.1)` } : undefined}
    >
      <div className="w-20 h-20 rounded-xl overflow-hidden bg-zinc-100 shrink-0">
        {img ? (
          <img
            src={img}
            alt=""
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full grid place-items-center">
            {Icon && <Icon size={20} style={{ color: cat.color }} />}
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          {Icon && <Icon size={13} style={{ color: cat.color }} aria-hidden="true" />}
          <span
            className="text-[11px] uppercase tracking-wide font-semibold"
            style={{ color: cat?.color }}
          >
            {lang === "zh" ? cat.labelZh : cat.labelEn}
          </span>
        </div>
        <h3 className="font-display font-semibold text-[15px] text-zinc-900 truncate">
          {title}
        </h3>
        <p className="text-xs text-zinc-600 line-clamp-2 mt-0.5 leading-snug">{summary}</p>
        <div className="flex items-center gap-3 mt-1.5 text-[11px] text-zinc-500">
          <span className="inline-flex items-center gap-1">
            <MapPin size={11} aria-hidden="true" />
            {fmtDistance(item.distanceMeters, t)}
          </span>
          {date && (
            <span className="inline-flex items-center gap-1">
              <Clock size={11} aria-hidden="true" />
              {date}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
