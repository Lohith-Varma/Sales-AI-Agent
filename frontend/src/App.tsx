import { useState } from 'react'
import type { TranscriptLine } from './types'
import { LiveCallConsole } from './pages/LiveCallConsole'
import { PostCallWrapUp } from './pages/PostCallWrapUp'
import { CrmRecordView } from './pages/CrmRecordView'
import './App.css'
export default function App() { const [path, setPath] = useState(window.location.pathname); const [callData, setCallData] = useState<{ consent: boolean; transcript: TranscriptLine[]; notes: string[] }>({ consent: false, transcript: [], notes: [] }); const navigate = (to: string) => { window.history.pushState({}, '', to); setPath(to) }; if (path.includes('/wrap-up')) return <PostCallWrapUp callData={callData} onNavigate={navigate}/>; if (path.startsWith('/crm/')) return <CrmRecordView onNavigate={navigate}/>; return <LiveCallConsole onNavigate={navigate} setCallData={setCallData}/> }
