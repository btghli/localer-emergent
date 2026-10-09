import React, { useEffect, useState } from "react";
import { CAT_MAP } from "@/lib/categories";
import { useI18n } from "@/context/I18nContext";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import {
  X,
  ExternalLink,
  MapPin,
  Clock,
  Heart,
  Volume2,
  Pause,
  Play,
  Square,
  Languages,
  AlertTriangle,
  Loader2,
  Beaker,
  Archive,
  Ban,
} from "lucide-react";
import { contentApi, favApi } from "@/lib/api";
import { speak, pause as ttsPause, resume as ttsResume, stop as ttsStop } from "@/lib/tts";
import { toast } from "sonner";
import AskLocalerPanel from "./AskLocalerPanel";

function fmt(iso, lang) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString(lang === "zh" ? "zh-CN" : "en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return null;
  }
}

export default function ItemDetail({ item, onClose, favorites, onToggleFavorite }) {
  const { lang, t } = useI18n();
  const { user, setAuthOpen } = useAuth();
  const [showZh, setShowZh] = useState(lang === "zh");
  const [translation, setTranslation] = useState({ itemId: null, title: null, summary: null });
  const [translating, setTranslating] = useState(false);
  const [ttsState, setTtsState] = useState("idle");
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setShowZh(lang === "zh");
  }, [item?.id, lang]);

  useEffect(() => {
    setImageFailed(false);
  }, [item?.imageUrl]);

  useEffect(() => {
    return () => ttsStop();
  }, [item?.id]);

  useEffect(() => {
    let cancelled = false;
    const translate = async () => {
      if (!item) return;
      if (!showZh) {
        setTranslating(false);
        return;
      }
      if (item.titleZh && item.summaryZh) {
        setTranslation({ itemId: item.id, title: item.titleZh, summary: item.summaryZh });
        setTranslating(false);
        return;
      }
      if (!item.summary && !item.title) return;
      // Associate every translation with its item. This prevents a slow
      // response for the previously selected card from replacing new content.
      setTranslation({
        itemId: item.id,
        title: item.titleZh || null,
        summary: item.summaryZh || null,
      });
      setTranslating(true);
      try {
        const [tTitle, tSum] = await Promise.all([
          item.titleZh
            ? Promise.resolve({ text: item.titleZh })
            : contentApi.translate(item.title || "", "zh"),
          item.summaryZh || !item.summary
            ? Promise.resolve({ text: item.summaryZh || "" })
            : contentApi.translate(item.summary, "zh"),
        ]);
        if (!cancelled) {
          setTranslation({ itemId: item.id, title: tTitle.text, summary: tSum.text });
        }
      } catch {
        if (!cancelled) {
          setTranslation({ itemId: item.id, title: item.title, summary: item.summary });
        }
      } finally {
        if (!cancelled) setTranslating(false);
      }
    };
    translate();
    return () => {
      cancelled = true;
    };
  }, [item, showZh]);

  if (!item) return null;
  const cat = CAT_MAP[item.category];
  const Icon = cat?.icon;
  const hasImage = item.imageUrl && !item.imageIsFallback && !imageFailed;

  const currentTranslation = translation.itemId === item.id ? translation : null;

  const titleDisplay = showZh ? currentTranslation?.title || item.title : item.title;
  const summaryDisplay = showZh
    ? currentTranslation?.summary || item.summary || ""
    : item.summary || "";

  const isFav = favorites?.has(item.externalId);
  const date = fmt(item.startsAt || item.publishedAt, lang);
  const approximate = ["city", "region", "neighborhood"].includes(item.locationPrecision);
  const cancelled = item.eventStatus === "cancelled";
  const postponed = item.eventStatus === "postponed";

  const onListen = () => {
    if (ttsState === "playing") {
      ttsPause();
      setTtsState("paused");
      return;
    }
    if (ttsState === "paused") {
      ttsResume();
      setTtsState("playing");
      return;
    }
    const text = `${titleDisplay}. ${summaryDisplay || ""}`;
    speak(text, {
      lang: showZh ? "zh" : "en",
      voiceName: user?.tts_voice,
    });
    setTtsState("playing");
    const check = setInterval(() => {
      if (!window.speechSynthesis?.speaking && !window.speechSynthesis?.paused) {
        setTtsState("idle");
        clearInterval(check);
      }
    }, 400);
  };

  const onStop = () => {
    ttsStop();
    setTtsState("idle");
  };

  const onFav = async () => {
    if (!user) {
      setAuthOpen(true);
      return;
    }
    try {
      if (isFav) {
        await favApi.remove(item.externalId);
        onToggleFavorite(item.externalId, false);
      } else {
        await favApi.add(item);
        onToggleFavorite(item.externalId, true);
        toast.success(t("saved"));
      }
    } catch {
      toast.error("Failed");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="relative shrink-0">
        {hasImage ? (
          <div className="h-40 sm:h-48 w-full overflow-hidden rounded-t-3xl">
            <img
              src={item.imageUrl}
              alt=""
              className="w-full h-full object-cover"
              onError={() => setImageFailed(true)}
            />
          </div>
        ) : (
          <div
            className="h-32 sm:h-36 w-full rounded-t-3xl grid place-items-center relative"
            style={{
              background: `linear-gradient(135deg, ${cat?.color}24, ${cat?.color}0a 70%)`,
            }}
          >
            {Icon && <Icon size={38} style={{ color: cat?.color, opacity: 0.65 }} />}
            <span className="absolute bottom-2 right-3 text-[10px] uppercase tracking-wider text-zinc-500">
              {t("no_image_provided")}
            </span>
          </div>
        )}
        <button
          type="button"
          data-testid="detail-close-btn"
          onClick={onClose}
          className="absolute top-3 right-3 w-9 h-9 rounded-full bg-white/95 backdrop-blur-xl shadow-md grid place-items-center hover:bg-white"
          aria-label={t("close")}
        >
          <X size={16} />
        </button>
        <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-white/95 backdrop-blur-xl rounded-full pl-2 pr-3 py-1 shadow-md">
          {Icon && <Icon size={13} style={{ color: cat.color }} aria-hidden="true" />}
          <span className="text-xs font-semibold" style={{ color: cat.color }}>
            {lang === "zh" ? cat.labelZh : cat.labelEn}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto nice-scroll px-4 sm:px-5 pt-4 pb-6 space-y-4">
        <div>
          <h2 data-testid="detail-title" className="font-display text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
            {titleDisplay}
          </h2>
          {showZh && currentTranslation?.title && currentTranslation.title !== item.title && (
            <p className="text-xs text-zinc-500 mt-1">
              {t("original_name")}: <span className="text-zinc-700">{item.title}</span>
            </p>
          )}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-zinc-600">
            {item.distanceMeters != null && (
              <span className="inline-flex items-center gap-1">
                <MapPin size={12} />
                {item.distanceMeters < 1000
                  ? `${Math.round(item.distanceMeters)} ${t("m")}`
                  : `${(item.distanceMeters / 1000).toFixed(1)} ${t("km")}`}
              </span>
            )}
            {date && (
              <span className="inline-flex items-center gap-1">
                <Clock size={12} /> {date}
              </span>
            )}
            {item.venueName && <span className="truncate max-w-[200px]">{item.venueName}</span>}
          </div>

          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            {approximate && (
              <div className="inline-flex items-center gap-1.5 text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-1">
                <AlertTriangle size={11} /> {t("approx_location")}
              </div>
            )}
            {item.isDemo && (
              <div className="inline-flex items-center gap-1.5 text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-1">
                <Beaker size={11} /> {t("demo_content")}
              </div>
            )}
            {item.stale && (
              <div className="inline-flex items-center gap-1.5 text-[11px] text-slate-700 bg-slate-100 border border-slate-200 rounded-full px-2.5 py-1">
                <Archive size={11} /> {t("stale_content")}
              </div>
            )}
            {cancelled && (
              <div className="inline-flex items-center gap-1.5 text-[11px] text-rose-800 bg-rose-50 border border-rose-200 rounded-full px-2.5 py-1">
                <Ban size={11} /> {t("event_cancelled")}
              </div>
            )}
            {postponed && (
              <div className="inline-flex items-center gap-1.5 text-[11px] text-indigo-800 bg-indigo-50 border border-indigo-200 rounded-full px-2.5 py-1">
                <AlertTriangle size={11} /> {t("event_postponed")}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            onClick={() => setShowZh((s) => !s)}
            data-testid="lang-toggle-btn"
            variant="secondary"
            className="rounded-full h-9 px-3 bg-white border border-zinc-200 hover:bg-zinc-50"
          >
            <Languages size={14} className="mr-1" />
            {showZh ? "中文" : "EN"} / {showZh ? "EN" : "中文"}
          </Button>

          {(summaryDisplay || titleDisplay) && (
            <Button
              type="button"
              size="sm"
              onClick={onListen}
              disabled={translating}
              data-testid="tts-listen-btn"
              className="rounded-full h-9 px-3 bg-zinc-900 text-white hover:bg-zinc-800"
            >
              {ttsState === "playing" ? (
                <><Pause size={14} className="mr-1" /> {t("pause")}</>
              ) : ttsState === "paused" ? (
                <><Play size={14} className="mr-1" /> {t("resume")}</>
              ) : (
                <><Volume2 size={14} className="mr-1" /> {t("listen")}</>
              )}
            </Button>
          )}
          {ttsState !== "idle" && (
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={onStop}
              data-testid="tts-stop-btn"
              className="rounded-full h-9 px-3 bg-white border border-zinc-200"
            >
              <Square size={14} className="mr-1" /> {t("stop")}
            </Button>
          )}

          <Button
            type="button"
            size="sm"
            onClick={onFav}
            data-testid="fav-toggle-btn"
            variant="secondary"
            className={`rounded-full h-9 px-3 border ${
              isFav
                ? "bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100"
                : "bg-white border-zinc-200 hover:bg-zinc-50"
            }`}
          >
            <Heart size={14} className="mr-1" fill={isFav ? "currentColor" : "none"} />
            {isFav ? t("saved") : t("save")}
          </Button>
        </div>

        {summaryDisplay && (
          <div>
            <p className="text-[11px] uppercase tracking-wide font-semibold text-zinc-500 mb-1">
              {t("description")}
            </p>
            {translating ? (
              <p className="text-sm text-zinc-500 inline-flex items-center gap-1">
                <Loader2 size={14} className="animate-spin" /> {t("translating")}
              </p>
            ) : (
              <p
                data-testid="detail-summary"
                className="text-[15px] text-zinc-800 leading-relaxed whitespace-pre-wrap"
              >
                {summaryDisplay}
              </p>
            )}
          </div>
        )}

        {item.sourceUrl && (
          <a
            href={item.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="detail-source-link"
            className="inline-flex items-center gap-1.5 text-sm text-zinc-700 underline underline-offset-4 hover:text-zinc-900"
          >
            {t("source")}: {item.sourceName} <ExternalLink size={13} />
          </a>
        )}

        {item.imageAttribution && hasImage && (
          <p className="text-[10px] text-zinc-500">
            {t("image_credit")}: {item.imageAttribution}
          </p>
        )}

        <AskLocalerPanel item={item} />
      </div>
    </div>
  );
}
