import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatePanel } from "@/components/states/state-panel";

export default function NotFound() { return <main className="grid min-h-screen place-items-center bg-slate-50 p-6"><div className="w-full max-w-xl"><StatePanel title="Page not found" description="The workspace page you requested does not exist." action={undefined} /><Button asChild className="mx-auto mt-4 flex w-fit"><Link href="/dashboard"><ArrowLeft />Back to dashboard</Link></Button></div></main>; }
