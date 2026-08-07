import { useEffect, useRef } from 'react'
import { AlertTriangle, ChevronDown, Search, X } from 'lucide-react'
import type { Clause } from '../types'

type Props = { clauses: Clause[]; query: string; setQuery: (x: string) => void; open: boolean; setOpen: (x: boolean) => void; highlighted?: string }

export function ReferenceDrawer({ clauses, query, setQuery, open, setOpen, highlighted }: Props) {
  const itemRef = useRef<HTMLDivElement>(null)
  useEffect(() => { if (highlighted && open) itemRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [highlighted, open])
  const filtered = clauses.filter(c => `${c.title} ${c.body} ${c.topic}`.toLowerCase().includes(query.toLowerCase()))
  return <section className="drawer">
    <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-5 py-3 text-left">
      <div><p className="eyebrow">Zone D</p><h2 className="text-base">Product & KYC reference</h2></div>
      <ChevronDown className={`transition ${open ? 'rotate-180' : ''}`}/>
    </button>
    {open && <div className="border-t border-slate-200 px-5 pb-4">
      <label className="mt-3 flex max-w-md items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
        <Search size={16} className="text-slate-400"/>
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search clauses, KYC, policies" className="w-full outline-none"/>
        {query && <X size={15} className="cursor-pointer text-slate-400" onClick={() => setQuery('')}/>} 
      </label>
      <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map(c => <article ref={highlighted === c.topic ? itemRef : null} key={c.id} className={`rounded-xl border p-3 text-sm transition ${highlighted === c.topic ? 'border-indigo-400 bg-indigo-50 ring-2 ring-indigo-100' : 'border-slate-200 bg-white'} ${c.stale ? 'border-amber-300 bg-amber-50' : ''}`}>
          <div className="flex items-start justify-between gap-2"><h3 className="font-bold text-slate-800">{c.title}</h3>{c.stale && <AlertTriangle className="shrink-0 text-amber-600" size={17}/>}</div>
          {c.stale && <p className="mt-1 text-xs font-bold text-amber-800">This may be outdated — verify before quoting.</p>}
          <p className="mt-2 text-xs leading-4 text-slate-600">{c.body}</p><p className="mt-2 text-[11px] font-medium text-slate-500">Source: {c.source}</p><p className="text-[11px] text-slate-500">Last synced: {c.lastSynced}</p>
        </article>)}
      </div>
    </div>}
  </section>
}
