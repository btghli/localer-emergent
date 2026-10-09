import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { STRINGS } from "@/lib/i18n";

const I18nCtx = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => {
    const saved = localStorage.getItem("localer_lang");
    if (saved === "en" || saved === "zh") return saved;
    const nav = (navigator.language || "en").toLowerCase();
    if (nav.startsWith("zh")) return "zh";
    return "en";
  });

  useEffect(() => {
    localStorage.setItem("localer_lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  }, [lang]);

  const value = useMemo(() => {
    const dict = STRINGS[lang] || STRINGS.en;
    const t = (k) => dict[k] ?? k;
    return { lang, setLang, t };
  }, [lang]);

  return <I18nCtx.Provider value={value}>{children}</I18nCtx.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nCtx);
  if (!ctx) throw new Error("useI18n must be inside I18nProvider");
  return ctx;
}
