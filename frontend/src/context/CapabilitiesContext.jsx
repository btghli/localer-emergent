import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { contentApi } from "@/lib/api";

const CapabilitiesCtx = createContext(null);

export function CapabilitiesProvider({ children }) {
  const [capabilities, setCapabilities] = useState({ ai: false });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    contentApi
      .capabilities()
      .then((result) => {
        if (!cancelled) setCapabilities({ ai: result?.ai === true });
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({ aiEnabled: capabilities.ai, loading }),
    [capabilities.ai, loading]
  );

  return <CapabilitiesCtx.Provider value={value}>{children}</CapabilitiesCtx.Provider>;
}

export function useCapabilities() {
  const value = useContext(CapabilitiesCtx);
  if (!value) throw new Error("useCapabilities must be inside CapabilitiesProvider");
  return value;
}
