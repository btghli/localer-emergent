import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, NavLink, Link } from "react-router-dom";
import { I18nProvider, useI18n } from "@/context/I18nContext";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import BottomNav from "@/components/BottomNav";
import AuthDialog from "@/components/AuthDialog";
import Explore from "@/pages/Explore";
import Favorites from "@/pages/Favorites";
import Account from "@/pages/Account";
import { Compass, Heart, UserRound, Languages, MapPinned } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function DesktopHeader() {
  const { lang, setLang, t } = useI18n();
  const { user, setAuthOpen, logout } = useAuth();

  return (
    <header className="hidden md:flex fixed top-0 inset-x-0 h-16 z-50 pointer-events-none">
      <div className="w-full flex items-center justify-between px-4 gap-4">
        <div className="pointer-events-auto flex items-center gap-2 min-w-0">
          <Link
            to="/"
            data-testid="brand-logo"
            className="inline-flex items-center gap-2 bg-white/90 backdrop-blur-xl rounded-full px-3 py-1.5 shadow-sm border border-white/70 shrink-0"
          >
            <div className="w-7 h-7 rounded-full bg-zinc-900 grid place-items-center">
              <MapPinned size={14} className="text-white" />
            </div>
            <span className="font-display font-bold text-zinc-900">{t("app_name")}</span>
          </Link>

          <nav className="bg-white/90 backdrop-blur-xl rounded-full px-1 py-1 shadow-sm border border-white/70 flex items-center gap-0.5">
            {[
              { to: "/", label: t("explore"), icon: Compass, testid: "nav-explore-desktop" },
              { to: "/favorites", label: t("favorites"), icon: Heart, testid: "nav-favorites-desktop" },
              { to: "/account", label: t("account"), icon: UserRound, testid: "nav-account-desktop" },
            ].map((n) => {
              const Icon = n.icon;
              return (
                <NavLink
                  key={n.to}
                  to={n.to}
                  end={n.to === "/"}
                  data-testid={n.testid}
                  className={({ isActive }) =>
                    `inline-flex items-center gap-1.5 text-sm px-3 h-9 rounded-full transition-colors ${
                      isActive
                        ? "bg-zinc-900 text-white"
                        : "text-zinc-700 hover:bg-zinc-100"
                    }`
                  }
                >
                  <Icon size={14} />
                  <span>{n.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        <div className="pointer-events-auto flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="secondary"
                size="sm"
                data-testid="lang-menu-trigger"
                className="rounded-full h-9 px-3 bg-white/90 backdrop-blur-xl border border-white/70"
              >
                <Languages size={14} className="mr-1.5" />
                {lang === "zh" ? "中文" : "EN"}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="rounded-xl">
              <DropdownMenuItem data-testid="lang-set-en" onClick={() => setLang("en")}>
                English
              </DropdownMenuItem>
              <DropdownMenuItem data-testid="lang-set-zh" onClick={() => setLang("zh")}>
                简体中文
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          {user ? (
            <Button
              variant="secondary"
              size="sm"
              data-testid="header-sign-out"
              onClick={logout}
              className="rounded-full h-9 px-3 bg-white/90 border border-white/70"
            >
              {t("sign_out")}
            </Button>
          ) : (
            <Button
              size="sm"
              data-testid="header-sign-in"
              onClick={() => setAuthOpen(true)}
              className="rounded-full h-9 px-3 bg-zinc-900 hover:bg-zinc-800"
            >
              {t("sign_in")}
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}

function MobileLangFab() {
  const { lang, setLang } = useI18n();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          data-testid="mobile-lang-trigger"
          className="md:hidden fixed top-3 right-3 z-[55] w-9 h-9 rounded-full bg-white/95 backdrop-blur-xl border border-white/70 shadow grid place-items-center"
          aria-label="language"
        >
          <Languages size={14} />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="rounded-xl">
        <DropdownMenuItem onClick={() => setLang("en")}>English</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setLang("zh")}>简体中文</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Shell() {
  return (
    <>
      <DesktopHeader />
      <Routes>
        <Route path="/" element={<Explore />} />
        <Route path="/favorites" element={<Favorites />} />
        <Route path="/account" element={<Account />} />
      </Routes>
      <BottomNav />
      <AuthDialog />
      <Toaster position="top-center" richColors />
    </>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <BrowserRouter>
          <Shell />
        </BrowserRouter>
      </AuthProvider>
    </I18nProvider>
  );
}
