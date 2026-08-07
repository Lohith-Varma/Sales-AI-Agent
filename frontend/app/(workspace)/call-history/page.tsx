import type { Metadata } from "next";
import { CallHistoryPage } from "@/features/calls/call-history-page";

export const metadata: Metadata = { title: "Call History" };
export default function Page() { return <CallHistoryPage />; }
