"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { authApi, clearAccessToken, coreApi, getAccessToken } from "@/lib/api/client";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const health = useQuery({ queryKey: ["auth", "configuration"], queryFn: coreApi.health, staleTime: 60_000 });
  const authRequired = health.data?.data.auth_required === true;
  const hasToken = Boolean(getAccessToken());
  const identity = useQuery({ queryKey: ["auth", "me"], queryFn: authApi.me, enabled: authRequired && hasToken, retry: false });

  useEffect(() => {
    if (!authRequired) return;
    if (!hasToken || identity.isError) {
      clearAccessToken();
      router.replace("/login");
    }
  }, [authRequired, hasToken, identity.isError, router]);

  if (health.isLoading || (authRequired && (!hasToken || identity.isLoading || identity.isError))) {
    return <div className="grid min-h-screen place-items-center bg-slate-50 text-slate-500 dark:bg-slate-950"><Loader2 className="size-6 animate-spin" aria-label="Checking workspace access" /></div>;
  }
  return children;
}
