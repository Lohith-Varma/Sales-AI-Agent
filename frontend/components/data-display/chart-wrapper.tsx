import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ChartWrapper({ title, description, action, children, className }: { title: string; description: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <Card className={className}><CardHeader className="flex-row items-start justify-between gap-4"><div><CardTitle>{title}</CardTitle><CardDescription className="mt-1">{description}</CardDescription></div>{action}</CardHeader><CardContent>{children}</CardContent></Card>;
}
