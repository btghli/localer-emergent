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

export function catColor(k) {
  return CAT_MAP[k]?.color || "#334155";
}
