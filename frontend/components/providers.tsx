"use client";

import { QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";
import { toast, Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: { staleTime: 30_000, gcTime: 5 * 60_000, retry: (count, error) => count < 2 && !(error instanceof Error && "status" in error && error.status === 404), refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
    queryCache: new QueryCache({ onError: (error, query) => { if (query.state.data !== undefined) toast.error("Could not refresh data", { description: error.message }); } }),
  }));

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={300}>
          {children}
          <Toaster richColors closeButton position="bottom-right" toastOptions={{ className: "font-sans" }} />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
