import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/context/I18nContext";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function AuthDialog() {
  const { authOpen, setAuthOpen, login, register } = useAuth();
  const { t } = useI18n();
  const [tab, setTab] = useState("in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (tab === "in") {
        await login(email, password);
        toast.success(t("sign_in"));
      } else {
        await register(email, password, name);
        toast.success(t("sign_up"));
      }
      setAuthOpen(false);
      setEmail("");
      setPassword("");
      setName("");
      setShowPassword(false);
    } catch (e2) {
      const detail = e2?.response?.data?.detail;
      if (detail === "Email already registered") {
        toast.error(t("auth_email_exists"));
      } else if (detail === "Invalid credentials") {
        toast.error(t("auth_invalid_credentials"));
      } else {
        toast.error(t("auth_error"));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={authOpen} onOpenChange={setAuthOpen}>
      <DialogContent className="sm:max-w-md rounded-2xl" data-testid="auth-dialog">
        <DialogHeader>
          <DialogTitle className="font-display">{t("sign_in_needed_title")}</DialogTitle>
          <DialogDescription>{t("sign_in_needed_body")}</DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={setTab} className="mt-2">
          <TabsList className="grid grid-cols-2 w-full rounded-full p-1">
            <TabsTrigger value="in" data-testid="auth-tab-in" className="rounded-full">
              {t("sign_in")}
            </TabsTrigger>
            <TabsTrigger value="up" data-testid="auth-tab-up" className="rounded-full">
              {t("sign_up")}
            </TabsTrigger>
          </TabsList>

          <form onSubmit={submit} className="space-y-3 mt-4">
            <TabsContent value="up" className="m-0">
              <Input
                data-testid="auth-name-input"
                placeholder={t("name")}
                aria-label={t("name")}
                autoComplete="name"
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="rounded-xl"
              />
            </TabsContent>
            <Input
              type="email"
              required
              data-testid="auth-email-input"
              placeholder={t("email")}
              aria-label={t("email")}
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-xl"
            />
            <div>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={tab === "up" ? 6 : 1}
                  maxLength={128}
                  data-testid="auth-password-input"
                  placeholder={t("password")}
                  aria-label={t("password")}
                  autoComplete={tab === "up" ? "new-password" : "current-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="rounded-xl pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((shown) => !shown)}
                  aria-label={showPassword ? t("hide_password") : t("show_password")}
                  className="absolute inset-y-0 right-0 grid w-10 place-items-center rounded-r-xl text-zinc-500 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-zinc-900"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {tab === "up" && (
                <p className="mt-1.5 px-1 text-xs text-zinc-500">{t("password_hint")}</p>
              )}
            </div>
            <Button
              type="submit"
              data-testid="auth-submit-btn"
              disabled={loading}
              className="w-full rounded-xl bg-zinc-900 hover:bg-zinc-800 h-11"
            >
              {loading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : tab === "in" ? (
                t("sign_in")
              ) : (
                t("sign_up")
              )}
            </Button>
          </form>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
