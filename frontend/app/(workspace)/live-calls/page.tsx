import type { Metadata } from "next";
import { LiveCallPage } from "@/features/calls/live-call-page";

export const metadata: Metadata = { title: "Live Calls" };
export default function Page() { return <LiveCallPage />; }
