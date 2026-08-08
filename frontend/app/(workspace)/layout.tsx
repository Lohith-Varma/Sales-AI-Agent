import { AppShell } from "@/components/shell/app-shell";
import { AuthGate } from "@/components/auth/auth-gate";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate><AppShell><div id="main-content" tabIndex={-1}>{children}</div></AppShell></AuthGate>;
}
