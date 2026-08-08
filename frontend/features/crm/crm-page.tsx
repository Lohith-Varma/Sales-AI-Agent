"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Search, UserRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { PageHeader } from "@/components/states/page-header";
import { ErrorState, StatePanel } from "@/components/states/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { CustomerDrawer } from "@/features/crm/customer-drawer";
import { coreApi, queryKeys } from "@/lib/api/client";
import { titleCase } from "@/lib/utils";

const createSchema = z.object({ name: z.string().trim().min(2), phone_number: z.string().trim().min(8), email: z.string().trim().email().optional().or(z.literal("")), salary: z.coerce.number().positive().optional().or(z.literal("")) });
type CreateInput = z.input<typeof createSchema>;

export function CRMPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const create = useForm<CreateInput>({ resolver: zodResolver(createSchema), defaultValues: { name: "", phone_number: "", email: "", salary: "" } });
  const customers = useQuery({ queryKey: queryKeys.customers(search), queryFn: () => coreApi.customers(search), refetchInterval: 30_000 });
  const selected = useQuery({ queryKey: queryKeys.customer(selectedId), queryFn: () => coreApi.customer(selectedId), enabled: Boolean(selectedId), retry: false });
  const createCustomer = useMutation({ mutationFn: (input: CreateInput) => { const parsed = createSchema.parse(input); return coreApi.createCustomer({ ...parsed, email: parsed.email || undefined, salary: parsed.salary === "" ? undefined : parsed.salary }); }, onSuccess: (response) => { toast.success("Customer created", { description: response.data.name }); setCreateOpen(false); create.reset(); setSelectedId(response.data.customer_id); void queryClient.invalidateQueries({ queryKey: ["customers"] }); }, onError: (error) => toast.error("Customer could not be created", { description: error.message }) });
  const items = customers.data?.data.items ?? [];

  return <div className="space-y-7"><PageHeader eyebrow="Customer workspace" title="CRM" description="Search and open live customer, KYC, call, purchase, offer, follow-up, note, tag, stage, and lead-score records." actions={<Button onClick={() => setCreateOpen(true)}><Plus />New customer</Button>} />
    <Card className="p-4"><div className="relative"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input value={search} onChange={(event) => setSearch(event.target.value)} className="pl-9" placeholder="Search name, phone, or email" aria-label="Search customers" /></div></Card>
    {customers.isLoading ? <StatePanel title="Loading customers" description="Reading CRM records." icon={Loader2} className="min-h-72" /> : customers.isError ? <ErrorState title="Customers could not be loaded" description={customers.error.message} retry={() => void customers.refetch()} /> : items.length ? <Card className="overflow-hidden"><div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 text-xs dark:border-slate-800"><span>{customers.data?.data.total ?? items.length} customers</span><Badge variant="success">Live database</Badge></div><div className="divide-y divide-slate-100 dark:divide-slate-800">{items.map((customer) => <button key={customer.id} onClick={() => setSelectedId(customer.id)} className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-4 p-4 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50"><div className="grid size-10 place-items-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"><UserRound className="size-4" /></div><div className="min-w-0"><p className="truncate text-sm font-semibold">{customer.name}</p><p className="mt-1 truncate text-xs text-slate-500">{customer.phone}{customer.location ? ` · ${customer.location}` : ""}</p></div><div className="text-right"><Badge variant="primary">{customer.leadScore}</Badge><p className="mt-1 text-[10px] text-slate-400">{titleCase(customer.stage)}</p></div></button>)}</div></Card> : <StatePanel title="No customers found" description="Create a customer or change the search." icon={UserRound} className="min-h-72" />}
    <CustomerDrawer customer={selected.data?.data ?? null} open={Boolean(selectedId && selected.data)} onOpenChange={(open) => { if (!open) setSelectedId(""); }} requestedId={selectedId} />
    <Sheet open={createOpen} onOpenChange={setCreateOpen}><SheetContent title="Create customer"><div className="pr-10"><h2 className="text-xl font-semibold">Create customer</h2><p className="mt-1 text-sm text-slate-500">Creates the customer and opens a linked lead. KYC remains pending until verified.</p><form onSubmit={create.handleSubmit((input) => createCustomer.mutate(input))} className="mt-6 space-y-4"><Field label="Full name"><Input {...create.register("name")} autoFocus /></Field><Field label="Phone number"><Input {...create.register("phone_number")} inputMode="tel" /></Field><Field label="Email (optional)"><Input {...create.register("email")} type="email" /></Field><Field label="Salary (optional)"><Input {...create.register("salary")} type="number" min="0" step="0.01" /></Field><Button className="w-full" type="submit" disabled={createCustomer.isPending}>{createCustomer.isPending ? <Loader2 className="animate-spin" /> : <Plus />}Create customer</Button></form></div></SheetContent></Sheet>
  </div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>; }
