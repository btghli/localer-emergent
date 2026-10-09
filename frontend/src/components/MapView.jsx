import React, { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { renderToStaticMarkup } from "react-dom/server";
import { CAT_MAP, catColor } from "@/lib/categories";
import { Navigation } from "lucide-react";

function buildCategoryIcon(category, isSelected) {
  const CatInfo = CAT_MAP[category];
  const Icon = CatInfo?.icon;
  const color = catColor(category);
  const svg = Icon
    ? renderToStaticMarkup(<Icon size={16} color="#ffffff" strokeWidth={2.4} />)
    : "";
  const scale = isSelected ? 1.15 : 1;
  const html = `
    <div style="position:relative;transform:translate(-50%,-100%) scale(${scale});transition:transform .18s ease;">
      <div style="width:36px;height:36px;border-radius:999px;background:${color};
        box-shadow:0 6px 18px rgba(0,0,0,.25),0 0 0 3px rgba(255,255,255,.95);
        display:flex;align-items:center;justify-content:center;">${svg}</div>
      <div style="position:absolute;left:50%;bottom:-6px;transform:translateX(-50%);
        width:0;height:0;border-left:7px solid transparent;border-right:7px solid transparent;
        border-top:9px solid ${color};"></div>
    </div>`;
  return L.divIcon({
    html,
    className: "localer-marker",
    iconSize: [36, 44],
    iconAnchor: [18, 44],
  });
}

function userLocationIcon() {
  const html = `
    <div style="position:relative;width:18px;height:18px;transform:translate(-50%,-50%);">
      <div class="loc-pulse" style="position:absolute;inset:0;border-radius:999px;background:#2563eb;opacity:.4;"></div>
      <div style="position:absolute;inset:0;border-radius:999px;background:#2563eb;border:3px solid #fff;box-shadow:0 0 0 1px #2563eb33;"></div>
    </div>`;
  return L.divIcon({ html, className: "localer-user", iconSize: [18, 18], iconAnchor: [9, 9] });
}

function MapEvents({ onMoveEnd, onClick }) {
  useMapEvents({
    moveend: (e) => onMoveEnd && onMoveEnd(e.target.getCenter(), e.target.getZoom()),
    click: () => onClick && onClick(),
  });
  return null;
}

function Controller({ center, zoom, flyToKey }) {
  const map = useMap();
  useEffect(() => {
    // Only move the camera for an explicit recenter/place-selection action.
    // Depending on center/zoom here makes a user zoom emit moveend, update the
    // React zoom state, and then snap the map back to the previous search
    // center.  Search-this-area already has the camera in the right place.
    if (center && flyToKey > 0) {
      map.flyTo([center.lat, center.lng], zoom ?? map.getZoom(), { duration: 0.6 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flyToKey]);
  return null;
}

export default function MapView({
  center,
  zoom = 14,
  userLocation,
  items,
  selectedId,
  onSelect,
  onMoveEnd,
  onBackgroundClick,
  flyToKey,
}) {
  // Leaflet owns camera movement after mount; keep only the first center here
  // and route later programmatic moves through Controller.
  const defaultCenter = useRef(center || userLocation || { lat: 40.7128, lng: -74.006 }).current;
  const mapRef = useRef(null);

  return (
    <MapContainer
      center={[defaultCenter.lat, defaultCenter.lng]}
      zoom={zoom}
      zoomControl={false}
      className="absolute inset-0 z-0"
      ref={mapRef}
      preferCanvas={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
      />

      <Controller center={center} zoom={zoom} flyToKey={flyToKey} />
      <MapEvents onMoveEnd={onMoveEnd} onClick={onBackgroundClick} />

      {userLocation && (
        <Marker
          position={[userLocation.lat, userLocation.lng]}
          icon={userLocationIcon()}
          interactive={false}
        />
      )}

      {items?.filter((it) => it.latitude != null && it.longitude != null).map((it) => (
        <Marker
          key={it.id}
          position={[it.latitude, it.longitude]}
          icon={buildCategoryIcon(it.category, selectedId === it.id)}
          eventHandlers={{
            click: () => onSelect && onSelect(it),
          }}
          keyboard
          alt={`${it.category}: ${it.title}`}
        />
      ))}
    </MapContainer>
  );
}

export { Navigation };
