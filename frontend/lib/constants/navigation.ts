export const navigation = [
  { label: "Dashboard", href: "/dashboard", shortcut: "G D" },
  { label: "Live Calls", href: "/live-calls", shortcut: "G L" },
  { label: "Call History", href: "/call-history", shortcut: "G H" },
  { label: "CRM", href: "/crm", shortcut: "G C" },
  { label: "Knowledge Base", href: "/knowledge-base", shortcut: "G K" },
  { label: "Analytics", href: "/analytics", shortcut: "G A" },
  { label: "Tasks", href: "/tasks", shortcut: "G T" },
  { label: "Follow Ups", href: "/follow-ups", shortcut: "G F" },
  { label: "Reports", href: "/reports", shortcut: "G R" },
  { label: "Settings", href: "/settings", shortcut: "G S" },
  { label: "Admin", href: "/admin", shortcut: "G M" },
] as const;

export type NavigationItem = (typeof navigation)[number];
