import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/context/I18nContext";
import { favApi } from "@/lib/api";
import ItemCard from "@/components/ItemCard";
import ItemDetail from "@/components/ItemDetail";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Heart, Loader2, Trash2 } from "lucide-react";
import { CATEGORIES } from "@/lib/categories";
import CategoryFilters from "@/components/CategoryFilters";
import { toast } from "sonner";

export default function Favorites() {
  const { user, loading: authLoading, setAuthOpen } = useAuth();
  const { t } = useI18n();
  const [list, setList] = useState([]);
  const [favoritesLoading, setFavoritesLoading] = useState(false);
  const [selected, setSelected] = useState(null);
  const [cats, setCats] = useState(new Set(CATEGORIES.map((c) => c.key)));
  const [keys, setKeys] = useState(new Set());

  useEffect(() => {
    if (!user) return;
    setFavoritesLoading(true);
    favApi
      .list()
      .then((data) => {
        setList(data || []);
        setKeys(new Set((data || []).map((i) => i.externalId)));
      })
      .catch(() => setList([]))
      .finally(() => setFavoritesLoading(false));
  }, [user]);

  if (authLoading) {
    return (
      <div className="min-h-screen grid place-items-center bg-gradient-to-b from-zinc-50 to-white">
        <div className="inline-flex items-center gap-2 text-sm text-zinc-500" role="status">
          <Loader2 className="animate-spin" size={17} /> {t("restoring_session")}
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen grid place-items-center p-6 bg-gradient-to-b from-zinc-50 to-white">
        <div className="max-w-md w-full bg-white rounded-3xl border border-zinc-200 shadow-sm p-8 text-center">
          <div className="w-14 h-14 rounded-full bg-rose-50 grid place-items-center mx-auto mb-4">
            <Heart size={22} className="text-rose-600" />
          </div>
          <h2 className="font-display text-2xl font-bold text-zinc-900">
            {t("sign_in_needed_title")}
          </h2>
          <p className="text-sm text-zinc-600 mt-2">{t("sign_in_needed_body")}</p>
          <Button
            type="button"
            onClick={() => setAuthOpen(true)}
            data-testid="favorites-sign-in-btn"
            className="mt-5 w-full rounded-xl bg-zinc-900 hover:bg-zinc-800 h-11"
          >
            {t("sign_in")}
          </Button>
        </div>
      </div>
    );
  }

  const filtered = list.filter((it) => cats.has(it.category));

  const toggleFav = (key, isFav) => {
    setKeys((current) => {
      const next = new Set(current);
      if (isFav) next.add(key);
      else next.delete(key);
      return next;
    });
    setList((current) => {
      if (!isFav) return current.filter((item) => item.externalId !== key);
      if (current.some((item) => item.externalId === key)) return current;
      if (selected?.externalId === key) return [selected, ...current];
      return current;
    });
  };

  const removeFav = async (item) => {
    try {
      await favApi.remove(item.externalId);
      toggleFav(item.externalId, false);
    } catch {
      toast.error(t("favorite_remove_error"));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-white pb-24 md:pb-10">
      <div className="max-w-3xl mx-auto px-4 pt-6 md:pt-10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-[11px] uppercase tracking-wide font-semibold text-zinc-500">
              {t("app_name")}
            </p>
            <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight">
              {t("favorites")}
            </h1>
          </div>
        </div>

        <div className="mb-3">
          <CategoryFilters
            active={cats}
            onToggle={(k) =>
              setCats((s) => {
                const n = new Set(s);
                if (n.has(k)) n.delete(k);
                else n.add(k);
                if (n.size === 0) return new Set(CATEGORIES.map((c) => c.key));
                return n;
              })
            }
            onAll={() => setCats(new Set(CATEGORIES.map((c) => c.key)))}
          />
        </div>

        {favoritesLoading ? (
          <div className="flex items-center justify-center py-16 text-zinc-500">
            <Loader2 className="animate-spin mr-2" size={16} /> {t("loading_nearby")}
          </div>
        ) : list.length === 0 ? (
          <div
            data-testid="favorites-empty"
            className="text-center py-16 text-zinc-600 bg-white rounded-2xl border border-zinc-200"
          >
            <Heart size={24} className="mx-auto text-zinc-400 mb-2" />
            <p className="text-sm">{t("favorites_empty")}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div
            data-testid="favorites-filter-empty"
            className="text-center py-12 px-5 text-zinc-600 bg-white rounded-2xl border border-zinc-200"
          >
            <Heart size={24} className="mx-auto text-zinc-400 mb-2" />
            <p className="text-sm">{t("favorites_filter_empty")}</p>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setCats(new Set(CATEGORIES.map((category) => category.key)))}
              className="mt-4 rounded-full border border-zinc-200 bg-white"
            >
              {t("show_all_favorites")}
            </Button>
          </div>
        ) : (
          <div className="space-y-2" data-testid="favorites-list">
            {filtered.map((it) => (
              <div key={it.id} className="relative">
                <ItemCard item={it} onClick={setSelected} />
                <button
                  type="button"
                  data-testid={`favorites-remove-${it.externalId}`}
                  onClick={() => removeFav(it)}
                  className="absolute top-2 right-2 w-8 h-8 rounded-full bg-white border border-zinc-200 grid place-items-center shadow-sm hover:bg-rose-50 hover:border-rose-200"
                  aria-label={t("remove")}
                >
                  <Trash2 size={14} className="text-rose-600" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
          <SheetContent side="bottom" className="h-[88vh] rounded-t-3xl p-0 border-none max-w-2xl md:left-1/2 md:-translate-x-1/2">
            <ItemDetail
              item={selected}
              onClose={() => setSelected(null)}
              favorites={keys}
              onToggleFavorite={toggleFav}
            />
          </SheetContent>
        </Sheet>
      )}
    </div>
  );
}
