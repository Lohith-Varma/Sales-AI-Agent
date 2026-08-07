import { useMemo, useState } from 'react'
import { Check, ClipboardCheck, Flag, PlusCircle, Loader2 } from 'lucide-react'
import { salesApi } from '../api/sales'
import type { TranscriptLine } from '../types'

function Toast({ text }: { text: string }) {
  return (
    <div className="fixed bottom-5 right-5 z-50 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-xl">
      ✓ {text}
    </div>
  );
}

export function PostCallWrapUp({
  callData,
  onNavigate
}: {
  callData: { consent: boolean; transcript: TranscriptLine[]; notes: string[] };
  onNavigate: (p: string) => void;
}) {
  // Parse callId from the URL pathname (e.g. /call/some-uuid/wrap-up)
  const pathParts = window.location.pathname.split('/');
  const callId = pathParts[pathParts.length - 2] || 'demo-1';

  const [summary, setSummary] = useState(
    'Customer Ananya Rao enquired about the Pay-in-3 zero-cost EMI terms, verification documents required for KYC, and possible late fees. The agent confirmed that verified KYC info is already on file. Customer requested a follow-up callback in 48 hours.'
  );
  const [outcome, setOutcome] = useState('Follow-up needed');
  const [taskCreated, setTaskCreated] = useState(false);
  const [manualKyc, setManualKyc] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [complete, setComplete] = useState(false);

  // Check compliance terms
  const termsDisclosed = callData.transcript.some(x =>
    x.text.toLowerCase().includes('late') || x.text.toLowerCase().includes('fee') || x.text.toLowerCase().includes('policy')
  );

  const checks = useMemo(() => [
    { label: 'Customer consent confirmed', verified: callData.consent },
    { label: 'Terms and late-payment policy disclosed', verified: termsDisclosed },
    { label: 'KYC steps followed without re-requesting held data', verified: false, manual: manualKyc }
  ], [callData.consent, manualKyc, termsDisclosed]);

  const ready = checks.every(c => c.verified || c.manual);

  const handleCompleteWrapUp = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await salesApi.completeWrapUp(callId, summary, outcome);
      
      if (response.success) {
        setComplete(true);
        setTimeout(() => {
          onNavigate('/');
        }, 2000);
      } else {
        setError(response.message || 'Failed to complete wrap-up');
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred during call wrap-up completion.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 p-5 text-slate-900">
      <main className="mx-auto max-w-5xl">
        <button
          onClick={() => onNavigate(`/call/${callId}`)}
          className="mb-4 text-sm font-semibold text-indigo-700"
        >
          ← Back to live console
        </button>
        
        <div className="mb-5 flex items-start justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">Call complete</p>
            <h1 className="text-3xl font-black tracking-tight">Post-call wrap-up</h1>
            <p className="mt-1 text-slate-600">Review the draft, record the outcome, and complete the compliance checks.</p>
          </div>
          <span className="rounded-full bg-indigo-100 px-3 py-1.5 text-sm font-bold text-indigo-700">
            Call: {callId.substring(0, 8)}
          </span>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700">
            [FAIL] {error}
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-[1.25fr_.75fr]">
          <section className="space-y-5">
            <article className="panel p-5 bg-white border border-slate-200 rounded-2xl shadow-sm">
              <h2 className="font-bold text-slate-800 text-lg">Auto-drafted summary</h2>
              <textarea
                value={summary}
                onChange={e => setSummary(e.target.value)}
                className="mt-3 min-h-40 w-full rounded-xl border border-slate-200 p-3 text-sm leading-5 outline-none focus:border-indigo-500 bg-slate-50"
              />
              <p className="mt-2 text-xs text-slate-500 font-medium">
                Drafted from the live call transcript. Edit before completing.
              </p>
            </article>
            
            <article className="panel p-5 bg-white border border-slate-200 rounded-2xl shadow-sm">
              <h2 className="font-bold text-slate-800 text-lg">Outcome</h2>
              <select
                value={outcome}
                onChange={e => setOutcome(e.target.value)}
                className="mt-3 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500"
              >
                <option>Converted</option>
                <option>Follow-up needed</option>
                <option>Dropped</option>
              </select>
            </article>
          </section>
          
          <aside className="space-y-5">
            <article className="rounded-2xl bg-indigo-700 p-5 text-white shadow-md">
              <p className="text-xs font-bold uppercase tracking-wider text-indigo-200">Suggested next action</p>
              <h2 className="mt-2 text-lg font-bold">Schedule callback in 48h</h2>
              <p className="mt-2 text-sm text-indigo-100">
                Customer explicitly requested time to review affordability options.
              </p>
              <button
                onClick={() => setTaskCreated(true)}
                disabled={taskCreated}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-bold text-indigo-700 disabled:opacity-60 cursor-pointer shadow-sm"
              >
                <PlusCircle size={16} />
                {taskCreated ? 'CRM task created' : 'Create CRM task'}
              </button>
            </article>
            
            <article className="panel p-5 bg-white border border-slate-200 rounded-2xl shadow-sm">
              <div className="flex items-center gap-2">
                <ClipboardCheck className="text-indigo-600" />
                <h2 className="font-bold text-slate-800 text-lg">Compliance checklist</h2>
              </div>
              
              <div className="mt-3 space-y-3">
                {checks.map((c, i) => (
                  <div
                    key={c.label}
                    className={`rounded-lg border p-3 text-sm ${
                      c.verified || c.manual
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                        : 'border-rose-200 bg-rose-50 text-rose-800'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {c.verified || c.manual ? (
                        <Check className="mt-0.5 text-emerald-600 shrink-0" size={17} />
                      ) : (
                        <Flag className="mt-0.5 text-rose-600 shrink-0" size={17} />
                      )}
                      <span className="font-semibold">{c.label}</span>
                    </div>
                    {!c.verified && !c.manual && (
                      <label className="mt-2 flex cursor-pointer items-center gap-2 text-xs font-bold text-rose-700">
                        <input
                          type="checkbox"
                          className="accent-rose-600"
                          onChange={e => i === 2 && setManualKyc(e.target.checked)}
                        />
                        I manually confirm this compliance item
                      </label>
                    )}
                  </div>
                ))}
              </div>
              
              <button
                disabled={!ready || loading}
                onClick={handleCompleteWrapUp}
                className="mt-4 w-full flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 py-2.5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-35 cursor-pointer hover:bg-slate-800"
              >
                {loading && <Loader2 className="animate-spin" size={16} />}
                Complete wrap-up
              </button>
            </article>
          </aside>
        </div>
      </main>
      
      {taskCreated && <Toast text="CRM task added to task list" />}
      {complete && <Toast text="Wrap-up submitted! Navigating home..." />}
    </div>
  );
}
