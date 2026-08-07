"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, CircleStop, Loader2, Mic, MicOff, PhoneCall, Send, ShieldCheck, Sparkles, Wifi, WifiOff } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { PageHeader } from "@/components/states/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { CustomerDrawer } from "@/features/crm/customer-drawer";
import { CallActionBar } from "@/features/calls/call-action-bar";
import { CustomerPanel } from "@/features/calls/customer-panel";
import { PostCallSheet } from "@/features/calls/post-call-sheet";
import { TranscriptPanel } from "@/features/calls/transcript-panel";
import type { TranscriptItem } from "@/features/calls/types";
import { useMicrophoneStream } from "@/features/calls/use-microphone-stream";
import { CopilotPanel } from "@/features/copilot/copilot-panel";
import { useCopilotSocket } from "@/features/copilot/use-copilot-socket";
import type { AIServerEvent, CopilotResult, CoreCustomer, CRMSummary, WorkflowStage } from "@/lib/api/contracts";
import { aiApi, coreApi } from "@/lib/api/client";
import { useUIStore } from "@/lib/stores/ui-store";
import { cn, formatDuration, titleCase } from "@/lib/utils";

const setupSchema = z.object({ customerId: z.string().trim().min(1, "Enter a customer ID."), direction: z.enum(["inbound", "outbound"]) });
const textSchema = z.object({ utterance: z.string().trim().min(1).max(10_000) });
type SetupInput = z.infer<typeof setupSchema>;
type TextInput = z.infer<typeof textSchema>;

export function LiveCallPage() {
  const [customer, setCustomer] = useState<CoreCustomer | null>(null);
  const [requestedCustomerId, setRequestedCustomerId] = useState("");
  const [callId, setCallId] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [latestResult, setLatestResult] = useState<CopilotResult | null>(null);
  const [crmSummary, setCrmSummary] = useState<CRMSummary | null>(null);
  const [workflowStage, setWorkflowStage] = useState<WorkflowStage | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [wrapUpOpen, setWrapUpOpen] = useState(false);
  const [sequence, setSequence] = useState(0);
  const setup = useForm<SetupInput>({ resolver: zodResolver(setupSchema), defaultValues: { customerId: "", direction: "inbound" } });
  const textForm = useForm<TextInput>({ resolver: zodResolver(textSchema), defaultValues: { utterance: "" } });
  const noteRef = useRef<HTMLTextAreaElement>(null);
  const note = useUIStore((state) => callId ? state.callNotes[callId] ?? "" : "");
  const setCallNote = useUIStore((state) => state.setCallNote);

  const handleRealtimeEvent = useCallback((event: AIServerEvent) => {
    if (event.type === "transcript") {
      const receivedAt = new Date().toISOString();
      setTranscript((current) => {
        const existing = new Set(current.map((item) => item.segment_id));
        return [...current, ...event.segments.filter((segment) => !existing.has(segment.segment_id)).map((segment) => ({ ...segment, receivedAt, source: "websocket" as const }))];
      });
    } else if (event.type === "copilot_result") {
      setLatestResult(event.result);
      setSequence((value) => Math.max(value, event.result.sequence_number + 1));
    } else if (event.type === "crm_summary") {
      setCrmSummary(event.crm_summary);
      setWrapUpOpen(true);
      toast.success("Post-call CRM summary is ready for review");
    } else if (event.type === "status") setWorkflowStage(event.stage);
    else if (event.type === "error") toast.error("Copilot event failed", { description: event.message });
  }, []);

  const socket = useCopilotSocket({ onEvent: handleRealtimeEvent, onSessionReset: () => toast.warning("AI session reconnected", { description: "The live AI context restarted; the visible transcript remains local." }) });
  const microphone = useMicrophoneStream();
  const stopMicrophone = microphone.stop;
  const startCall = useMutation({ mutationFn: async (input: SetupInput) => { const customerResponse = await coreApi.customer(input.customerId); const callResponse = await coreApi.createCall(customerResponse.data.id, input.direction); return { customer: customerResponse.data, call: callResponse.data, requestedId: input.customerId }; }, onSuccess: ({ customer: record, call, requestedId }) => { setCustomer(record); setRequestedCustomerId(requestedId); setCallId(call.call_id); setStartedAt(Date.now()); toast.success("Call workspace created", { description: "Confirm customer consent before starting AI assistance." }); }, onError: (error) => toast.error("Call could not be started", { description: error.message }) });
  const consentMutation = useMutation({ mutationFn: () => { if (!callId) throw new Error("No call is active."); return coreApi.logConsent(callId, true); }, onSuccess: () => { setConsent(true); if (customer) socket.connect({ salesAgentId: "frontend-agent", leadId: customer.id }); toast.success("Consent recorded"); }, onError: (error) => toast.error("Consent could not be recorded", { description: error.message }) });
  const analyzeText = useMutation({ mutationFn: async ({ utterance }: TextInput) => { if (!socket.sessionId) throw new Error("Wait for the AI session to connect."); return aiApi.analyzeText({ session_id: socket.sessionId, sequence_number: sequence, customer_utterance: utterance }); }, onSuccess: (result, variables) => { const now = new Date().toISOString(); setTranscript((current) => [...current, { segment_id: `text-${result.request_id}`, speaker: "customer", text: variables.utterance, start_seconds: elapsed, end_seconds: elapsed + .001, confidence: null, language: "en", is_final: true, receivedAt: now, source: "text_fallback" }]); setLatestResult(result); setSequence((value) => value + 1); textForm.reset(); }, onError: (error) => toast.error("Text analysis failed", { description: error.message }) });

  useEffect(() => { if (!startedAt || !consent) return; const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000); return () => clearInterval(timer); }, [consent, startedAt]);
  useEffect(() => () => { void stopMicrophone(); }, [stopMicrophone]);
  const leadScore = crmSummary?.lead_score.score;
  const connectionVariant = socket.status === "connected" ? "success" : socket.status === "error" ? "danger" : "warning";
  const connectionLabel = socket.status === "connected" ? "AI connected" : titleCase(socket.status);
  const fallbackMismatch = customer && requestedCustomerId !== customer.id;
  const canStream = consent && socket.status === "connected";
  const endCall = async () => { await microphone.stop(); const sent = socket.sendControl({ type: "call_end", ended_at: new Date().toISOString() }); if (!sent) setWrapUpOpen(true); };
  const resetWorkspace = async () => { await microphone.stop(); socket.disconnect(); setCustomer(null); setCallId(null); setConsent(false); setStartedAt(null); setElapsed(0); setTranscript([]); setLatestResult(null); setCrmSummary(null); setWorkflowStage(null); setSequence(0); setup.reset(); };
  const sendText = textForm.handleSubmit((values) => analyzeText.mutate(values));

  if (!callId || !customer) return <div className="space-y-7"><PageHeader eyebrow="Realtime workspace" title="Start a live call" description="Load a core customer record, create a call, record consent, then connect the native AI WebSocket for transcript and copilot events." /><div className="mx-auto grid max-w-5xl gap-5 lg:grid-cols-[1.05fr_.95fr]"><Card className="p-6"><h2 className="text-lg font-semibold">Call setup</h2><p className="mt-1 text-sm leading-6 text-slate-500">Use an existing customer UUID. The core backend may return its demo customer for an unknown ID.</p><form onSubmit={setup.handleSubmit((input) => startCall.mutate(input))} className="mt-6 space-y-4"><div className="space-y-1.5"><Label htmlFor="customer-id">Customer ID</Label><Input id="customer-id" {...setup.register("customerId")} placeholder="Customer UUID" autoFocus />{setup.formState.errors.customerId ? <p className="text-xs text-red-600">{setup.formState.errors.customerId.message}</p> : null}</div><div className="space-y-1.5"><Label htmlFor="direction">Direction</Label><select id="direction" {...setup.register("direction")} className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-900"><option value="inbound">Inbound</option><option value="outbound">Outbound</option></select></div><Button type="submit" className="w-full" disabled={startCall.isPending}>{startCall.isPending ? <Loader2 className="animate-spin" /> : <PhoneCall />}Create call workspace</Button></form></Card><Card className="p-6"><p className="flex items-center gap-2 text-sm font-semibold"><ShieldCheck className="size-4 text-blue-600" />Before audio begins</p><ol className="mt-5 space-y-4">{["Customer record is retrieved from the core API.", "A core call ID is created for wrap-up and consent.", "Customer recording and AI-processing consent is logged.", "The AI-native WebSocket starts a separate in-memory session.", "Microphone audio is downsampled to 16 kHz PCM16 in the browser."].map((item, index) => <li key={item} className="flex gap-3 text-sm leading-6 text-slate-600 dark:text-slate-300"><span className="grid size-6 shrink-0 place-items-center rounded-full bg-slate-100 text-[11px] font-semibold dark:bg-slate-800">{index + 1}</span>{item}</li>)}</ol><div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300">The core and AI call IDs are not linked by the backend. The UI preserves both in one workspace but cannot create a cross-service transaction.</div></Card></div></div>;

  return <div className="space-y-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><h1 className="text-xl font-semibold tracking-tight">Live call · {customer.name}</h1><Badge variant={connectionVariant}>{socket.status === "connected" ? <Wifi className="size-3" /> : <WifiOff className="size-3" />}{connectionLabel}</Badge>{workflowStage ? <Badge variant="primary"><Sparkles className="size-3" />{titleCase(workflowStage)}</Badge> : null}</div><p className="mt-1 text-xs text-slate-400">Call {callId.slice(0, 8)} · {formatDuration(elapsed)} · {consent ? "Consent recorded" : "Consent required"}</p></div><div className="flex items-center gap-2"><Button variant="secondary" size="sm" onClick={() => void resetWorkspace()}>New call</Button><Button variant="danger" size="sm" onClick={() => void endCall()}><CircleStop />End call</Button></div></div>
    {fallbackMismatch ? <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300"><AlertTriangle className="mr-2 inline size-3.5" />Requested {requestedCustomerId}, but the core API returned demo/fallback customer {customer.id}.</div> : null}
    {!consent ? <Card className="border-amber-200 bg-amber-50/70 p-4 dark:border-amber-900 dark:bg-amber-950/30"><div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center"><div><p className="text-sm font-semibold text-amber-900 dark:text-amber-200">Customer consent is required</p><p className="mt-1 text-xs leading-5 text-amber-700 dark:text-amber-300">Recording and AI processing are blocked by the core WebSocket until DPDP consent is logged.</p></div><Button onClick={() => consentMutation.mutate()} disabled={consentMutation.isPending}>{consentMutation.isPending ? <Loader2 className="animate-spin" /> : <CheckCircle2 />}Confirm recorded consent</Button></div></Card> : <div className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white p-2 dark:border-slate-800 dark:bg-slate-900"><Tooltip><TooltipTrigger asChild><span><Button size="sm" variant={microphone.status === "active" ? "danger" : "secondary"} disabled={!canStream || microphone.status === "requesting"} onClick={() => microphone.status === "active" ? void microphone.stop() : void microphone.start(socket.sendAudio)}>{microphone.status === "requesting" ? <Loader2 className="animate-spin" /> : microphone.status === "active" ? <MicOff /> : <Mic />}{microphone.status === "active" ? "Stop listening" : "Start listening"}</Button></span></TooltipTrigger><TooltipContent>{canStream ? "Stream 16 kHz PCM16 microphone audio" : "Wait for the AI WebSocket to connect"}</TooltipContent></Tooltip><span className={cn("text-[11px]", microphone.status === "error" ? "text-red-600" : "text-slate-400")}>{microphone.error ?? (microphone.status === "active" ? "Microphone audio is streaming" : "Microphone is off")}</span><span className="ml-auto text-[11px] text-slate-400">Native WebSocket · not Socket.IO</span></div>}
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(240px,.75fr)_minmax(400px,1.25fr)] min-[1440px]:grid-cols-[280px_minmax(420px,1fr)_360px]">
      <div className="space-y-3"><CustomerPanel customer={customer} leadScore={leadScore} /><Card className="p-4"><Label htmlFor="call-notes">Agent notes</Label><Textarea ref={noteRef} id="call-notes" value={note} onChange={(event) => setCallNote(callId, event.target.value)} placeholder="Notes save automatically on this device…" className="mt-2 min-h-28 text-xs" /><p className="mt-2 text-[10px] text-slate-400">Autosaved locally · no notes API is available</p></Card></div>
      <div className="space-y-3"><TranscriptPanel callId={callId} items={transcript} searching={socket.status === "connecting"} /><Card className="p-3"><form onSubmit={sendText} className="flex items-end gap-2"><div className="flex-1"><Label htmlFor="text-utterance" className="sr-only">Customer utterance text fallback</Label><Textarea id="text-utterance" {...textForm.register("utterance")} placeholder="Text fallback: enter a customer utterance for AI analysis…" className="min-h-12 resize-none py-3" onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void sendText(); } }} /></div><Button size="icon" type="submit" disabled={!socket.sessionId || analyzeText.isPending} aria-label="Analyze customer utterance">{analyzeText.isPending ? <Loader2 className="animate-spin" /> : <Send />}</Button></form><p className="mt-2 text-[10px] text-slate-400">Press Enter to analyze · Shift+Enter for a new line</p></Card></div>
      <div className="lg:col-span-2 min-[1440px]:col-span-1"><CopilotPanel result={latestResult} socketStatus={socket.status} socketError={socket.error} /></div>
    </div>
    <CallActionBar onOpenKyc={() => setDetailsOpen(true)} onCreateNote={() => noteRef.current?.focus()} onCloseDeal={() => setWrapUpOpen(true)} />
    <CustomerDrawer customer={customer} requestedId={requestedCustomerId} open={detailsOpen} onOpenChange={setDetailsOpen} /><PostCallSheet open={wrapUpOpen} onOpenChange={setWrapUpOpen} callId={callId} crmSummary={crmSummary} latestResult={latestResult} />
  </div>;
}
