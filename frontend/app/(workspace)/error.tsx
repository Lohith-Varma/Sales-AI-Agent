"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/states/state-panel";

export default function WorkspaceError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return <ErrorState title="This page could not be rendered" description="The workspace recovered the rest of your session. Try this page again." retry={reset} className="min-h-[50vh]" />;
}
