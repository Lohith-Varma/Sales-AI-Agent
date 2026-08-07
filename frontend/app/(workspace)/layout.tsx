import { AppShell } from "@/components/shell/app-shell";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <AppShell><div id="main-content" tabIndex={-1}>{children}</div></AppShell>;
}
