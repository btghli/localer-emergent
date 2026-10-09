import { Landmark, CalendarDays, Newspaper, UtensilsCrossed, Leaf } from "lucide-react";

export const CATEGORIES = [
  {
    key: "landmark",
    labelEn: "Landmarks",
    labelZh: "地标",
    color: "#7c3aed", // purple
    bgSoft: "bg-purple-100",
    textStrong: "text-purple-700",
    icon: Landmark,
  },
  {
    key: "event",
    labelEn: "Events",
    labelZh: "活动",
    color: "#ea580c", // orange
    bgSoft: "bg-orange-100",
    textStrong: "text-orange-700",
    icon: CalendarDays,
  },
  {
    key: "news",
    labelEn: "News",
    labelZh: "新闻",
    color: "#2563eb", // blue
    bgSoft: "bg-blue-100",
    textStrong: "text-blue-700",
    icon: Newspaper,
  },
  {
    key: "food",
    labelEn: "Food & Drink",
    labelZh: "美食",
    color: "#dc2626", // red
    bgSoft: "bg-red-100",
    textStrong: "text-red-700",
    icon: UtensilsCrossed,
  },
  {
    key: "nature",
    labelEn: "Nature",
    labelZh: "自然",
    color: "#16a34a", // green
    bgSoft: "bg-green-100",
    textStrong: "text-green-700",
    icon: Leaf,
  },
];

export const CAT_MAP = Object.fromEntries(CATEGORIES.map((c) => [c.key, c]));

export const DEMO_IMAGES = {
  landmark:
    "https://images.unsplash.com/photo-1688520820847-2d0c81c464ea?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzOTB8MHwxfHNlYXJjaHwxfHxoaXN0b3JpYyUyMGxhbmRtYXJrfGVufDB8fHx8MTc5MTU2NTkzNXww&ixlib=rb-4.1.0&q=85",
  event:
    "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzR8MHwxfHNlYXJjaHwxfHxjb25jZXJ0JTIwZXZlbnR8ZW58MHx8fHwxNzkxNTY1OTM1fDA&ixlib=rb-4.1.0&q=85",
  food:
    "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1MDV8MHwxfHNlYXJjaHwxfHxyZXN0YXVyYW50JTIwZm9vZHxlbnwwfHx8fDE3OTE1NjU5MzR8MA&ixlib=rb-4.1.0&q=85",
  nature:
    "https://images.unsplash.com/photo-1758451943784-8d557e873277?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzl8MHwxfHNlYXJjaHwxfHxzY2VuaWMlMjBuYXR1cmUlMjBwYXJrfGVufDB8fHx8MTc5MTU2NTkzNXww&ixlib=rb-4.1.0&q=85",
  news:
    "https://images.unsplash.com/photo-1504711434969-e33886168f5c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2ODl8MHwxfHNlYXJjaHwxfHxsb2NhbCUyMG5ld3MlMjBuYXR1cmV8ZW58MHx8fHwxNzkxNTY1OTQxfDA&ixlib=rb-4.1.0&q=85",
};

export function catColor(k) {
  return CAT_MAP[k]?.color || "#334155";
}
