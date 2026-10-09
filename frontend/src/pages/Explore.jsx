import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import MapView from "@/components/MapView";
import CategoryFilters from "@/components/CategoryFilters";
import SearchBar from "@/components/SearchBar";
import ItemCard from "@/components/ItemCard";
import ItemDetail from "@/components/ItemDetail";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/context/I18nContext";
import { useAuth } from "@/context/AuthContext";
import { contentApi, favApi } from "@/lib/api";
import { CATEGORIES } from "@/lib/categories";
import { Loader2, Navigation, LocateFixed, RefreshCw, Search } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

const DEFAULT_CENTER = { lat: 40.7128, lng: -74.006 }; // NYC fallback

export default function Explore() {
  const { lang, t } = useI18n();
  const { user } = useAuth();

  const [center, setCenter] = useState(null); // active search center
  const [mapCenter, setMapCenter] = useState(null); // current camera center
  const [flyKey, setFlyKey] = useState(0);
  const [zoom, setZoom] = useState(14);
  const [userLoc, setUserLoc] = useState(null);
  const [locationDenied, setLocationDenied] = useState(false);
  const [showMoveBtn, setShowMoveBtn] = useState(false);

  const [activeCats, setActiveCats] = useState(new Set(CATEGORIES.map((c) => c.key)));
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [favKeys, setFavKeys] = useState(new Set());

  const reqIdRef = useRef(0);

  // Initial location
  useEffect(() => {
    if (!("geolocation" in navigator)) {
      setLocationDenied(true);
      setCenter(DEFAULT_CENTER);
      setFlyKey((k) => k + 1);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setUserLoc(loc);
        setCenter(loc);
        setFlyKey((k) => k + 1);
      },
      () => {
        setLocationDenied(true);
        setCenter(DEFAULT_CENTER);
        setFlyKey((k) => k + 1);
      },
      { enableHighAccuracy: false, timeout: 7000, maximumAge: 60000 }
    );
  }, []);

  // Favorites keys
  useEffect(() => {
    if (!user) {
      setFavKeys(new Set());
      return;
    }
    favApi
      .list()
      .then((list) => setFavKeys(new Set(list.map((i) => i.externalId))))
      .catch(() => {});
  }, [user]);

  const fetchNearby = useCallback(
    async (c) => {
      if (!c) return;
      const id = ++reqIdRef.current;
      setLoading(true);
      setError(null);
      try {
        const cats = Array.from(activeCats);
        const data = await contentApi.nearby(c.lat, c.lng, 3500, cats);
        if (id !== reqIdRef.current) return;
        setItems(data || []);
        setShowMoveBtn(false);
      } catch (e) {
        if (id !== reqIdRef.current) return;
        setError(e?.message || "Failed");
        setItems([]);
      } finally {
        if (id === reqIdRef.current) setLoading(false);
      }
    },
    [activeCats]
  );

  useEffect(() => {
    if (center) fetchNearby(center);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center?.lat, center?.lng, activeCats]);

  const onMapMoveEnd = (c, z) => {
    setMapCenter({ lat: c.lat, lng: c.lng });
    setZoom(z);
    if (!center) return;
    const dLat = Math.abs(center.lat - c.lat);
    const dLng = Math.abs(center.lng - c.lng);
    if (dLat > 0.004 || dLng > 0.004) setShowMoveBtn(true);
  };

  const onSearchArea = () => {
    if (!mapCenter) return;
    setCenter(mapCenter);
  };

  const onRecenter = () => {
    if (!userLoc) {
      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            setUserLoc(loc);
            setCenter(loc);
            setFlyKey((k) => k + 1);
          },
          () => toast.error(t("location_denied_title"))
        );
      }
      return;
    }
    setCenter(userLoc);
    setFlyKey((k) => k + 1);
  };

  const toggleCat = (key) => {
    setActiveCats((s) => {
      const n = new Set(s);
      if (n.has(key)) n.delete(key);
      else n.add(key);
      if (n.size === 0) return new Set(CATEGORIES.map((c) => c.key));
      return n;
    });
  };

  const allCats = () => setActiveCats(new Set(CATEGORIES.map((c) => c.key)));

  const onPickPlace = (p) => {
    setCenter({ lat: p.lat, lng: p.lng });
    setFlyKey((k) => k + 1);
    setZoom(14);
  };

  const toggleFav = (key, isFav) => {
    setFavKeys((s) => {
      const n = new Set(s);
      if (isFav) n.add(key);
      else n.delete(key);
      return n;
    });
  };

  const notOnMyLocation = useMemo(() => {
    if (!userLoc || !mapCenter) return false;
    const d =
      Math.abs(userLoc.lat - mapCenter.lat) + Math.abs(userLoc.lng - mapCenter.lng);
    return d > 0.005;
  }, [userLoc, mapCenter]);

  const listNode = (
    <div className="flex flex-col h-full">
      <div className="px-3 pt-3 pb-2 shrink-0 hidden md:block">
        <SearchBar onPick={onPickPlace} />
      </div>
      <div className="px-3 pt-3 md:pt-1 pb-2 shrink-0">
        <CategoryFilters active={activeCats} onToggle={toggleCat} onAll={allCats} />
      </div>
      <div className="px-3 pb-2 flex items-center justify-between shrink-0">
        <div>
          <p className="text-[11px] uppercase tracking-wide font-semibold text-zinc-500">
            {t("nearby")}
          </p>
          <p className="text-sm text-zinc-800 font-medium">
            {loading ? t("loading_nearby") : `${items.length} ${lang === "zh" ? "项" : "results"}`}
          </p>
        </div>
      </div>
      <div
        className="flex-1 overflow-y-auto nice-scroll px-3 pb-20 md:pb-4 space-y-2"
        data-testid="nearby-list"
      >
        {loading && items.length === 0 && (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="rounded-2xl p-3 flex gap-3 bg-white/90 border border-white/70"
              >
                <Skeleton className="w-20 h-20 rounded-xl" />
                <div className="flex-1 space-y-2 py-1">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        )}
        {!loading && items.length === 0 && !error && (
          <div className="text-sm text-zinc-600 bg-white/80 rounded-xl p-4 border border-white/70">
            {t("no_results")}
          </div>
        )}
        {error && (
          <div className="text-sm text-rose-700 bg-rose-50 rounded-xl p-4 border border-rose-200 flex items-center justify-between">
            <span>Oops: {String(error)}</span>
            <button
              onClick={() => fetchNearby(center)}
              className="text-rose-800 underline inline-flex items-center gap-1"
            >
              <RefreshCw size={13} /> {t("retry")}
            </button>
          </div>
        )}
        {items.map((it) => (
          <ItemCard
            key={it.id}
            item={it}
            selected={selected?.id === it.id}
            onClick={(x) => {
              setSelected(x);
              setCenter((c) => c); // keep
            }}
          />
        ))}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 overflow-hidden">
      <MapView
        center={center}
        flyToKey={flyKey}
        zoom={zoom}
        userLocation={userLoc}
        items={items}
        selectedId={selected?.id}
        onSelect={(x) => setSelected(x)}
        onMoveEnd={onMapMoveEnd}
        onBackgroundClick={() => {}}
      />

      {/* Search bar — desktop lives inside discovery panel; mobile floats at top */}
      <div className="md:hidden fixed top-3 left-3 right-14 z-40">
        <SearchBar onPick={onPickPlace} />
      </div>

      {/* "Search this area" button */}
      {showMoveBtn && (
        <div className="fixed top-16 md:top-20 left-1/2 md:left-[432px] -translate-x-1/2 md:translate-x-0 z-[45] pointer-events-auto">
          <Button
            type="button"
            onClick={onSearchArea}
            data-testid="search-this-area-btn"
            className="rounded-full bg-zinc-900 hover:bg-zinc-800 text-white shadow-lg h-10 px-4"
          >
            <Search size={14} className="mr-1.5" />
            {t("search_this_area")}
          </Button>
        </div>
      )}

      {/* Floating recenter button */}
      {notOnMyLocation && (
        <button
          type="button"
          onClick={onRecenter}
          data-testid="recenter-btn"
          aria-label={t("recenter")}
          className="fixed bottom-24 md:bottom-8 right-4 md:right-8 z-40 w-12 h-12 rounded-full bg-white/95 backdrop-blur-xl shadow-[0_8px_24px_rgba(0,0,0,0.15)] grid place-items-center border border-white/70 hover:bg-white"
        >
          <LocateFixed size={18} className="text-zinc-800" />
        </button>
      )}

      {/* Loading indicator top */}
      {loading && items.length > 0 && (
        <div className="fixed top-3 right-3 md:top-6 md:right-6 z-40">
          <div className="bg-white/90 backdrop-blur-xl rounded-full px-3 py-1.5 shadow border border-white/70 inline-flex items-center gap-1.5 text-xs text-zinc-700">
            <Loader2 size={12} className="animate-spin" /> {t("loading_nearby")}
          </div>
        </div>
      )}

      {/* Location-denied banner */}
      {locationDenied && (
        <div className="fixed top-20 md:top-20 right-4 md:right-auto md:left-[432px] z-[44] pointer-events-auto">
          <div
            data-testid="location-denied-banner"
            className="max-w-sm bg-white/95 backdrop-blur-xl border border-amber-200 rounded-2xl shadow-lg px-4 py-3 text-sm text-zinc-800"
          >
            <p className="font-display font-semibold mb-0.5">{t("location_denied_title")}</p>
            <p className="text-xs text-zinc-600">{t("location_denied_body")}</p>
          </div>
        </div>
      )}

      {/* Desktop discovery panel */}
      <aside
        className="hidden md:flex fixed left-4 top-20 bottom-4 w-[400px] z-30 pointer-events-auto rounded-3xl bg-white/85 backdrop-blur-2xl border border-white/70 shadow-[0_12px_40px_rgba(0,0,0,0.12)] overflow-hidden"
        aria-label="Discovery panel"
      >
        {listNode}
      </aside>

      {/* Mobile bottom sheet */}
      <div
        className="md:hidden fixed bottom-16 left-0 right-0 top-16 z-30 pointer-events-none"
        aria-hidden="true"
      ></div>
      <div className="md:hidden fixed bottom-16 inset-x-0 z-30 pointer-events-auto">
        <MobileSheet>{listNode}</MobileSheet>
      </div>

      {/* Item detail */}
      {/* Desktop side panel */}
      {selected && (
        <aside
          data-testid="desktop-detail-panel"
          className="hidden md:flex fixed right-4 top-20 bottom-4 w-[460px] z-40 rounded-3xl overflow-hidden bg-white/95 backdrop-blur-2xl border border-white/70 shadow-[0_12px_40px_rgba(0,0,0,0.18)]"
        >
          <ItemDetail
            item={selected}
            onClose={() => setSelected(null)}
            favorites={favKeys}
            onToggleFavorite={toggleFav}
          />
        </aside>
      )}

      {/* Mobile detail sheet */}
      <Sheet open={!!selected && window.matchMedia("(max-width: 767px)").matches} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent
          side="bottom"
          className="md:hidden h-[88vh] rounded-t-3xl p-0 border-none"
          data-testid="mobile-detail-sheet"
        >
          {selected && (
            <ItemDetail
              item={selected}
              onClose={() => setSelected(null)}
              favorites={favKeys}
              onToggleFavorite={toggleFav}
            />
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function MobileSheet({ children }) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useI18n();
  return (
    <div
      className="mx-2 mb-1 rounded-t-3xl bg-white/95 backdrop-blur-2xl border border-white/70 shadow-[0_-8px_30px_rgba(0,0,0,0.12)] overflow-hidden transition-[height] duration-300"
      style={{ height: expanded ? "60vh" : "180px" }}
    >
      <button
        type="button"
        data-testid="mobile-sheet-handle"
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex flex-col items-center py-2"
        aria-label="Toggle nearby list"
      >
        <div className="w-10 h-1 rounded-full bg-zinc-300" />
        <span className="text-[11px] uppercase tracking-wide font-semibold text-zinc-500 mt-1">
          {t("nearby")}
        </span>
      </button>
      <div className="h-[calc(100%-40px)]">{children}</div>
    </div>
  );
}
