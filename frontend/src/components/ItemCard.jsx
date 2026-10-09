import React from "react";
import { CAT_MAP } from "@/lib/categories";
import { useI18n } from "@/context/I18nContext";
import { MapPin, Clock, AlertTriangle, Beaker } from "lucide-react";

function fmtDistance(m, t) {
  if (m == null) return null;
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
  const title = lang === "zh" && item.titleZh ? item.titleZh : item.title;
  const summary = lang === "zh" && item.summaryZh ? item.summaryZh : item.summary;
  const date = fmtDate(item.startsAt || item.publishedAt, lang);
  const dist = fmtDistance(item.distanceMeters, t);
  const hasImage = item.imageUrl && !item.imageIsFallback;
  const approx = ["city", "region", "neighborhood"].includes(item.locationPrecision);

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
      <div
        className="w-20 h-20 rounded-xl overflow-hidden shrink-0 relative"
        style={
          !hasImage
            ? {
                background: `linear-gradient(135deg, ${cat?.color}22, ${cat?.color}0a)`,
              }
            : undefined
        }
      >
        {hasImage ? (
          <img src={item.imageUrl} alt="" className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="w-full h-full grid place-items-center">
            {Icon && <Icon size={26} style={{ color: cat.color, opacity: 0.75 }} />}
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          {Icon && <Icon size={13} style={{ color: cat.color }} aria-hidden="true" />}
          <span className="text-[11px] uppercase tracking-wide font-semibold" style={{ color: cat?.color }}>
            {lang === "zh" ? cat.labelZh : cat.labelEn}
          </span>
          {item.isDemo && (
            <span className="ml-1 inline-flex items-center gap-0.5 text-[10px] font-semibold text-amber-800 bg-amber-50 border border-amber-200 rounded-full px-1.5 py-0.5">
              <Beaker size={9} /> {t("demo")}
            </span>
          )}
          {item.stale && (
            <span className="ml-1 inline-flex items-center gap-0.5 text-[10px] font-semibold text-slate-700 bg-slate-100 border border-slate-200 rounded-full px-1.5 py-0.5">
              {t("stale")}
            </span>
          )}
        </div>
        <h3 className="font-display font-semibold text-[15px] text-zinc-900 truncate">{title}</h3>
        {summary && (
          <p className="text-xs text-zinc-600 line-clamp-2 mt-0.5 leading-snug">{summary}</p>
        )}
        <div className="flex items-center gap-3 mt-1.5 text-[11px] text-zinc-500 flex-wrap">
          {dist && (
            <span className="inline-flex items-center gap-1">
              <MapPin size={11} aria-hidden="true" />
              {dist}
            </span>
          )}
          {date && (
            <span className="inline-flex items-center gap-1">
              <Clock size={11} aria-hidden="true" />
              {date}
            </span>
          )}
          {item.sourceName && (
            <span className="truncate max-w-[140px]" title={item.sourceName}>
              {item.sourceName}
            </span>
          )}
          {approx && (
            <span className="inline-flex items-center gap-1 text-amber-700">
              <AlertTriangle size={10} /> {t("approx_short")}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

