import axios from "axios";

const BASE = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
// Support both split frontend/backend development and a conventional
// same-origin production deployment. An unset variable must never produce
// requests to the literal URL "undefined/api".
export const API = BASE ? `${BASE}/api` : "/api";

export const http = axios.create({ baseURL: API, timeout: 20000 });

http.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("localer_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export const authApi = {
  register: (data) => http.post("/auth/register", data).then((r) => r.data),
  login: (data) => http.post("/auth/login", data).then((r) => r.data),
  me: () => http.get("/auth/me").then((r) => r.data),
  updateSettings: (data) => http.patch("/auth/settings", data).then((r) => r.data),
};

export const contentApi = {
  providers: () => http.get("/providers").then((r) => r.data),
  nearby: (lat, lng, radius, cats, signal) =>
    http
      .get("/nearby", {
        params: { lat, lng, radius, categories: cats?.join(",") },
        signal,
      })
      .then((r) => r.data),
  geocode: (q, signal) => http.get("/geocode", { params: { q }, signal }).then((r) => r.data),
  ask: (item, question, language) =>
    http.post("/ai/ask", { item, question, language }).then((r) => r.data),
  translate: (text, target) =>
    http.post("/ai/translate", { text, target }).then((r) => r.data),
};

export const favApi = {
  list: () => http.get("/favorites").then((r) => r.data),
  add: (item) => http.post("/favorites", { item }).then((r) => r.data),
  remove: (key) => http.delete(`/favorites/${encodeURIComponent(key)}`).then((r) => r.data),
};
