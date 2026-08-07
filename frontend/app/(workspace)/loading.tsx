import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() { return <div className="space-y-6" aria-busy="true" aria-label="Loading page"><div className="space-y-2"><Skeleton className="h-8 w-56" /><Skeleton className="h-4 w-[min(90%,520px)]" /></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-32 rounded-2xl" />)}</div><Skeleton className="h-80 rounded-2xl" /></div>; }
