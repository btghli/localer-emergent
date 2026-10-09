import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/context/I18nContext";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { loadVoices } from "@/lib/tts";
import { toast } from "sonner";
import { LogOut, UserRound } from "lucide-react";

export default function Account() {
  const { user, logout, updateSettings, setAuthOpen } = useAuth();
  const { lang, setLang, t } = useI18n();
  const [voices, setVoices] = useState([]);
  const [voiceName, setVoiceName] = useState(user?.tts_voice || "");

  useEffect(() => {
    loadVoices().then((v) => setVoices(v || []));
  }, []);

  useEffect(() => {
    setVoiceName(user?.tts_voice || "");
  }, [user]);

  const changeLang = async (l) => {
    setLang(l);
    if (user) {
      try {
        await updateSettings({ language: l });
      } catch {}
    }
  };

  const changeVoice = async (name) => {
    setVoiceName(name);
    if (user) {
      try {
        await updateSettings({ tts_voice: name });
        toast.success(t("settings_saved"));
      } catch {
        toast.error(t("settings_error"));
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-white pb-24 md:pb-10">
      <div className="max-w-xl mx-auto px-4 pt-6 md:pt-10">
        <p className="text-[11px] uppercase tracking-wide font-semibold text-zinc-500">
          {t("app_name")}
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight mb-6">
          {t("account")}
        </h1>

        <div className="rounded-3xl bg-white border border-zinc-200 shadow-sm p-5 mb-5">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-full bg-zinc-900 text-white grid place-items-center">
                <UserRound size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-display text-base font-semibold truncate" data-testid="account-email">
                  {user.name || user.email}
                </p>
                <p className="text-xs text-zinc-500 truncate">{user.email}</p>
              </div>
              <Button
                type="button"
                onClick={logout}
                data-testid="sign-out-btn"
                variant="secondary"
                className="rounded-full h-9 px-3 border border-zinc-200"
              >
                <LogOut size={14} className="mr-1" /> {t("sign_out")}
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <p className="font-display text-base font-semibold">{t("guest")}</p>
                <p className="text-xs text-zinc-500">{t("sign_in_needed_body")}</p>
              </div>
              <Button
                type="button"
                onClick={() => setAuthOpen(true)}
                data-testid="account-sign-in-btn"
                className="rounded-full h-9 px-3 bg-zinc-900 hover:bg-zinc-800"
              >
                {t("sign_in")}
              </Button>
            </div>
          )}
        </div>

        <div className="rounded-3xl bg-white border border-zinc-200 shadow-sm p-5">
          <h3 className="font-display font-semibold text-sm mb-3">{t("settings")}</h3>

          <div className="space-y-4">
            <div>
              <label className="text-[11px] uppercase tracking-wide font-semibold text-zinc-500 block mb-1.5">
                {t("language")}
              </label>
              <Select value={lang} onValueChange={changeLang}>
                <SelectTrigger
                  data-testid="settings-language-select"
                  className="rounded-xl h-10 bg-white"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="zh">简体中文</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Separator />

            <div>
              <label className="text-[11px] uppercase tracking-wide font-semibold text-zinc-500 block mb-1.5">
                {t("tts_voice")}
              </label>
              <Select value={voiceName || "auto"} onValueChange={(v) => changeVoice(v === "auto" ? "" : v)}>
                <SelectTrigger data-testid="settings-voice-select" className="rounded-xl h-10 bg-white">
                  <SelectValue placeholder={t("voice_auto")} />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  <SelectItem value="auto">{t("voice_auto")}</SelectItem>
                  {voices
                    .filter((v) => /^(en|zh)/i.test(v.lang || ""))
                    .map((v) => (
                      <SelectItem key={v.name} value={v.name}>
                        {v.name} ({v.lang})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
