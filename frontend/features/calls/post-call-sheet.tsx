"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  Save,
} from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Input, Textarea } from "@/components/ui/input";
import type { CopilotResult, CRMSummary } from "@/lib/api/contracts";
import { coreApi, queryKeys } from "@/lib/api/client";
import { titleCase } from "@/lib/utils";

const schema = z
  .object({
    summary: z.string().trim().min(10, "Add a meaningful call summary."),
    outcome: z.enum(["Converted", "Follow-up needed", "Dropped"]),
    productName: z.string(),
    amount: z.number().min(0),
  })
  .superRefine((value, context) => {
    if (value.outcome !== "Converted") return;
    if (!value.productName)
      context.addIssue({ code: "custom", path: ["productName"], message: "Select the purchased product." });
    if (value.amount <= 0)
      context.addIssue({ code: "custom", path: ["amount"], message: "Enter the completed sale amount." });
  });
type FormValues = z.infer<typeof schema>;

export function PostCallSheet({
  open,
  onOpenChange,
  callId,
  crmSummary,
  latestResult,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  callId: string;
  crmSummary: CRMSummary | null;
  latestResult: CopilotResult | null;
}) {
  const products = useQuery({ queryKey: queryKeys.products, queryFn: coreApi.products });
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { summary: "", outcome: "Follow-up needed", productName: "", amount: 0 },
  });
  const outcome = form.watch("outcome");
  useEffect(() => {
    if (!crmSummary) return;
    form.reset({
      summary: crmSummary.call_summary,
      outcome:
        crmSummary.lead_status === "not_interested" ||
        crmSummary.lead_status === "disqualified"
          ? "Dropped"
          : "Follow-up needed",
      productName: form.getValues("productName"),
      amount: form.getValues("amount"),
    });
  }, [crmSummary, form]);
  useEffect(() => {
    if (!form.getValues("productName") && products.data?.data[0])
      form.setValue("productName", products.data.data[0].name);
  }, [form, products.data]);
  const wrapUp = useMutation({
    mutationFn: async (values: FormValues) => {
      if (values.outcome === "Converted") {
        await coreApi.completeSale(callId, {
          product_name: values.productName,
          offer_name: values.productName,
          amount: values.amount,
          currency: "INR",
          summary: values.summary,
        });
        return;
      }
      await coreApi.wrapUp(callId, values.summary, values.outcome);
    },
    onSuccess: (_, values) => {
      toast.success(values.outcome === "Converted" ? "Sale and CRM updates completed" : "Call wrap-up saved");
      onOpenChange(false);
    },
    onError: (error) =>
      toast.error("Wrap-up could not be saved", { description: error.message }),
  });
  const complianceSafe = latestResult?.guardrail.is_safe ?? false;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[min(96vw,640px)]" title="Post-call wrap-up">
        <div className="pr-10">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-blue-600">
            Call complete
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">
            Post-call wrap-up
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Review AI-generated fields before writing the summary to the core
            call record.
          </p>
          {crmSummary ? (
            <div className="mt-5 grid grid-cols-2 gap-3">
              <Card className="p-3 shadow-none">
                <p className="text-[11px] text-slate-400">Lead score</p>
                <p className="mt-1 text-lg font-semibold">
                  {crmSummary.lead_score.score}/100{" "}
                  <span className="text-xs font-medium text-slate-400">
                    · {titleCase(crmSummary.lead_score.temperature)}
                  </span>
                </p>
              </Card>
              <Card className="p-3 shadow-none">
                <p className="text-[11px] text-slate-400">Lead status</p>
                <p className="mt-1 text-sm font-semibold">
                  {titleCase(crmSummary.lead_status)}
                </p>
              </Card>
            </div>
          ) : (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300">
              No AI CRM summary was received. You can still complete the core
              wrap-up manually.
            </div>
          )}
          <form
            onSubmit={form.handleSubmit((values) => wrapUp.mutate(values))}
            className="mt-5 space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="call-summary">Call summary</Label>
              <Textarea
                id="call-summary"
                {...form.register("summary")}
                className="min-h-40"
                placeholder="Summarize the conversation and agreed next step."
              />
              {form.formState.errors.summary ? (
                <p className="text-xs text-red-600">
                  {form.formState.errors.summary.message}
                </p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="call-outcome">Outcome</Label>
              <select
                id="call-outcome"
                {...form.register("outcome")}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/10 dark:border-slate-700 dark:bg-slate-900"
              >
                <option>Converted</option>
                <option>Follow-up needed</option>
                <option>Dropped</option>
              </select>
            </div>
            {outcome === "Converted" ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="sale-product">Purchased product</Label>
                  <select id="sale-product" {...form.register("productName")} className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-900">
                    <option value="">Select an approved product</option>
                    {products.data?.data.map((product) => <option key={product.id} value={product.name}>{product.name}</option>)}
                  </select>
                  {form.formState.errors.productName ? <p className="text-xs text-red-600">{form.formState.errors.productName.message}</p> : null}
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="sale-amount">Sale amount (INR)</Label>
                  <Input id="sale-amount" type="number" min="1" step="0.01" {...form.register("amount", { valueAsNumber: true })} />
                  {form.formState.errors.amount ? <p className="text-xs text-red-600">{form.formState.errors.amount.message}</p> : null}
                </div>
              </div>
            ) : null}
            <Card className="p-4 shadow-none">
              <p className="flex items-center gap-2 text-xs font-semibold">
                <ClipboardCheck className="size-4 text-blue-600" />
                Compliance review
              </p>
              <div className="mt-3 space-y-2">
                <CheckLine
                  ok={complianceSafe}
                  label="Latest suggested response passed guardrails"
                />
                <CheckLine
                  ok={Boolean(latestResult?.guardrail.is_grounded)}
                  label="Product claims are grounded in approved knowledge"
                />
                <CheckLine
                  ok={Boolean(crmSummary)}
                  label="Post-call CRM summary received for review"
                />
              </div>
              {latestResult?.guardrail.violations.length ? (
                <div className="mt-3 rounded-xl bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
                  {latestResult.guardrail.violations
                    .map((item) => item.message)
                    .join(" ")}
                </div>
              ) : null}
            </Card>
            <Button
              type="submit"
              className="w-full"
              disabled={wrapUp.isPending}
            >
              {wrapUp.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Save />
              )}
              {outcome === "Converted" ? "Complete sale and sync CRM" : "Save wrap-up"}
            </Button>
          </form>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function CheckLine({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div
      className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${ok ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300" : "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"}`}
    >
      {ok ? (
        <CheckCircle2 className="size-3.5" />
      ) : (
        <AlertTriangle className="size-3.5" />
      )}
      {label}
    </div>
  );
}
