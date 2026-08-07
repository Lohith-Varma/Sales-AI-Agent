import type { Metadata } from "next";
import { KnowledgePage } from "@/features/knowledge/knowledge-page";

export const metadata: Metadata = { title: "Knowledge Base" };
export default function Page() { return <KnowledgePage />; }
