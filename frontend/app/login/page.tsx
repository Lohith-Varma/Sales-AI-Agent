"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, LockKeyhole } from "lucide-react";
import { authApi, setAccessToken } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setLoading(true); setError("");
    try { const result = await authApi.login(email, password); setAccessToken(result.access_token); router.replace("/live-calls"); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Sign-in failed."); }
    finally { setLoading(false); }
  };
  return <main className="grid min-h-screen place-items-center bg-slate-50 p-5 dark:bg-slate-950"><Card className="w-full max-w-md p-7"><div className="grid size-11 place-items-center rounded-2xl bg-blue-600 text-white"><LockKeyhole className="size-5" /></div><h1 className="mt-5 text-2xl font-semibold">Sign in</h1><p className="mt-2 text-sm text-slate-500">Use an authorized sales workspace account.</p><form onSubmit={submit} className="mt-6 space-y-4"><div className="space-y-1.5"><Label htmlFor="email">Email</Label><Input id="email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></div><div className="space-y-1.5"><Label htmlFor="password">Password</Label><Input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></div>{error ? <p className="rounded-xl bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">{error}</p> : null}<Button className="w-full" type="submit" disabled={loading}>{loading ? <Loader2 className="animate-spin" /> : <LockKeyhole />}Sign in</Button></form></Card></main>;
}
