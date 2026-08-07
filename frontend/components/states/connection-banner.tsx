"use client";

import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

export function ConnectionBanner() {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    setOnline(navigator.onLine);
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);
  if (online) return null;
  return <div className="flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-xs font-semibold text-amber-950" role="status"><WifiOff className="size-3.5" />You are offline. Changes that require the backend are paused.</div>;
}
