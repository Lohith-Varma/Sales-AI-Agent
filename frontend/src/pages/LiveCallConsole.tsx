import { useEffect, useState, useRef } from 'react'
import { Loader2 } from 'lucide-react'
import { TopBar } from '../components/TopBar'
import { TranscriptPanel } from '../components/TranscriptPanel'
import { SuggestionRail } from '../components/SuggestionRail'
import { ReferenceDrawer } from '../components/ReferenceDrawer'
import { salesApi } from '../api/sales'
import { dashboardApi } from '../api/dashboard'
import type { Suggestion, TranscriptLine, Clause, CrmRecord } from '../types'

export function LiveCallConsole({
  onNavigate,
  setCallData
}: {
  onNavigate: (p: string) => void;
  setCallData: (x: { consent: boolean; transcript: TranscriptLine[]; notes: string[] }) => void;
}) {
  const [customer, setCustomer] = useState<CrmRecord | null>(null);
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [callId, setCallId] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [notes, setNotes] = useState<string[]>([]);
  
  // UI states
  const [drawer, setDrawer] = useState(false);
  const [highlighted, setHighlighted] = useState<string | undefined>();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);

  // Parse customer ID from URL or fallback
  const customerId = 'CRM-28419';

  // 1. Load customer details, clauses and initiate call session
  useEffect(() => {
    let active = true;
    const initSession = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch customer CRM profile
        const customerRes = await dashboardApi.getCustomer(customerId);
        if (!active) return;
        if (!customerRes.success || !customerRes.data) {
          throw new Error(customerRes.message || 'Failed to load customer profile');
        }
        setCustomer(customerRes.data);

        // Fetch product compliance clauses
        const clausesRes = await dashboardApi.getClauses();
        if (!active) return;
        if (clausesRes.success && clausesRes.data) {
          setClauses(clausesRes.data);
        }

        // Create active Call session
        const callRes = await salesApi.initiateCall(customerRes.data.id);
        if (!active) return;
        if (!callRes.success || !callRes.data) {
          throw new Error(callRes.message || 'Failed to create call session');
        }
        setCallId(callRes.data.call_id);
      } catch (err: any) {
        if (active) {
          setError(err.message || 'An error occurred during initialization.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    initSession();
    return () => { active = false; };
  }, [customerId]);

  // 2. Manage the timer
  useEffect(() => {
    if (!consent) return;
    const interval = window.setInterval(() => {
      setSeconds(s => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [consent]);

  // 3. Connect to the WebSocket when consent is given
  useEffect(() => {
    if (!consent || !callId) return;

    // Resolve ws endpoint url dynamically from backend URL configuration
    const apiURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    const wsURL = apiURL.replace(/^http/, 'ws') + `/ws/calls/${callId}`;
    
    console.log(`Connecting to WebSocket: ${wsURL}`);
    const ws = new WebSocket(wsURL);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log('Voice pipeline WebSocket connected.');
    };

    ws.onmessage = (event) => {
      try {
        if (typeof event.data === 'string') {
          const data = JSON.parse(event.data);
          
          if (data.event === 'transcript') {
            const newLine: TranscriptLine = {
              id: Date.now(),
              speaker: data.speaker === 'agent' ? 'Agent' : 'Customer',
              text: data.text,
              confidence: data.confidence,
            };
            setLines(prev => [...prev, newLine]);
          } else if (data.event === 'response') {
            const newLine: TranscriptLine = {
              id: Date.now(),
              speaker: 'Agent', // Suggestions are text for the agent to say
              text: data.text,
            };
            
            // Map intent to display highlight topic
            let topic = 'terms';
            if (data.text.toLowerCase().includes('kyc') || data.text.toLowerCase().includes('pan')) {
              topic = 'kyc';
            } else if (data.text.toLowerCase().includes('late') || data.text.toLowerCase().includes('fee')) {
              topic = 'late-fees';
            } else if (data.text.toLowerCase().includes('eligibility') || data.text.toLowerCase().includes('check')) {
              topic = 'eligibility';
            }

            setHighlighted(topic);
            setDrawer(true);

            // Add Suggestion card to suggestion rail
            const newSuggestion: Suggestion = {
              id: `${Date.now()}-suggestion`,
              intent: topic,
              text: data.text,
              source: data.citations && data.citations.length > 0 ? data.citations[0] : 'Knowledge Base',
              confidence: data.confidence || 0.95,
              createdAt: Date.now(),
              status: 'active',
            };
            
            setSuggestions(prev => [
              ...prev.map(s => ({ ...s, status: 'archived' as const })),
              newSuggestion
            ]);
          }
        } else {
          // Binary audio bytes received (TTS audio response payload)
          console.log(`Received ${event.data.size || event.data.byteLength} binary audio bytes.`);
        }
      } catch (err) {
        console.error('Error handling WebSocket message:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };

    ws.onclose = () => {
      console.log('WebSocket closed.');
    };

    // Periodically send simulated binary audio chunks to drive the backend Mock STT Provider
    const audioInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        // Send a 320-byte dummy packet (represents 20ms PCM audio)
        ws.send(new Uint8Array(320));
      }
    }, 400); // 400ms interval * 10 chunks = triggers new transcript every 4 seconds

    return () => {
      clearInterval(audioInterval);
      ws.close();
      socketRef.current = null;
    };
  }, [consent, callId]);

  // 4. Propagate call data back to parent wrap-up component
  useEffect(() => {
    setCallData({ consent, transcript: lines, notes });
  }, [consent, lines, notes, setCallData]);

  // 5. Confirm consent handler
  const handleConfirmConsent = async () => {
    if (!callId) return;
    try {
      // Call backend POST /api/consent endpoint
      const response = await salesApi.logConsent(callId, true);
      if (response.success) {
        setConsent(true);
      } else {
        alert('Failed to log consent: ' + response.message);
      }
    } catch (err: any) {
      alert('Error logging consent: ' + err.message);
    }
  };

  const handleEndCall = () => {
    if (socketRef.current) {
      socketRef.current.close();
    }
    // Navigate to post call wrap-up
    onNavigate(`/call/${callId || 'demo-1'}/wrap-up`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-5 text-slate-900">
        <div className="text-center bg-white p-8 border border-slate-200 rounded-2xl shadow-md max-w-sm w-full">
          <Loader2 className="animate-spin mx-auto text-indigo-700 mb-3" size={36} />
          <p className="text-sm font-bold text-slate-700">Connecting call server...</p>
          <p className="text-xs text-slate-400 mt-1">Initializing secure telephony pipeline</p>
        </div>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-5 text-slate-900">
        <div className="max-w-md w-full rounded-2xl border border-rose-200 bg-white p-6 text-center shadow-xl">
          <p className="text-lg font-bold text-rose-700">Call Connection Failed</p>
          <p className="mt-2 text-sm text-slate-600">{error || 'Unable to establish call pipeline.'}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-indigo-700 text-white rounded-lg text-sm font-semibold hover:bg-indigo-600"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <TopBar
        consent={consent}
        onConfirm={handleConfirmConsent}
        seconds={seconds}
        customer={customer}
        onOpenCrm={() => onNavigate(`/crm/${customer.id}`)}
        onEnd={handleEndCall}
      />
      
      <main className="mx-auto flex h-[calc(100vh-72px)] max-w-[1600px] flex-col p-4">
        <div className="relative grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(360px,.85fr)]">
          <div className={`contents transition duration-500 ${!consent ? 'pointer-events-none select-none blur-[3px] opacity-40' : ''}`}>
            
            <TranscriptPanel lines={lines} />
            
            <div className="flex min-h-0 flex-col gap-3">
              <SuggestionRail
                suggestions={suggestions}
                onInsert={s => setNotes(n => n.includes(s.text) ? n : [...n, s.text])}
              />
              
              <aside className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Agent notes</p>
                {notes.length === 0 ? (
                  <p className="mt-2 text-xs text-slate-400">Use “Insert into notes” to retain guidance for this call.</p>
                ) : (
                  <ul className="mt-2 space-y-2">
                    {notes.map((n, i) => (
                      <li key={`${n}-${i}`} className="rounded-lg bg-amber-50 p-2 text-xs leading-4 text-slate-700 border border-amber-100 shadow-sm">
                        {n}
                      </li>
                    ))}
                  </ul>
                )}
              </aside>
            </div>
          </div>
          
          {!consent && (
            <div className="absolute inset-0 z-10 grid place-items-center">
              <div className="max-w-sm rounded-2xl border border-amber-200 bg-white p-6 text-center shadow-xl">
                <p className="text-lg font-bold text-slate-800">Waiting for customer consent</p>
                <p className="mt-2 text-sm text-slate-600">
                  Confirm consent in the top bar before viewing or generating live call assistance.
                </p>
              </div>
            </div>
          )}
        </div>
        
        <ReferenceDrawer
          clauses={clauses}
          query={query}
          setQuery={setQuery}
          open={drawer}
          setOpen={setDrawer}
          highlighted={highlighted}
        />
      </main>
    </div>
  );
}
