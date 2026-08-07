"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Filter, Loader2, Plus, Search, SlidersHorizontal, UserRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { PageHeader } from "@/components/states/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { ErrorState, StatePanel } from "@/components/states/state-panel";
import { coreApi, queryKeys } from "@/lib/api/client";
import { CustomerDrawer } from "@/features/crm/customer-drawer";

const lookupSchema = z.object({ customerId: z.string().trim().min(1, "Enter a customer ID.") });
const createSchema = z.object({ name: z.string().trim().min(2, "Enter the customer's name."), phone_number: z.string().trim().min(8, "Enter a valid phone number."), email: z.string().trim().email("Enter a valid email.").optional().or(z.literal("")), salary: z.coerce.number().positive().optional().or(z.literal("")) });
type LookupInput = z.infer<typeof lookupSchema>;
type CreateInput = z.input<typeof createSchema>;

export function CRMPage() {
  const queryClient = useQueryClient();
  const [requestedId, setRequestedId] = useState("");
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const lookup = useForm<LookupInput>({ resolver: zodResolver(lookupSchema), defaultValues: { customerId: "" } });
  const create = useForm<CreateInput>({ resolver: zodResolver(createSchema), defaultValues: { name: "", phone_number: "", email: "", salary: "" } });
  const customer = useQuery({ queryKey: queryKeys.customer(requestedId), queryFn: () => coreApi.customer(requestedId), enabled: Boolean(requestedId), retry: false });
  const createCustomer = useMutation({ mutationFn: (input: CreateInput) => { const parsed = createSchema.parse(input); return coreApi.createCustomer({ ...parsed, email: parsed.email || undefined, salary: parsed.salary === "" ? undefined : parsed.salary }); }, onSuccess: (response) => { toast.success("Customer created", { description: response.data.name }); setCreateOpen(false); create.reset(); setRequestedId(response.data.customer_id); lookup.setValue("customerId", response.data.customer_id); void queryClient.invalidateQueries({ queryKey: queryKeys.customer(response.data.customer_id) }); }, onError: (error) => toast.error("Customer could not be created", { description: error.message }) });
  const onLookup = ({ customerId }: LookupInput) => { setRequestedId(customerId); setDetailsOpen(true); };

  return <div className="space-y-7"><PageHeader eyebrow="Customer workspace" title="CRM" description="Create customer records or retrieve an exact record by ID. Lead-list, filters, assignment, and CRM writing APIs are not present in the backend." actions={<Button onClick={() => setCreateOpen(true)}><Plus />New customer</Button>} />
    <Card><CardHeader><CardTitle>Find a customer</CardTitle><CardDescription>The core API supports one record at a time; it does not expose a paginated lead list.</CardDescription></CardHeader><CardContent><form onSubmit={lookup.handleSubmit(onLookup)} className="flex flex-col gap-2 sm:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input {...lookup.register("customerId")} className="pl-9" placeholder="Enter the exact customer UUID" aria-label="Customer ID" /></div><Button type="submit" disabled={customer.isFetching}>{customer.isFetching ? <Loader2 className="animate-spin" /> : <Search />}Open record</Button></form>{lookup.formState.errors.customerId ? <p className="mt-2 text-xs text-red-600">{lookup.formState.errors.customerId.message}</p> : null}</CardContent></Card>
    <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"><Button variant="secondary" disabled><Filter />Status</Button><Button variant="secondary" disabled><SlidersHorizontal />Stage</Button><Button variant="secondary" disabled>Assigned agent</Button><Button variant="secondary" disabled>Last contact</Button><span className="ml-auto text-[11px] text-slate-400">Filters require a lead-list endpoint</span></div>
    {customer.isError ? <ErrorState title="Customer lookup failed" description={customer.error.message} retry={() => void customer.refetch()} /> : customer.data ? <Card className="overflow-hidden"><button onClick={() => setDetailsOpen(true)} className="flex w-full items-center gap-4 p-5 text-left hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500 dark:hover:bg-slate-800/50"><div className="grid size-11 place-items-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"><UserRound className="size-5" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{customer.data.data.name}</p><p className="mt-1 truncate text-xs text-slate-500">{customer.data.data.phone} · {customer.data.data.city}</p></div><span className="text-xs font-medium text-blue-600">View details</span></button></Card> : <StatePanel title="No lead list is available" description="Search for a known customer ID above. A list view cannot be populated until the backend adds pagination and filters." icon={UserRound} className="min-h-72" />}
    <CustomerDrawer customer={customer.data?.data ?? null} open={detailsOpen && Boolean(customer.data)} onOpenChange={setDetailsOpen} requestedId={requestedId} />
    <Sheet open={createOpen} onOpenChange={setCreateOpen}><SheetContent title="Create customer"><div className="pr-10"><h2 className="text-xl font-semibold">Create customer</h2><p className="mt-1 text-sm text-slate-500">This writes directly to the core customer API. Salary is sent only when provided.</p><form onSubmit={create.handleSubmit((input) => createCustomer.mutate(input))} className="mt-6 space-y-4"><Field label="Full name" error={create.formState.errors.name?.message}><Input {...create.register("name")} autoFocus /></Field><Field label="Phone number" error={create.formState.errors.phone_number?.message}><Input {...create.register("phone_number")} inputMode="tel" /></Field><Field label="Email (optional)" error={create.formState.errors.email?.message}><Input {...create.register("email")} type="email" /></Field><Field label="Salary (optional)" error={create.formState.errors.salary?.message as string | undefined}><Input {...create.register("salary")} type="number" min="0" step="0.01" /></Field><div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300">Authentication is not enforced by the current backend. Do not expose this write route publicly until server authorization is implemented.</div><Button className="w-full" type="submit" disabled={createCustomer.isPending}>{createCustomer.isPending ? <Loader2 className="animate-spin" /> : <Plus />}Create customer</Button></form></div></SheetContent></Sheet>
  </div>;
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) { return <div className="space-y-1.5"><Label>{label}</Label>{children}{error ? <p className="text-xs text-red-600">{error}</p> : null}</div>; }
