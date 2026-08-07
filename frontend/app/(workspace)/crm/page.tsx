import type { Metadata } from "next";
import { CRMPage } from "@/features/crm/crm-page";

export const metadata: Metadata = { title: "CRM" };
export default function Page() { return <CRMPage />; }
