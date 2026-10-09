import React from "react";
import { NavLink } from "react-router-dom";
import { Compass, Heart, UserRound } from "lucide-react";
import { useI18n } from "@/context/I18nContext";

export default function BottomNav() {
  const { t } = useI18n();
  const items = [
    { to: "/", icon: Compass, label: t("explore"), testid: "nav-explore" },
    { to: "/favorites", icon: Heart, label: t("favorites"), testid: "nav-favorites" },
    { to: "/account", icon: UserRound, label: t("account"), testid: "nav-account" },
  ];
  return (
    <nav
      className="mobile-nav-safe md:hidden fixed bottom-0 inset-x-0 z-[60] pointer-events-auto"
      data-testid="bottom-nav"
    >
      <div className="mx-3 mb-3 rounded-2xl bg-white/90 backdrop-blur-xl border border-white/70 shadow-[0_8px_24px_rgba(0,0,0,0.1)] grid grid-cols-3">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <NavLink
              key={it.to}
              to={it.to}
              end={it.to === "/"}
              data-testid={it.testid}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition-colors ${
                  isActive ? "text-zinc-900" : "text-zinc-500 hover:text-zinc-800"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={18} strokeWidth={isActive ? 2.4 : 1.8} />
                  <span>{it.label}</span>
                </>
              )}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
