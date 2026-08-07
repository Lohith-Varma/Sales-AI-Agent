import { useEffect, useState } from 'react'
import { ArrowLeft, LockKeyhole, UserRound, Loader2 } from 'lucide-react'
import { dashboardApi } from '../api/dashboard'
import type { CrmRecord } from '../types'

export function CrmRecordView({ onNavigate }: { onNavigate: (p: string) => void }) {
  // Extract customerId from url path (e.g. /crm/customer-id)
  const pathParts = window.location.pathname.split('/');
  const customerId = pathParts[pathParts.length - 1] || 'CRM-28419';

  const [customer, setCustomer] = useState<CrmRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const fetchCustomer = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await dashboardApi.getCustomer(customerId);
        if (active) {
          if (response.success && response.data) {
            setCustomer(response.data);
          } else {
            setError(response.message || 'Failed to load customer profile');
          }
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || 'An error occurred while fetching customer details.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchCustomer();
    return () => {
      active = false;
    };
  }, [customerId]);

  const handleBackToCall = () => {
    // Navigate back to call page (use the current call context or fallback)
    onNavigate('/call/demo-1');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-5 text-slate-900">
        <div className="text-center">
          <Loader2 className="animate-spin mx-auto text-indigo-700 mb-2" size={32} />
          <p className="text-sm font-semibold text-slate-600">Retrieving CRM record...</p>
        </div>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-5 text-slate-900">
        <div className="max-w-md w-full rounded-2xl border border-rose-200 bg-white p-6 text-center shadow-xl">
          <p className="text-lg font-bold text-rose-700">Error Loading Profile</p>
          <p className="mt-2 text-sm text-slate-600">{error || 'Customer profile not found.'}</p>
          <button
            onClick={handleBackToCall}
            className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-indigo-700"
          >
            <ArrowLeft size={16} /> Back to call
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 p-5 text-slate-900">
      <main className="mx-auto max-w-4xl">
        <button onClick={handleBackToCall} className="mb-5 inline-flex items-center gap-1 text-sm font-bold text-indigo-700">
          <ArrowLeft size={16} />Back to call
        </button>
        
        <div className="panel overflow-hidden bg-white border border-slate-200 rounded-2xl shadow-sm">
          <div className="bg-slate-900 p-6 text-white">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Read-only CRM record</p>
            <h1 className="mt-1 text-3xl font-black">{customer.name}</h1>
            <p className="mt-1 text-slate-300">ID: {customer.id} · {customer.city}</p>
          </div>
          
          <div className="grid gap-6 p-6 md:grid-cols-2">
            <section>
              <h2 className="flex items-center gap-2 font-bold text-slate-800 text-lg">
                <UserRound size={19} className="text-indigo-600" />Customer profile
              </h2>
              <dl className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between border-b border-slate-100 py-2">
                  <dt className="text-slate-500 font-medium">Email</dt>
                  <dd className="text-slate-800 font-semibold">{customer.email}</dd>
                </div>
                <div className="flex justify-between border-b border-slate-100 py-2">
                  <dt className="text-slate-500 font-medium">Phone</dt>
                  <dd className="text-slate-800 font-semibold">{customer.phone}</dd>
                </div>
              </dl>
              
              <h2 className="mt-6 flex items-center gap-2 font-bold text-slate-800 text-lg">
                <LockKeyhole size={19} className="text-rose-600" />KYC fields on file
              </h2>
              <p className="mt-1 text-xs text-rose-600">Sensitive data present — do not re-request verified fields.</p>
              
              <ul className="mt-3 space-y-2">
                {customer.kycFields && customer.kycFields.map(k => (
                  <li key={k.label} className="rounded-lg bg-rose-50 p-3 text-sm border border-rose-100">
                    <b className="text-slate-800">{k.label}</b>
                    <span className="float-right text-slate-600 font-medium">{k.value}</span>
                  </li>
                ))}
              </ul>
            </section>
            
            <section>
              <h2 className="font-bold text-slate-800 text-lg">Past interactions</h2>
              <div className="mt-3 space-y-3">
                {customer.interactions && customer.interactions.map((i, index) => (
                  <article key={`${i.date}-${index}`} className="rounded-xl border border-slate-200 p-3 bg-slate-50">
                    <div className="flex justify-between gap-2 text-sm">
                      <b className="text-slate-800">{i.outcome}</b>
                      <span className="text-slate-500 font-medium">{i.date}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{i.note}</p>
                  </article>
                ))}
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
