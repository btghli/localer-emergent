import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authApi } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authOpen, setAuthOpen] = useState(false);

  useEffect(() => {
    const t = localStorage.getItem("localer_token");
    if (!t) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("localer_token");
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const r = await authApi.login({ email, password });
    localStorage.setItem("localer_token", r.token);
    setUser(r.user);
    return r.user;
  }, []);

  const register = useCallback(async (email, password, name) => {
    const r = await authApi.register({ email, password, name });
    localStorage.setItem("localer_token", r.token);
    setUser(r.user);
    return r.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("localer_token");
    setUser(null);
  }, []);

  const updateSettings = useCallback(async (data) => {
    const u = await authApi.updateSettings(data);
    setUser(u);
    return u;
  }, []);

  return (
    <AuthCtx.Provider
      value={{ user, loading, login, register, logout, updateSettings, authOpen, setAuthOpen }}
    >
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
