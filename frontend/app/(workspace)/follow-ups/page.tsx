import type { Metadata } from "next";
import { FollowUpsPage } from "@/features/operations/follow-ups-page";

export const metadata: Metadata = { title: "Follow Ups" };
export default function Page() { return <FollowUpsPage />; }
