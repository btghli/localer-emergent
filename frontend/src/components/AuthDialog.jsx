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
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function AuthDialog() {
  const { authOpen, setAuthOpen, login, register } = useAuth();
  const { t } = useI18n();
  const [tab, setTab] = useState("in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

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
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || "Error");
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
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-xl"
            />
            <Input
              type="password"
              required
              minLength={6}
              data-testid="auth-password-input"
              placeholder={t("password")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-xl"
            />
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
