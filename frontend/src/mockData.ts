import type { Clause, CrmRecord, TranscriptLine } from './types'
export const customer: CrmRecord = { id: 'CRM-28419', name: 'Ananya Rao', email: 'ananya.rao@example.com', phone: '+91 98••• 4182', city: 'Bengaluru', sensitiveDataOnFile: true, kycFields: [{ label: 'PAN', value: 'Verified ••••P7K' }, { label: 'Date of birth', value: 'Verified • 12 Aug 1994' }, { label: 'Address', value: 'Verified • Bengaluru, KA' }], interactions: [{ date: '28 Jul 2026', outcome: 'Follow-up needed', note: 'Asked about payment timing.' }, { date: '11 Jun 2026', outcome: 'Dropped', note: 'Preferred full payment at the time.' }, { date: '24 Mar 2026', outcome: 'Converted', note: 'Activated merchant offers.' }] }
export const transcriptScript: TranscriptLine[] = [
 { id: 1, speaker: 'Agent', text: 'Thanks for taking the call, Ananya. I can walk you through the flexible payment option.' },
 { id: 2, speaker: 'Customer', text: 'I am mainly worried that this will make the purchase more expensive.', intent: 'price objection', confidence: .96, topic: 'terms' },
 { id: 3, speaker: 'Agent', text: 'That is a fair question. Let me explain exactly how the instalments work.' },
 { id: 4, speaker: 'Customer', text: 'Can anyone use Pay-in-3, or are there eligibility rules?', intent: 'eligibility question', confidence: .91, topic: 'eligibility' },
 { id: 5, speaker: 'Agent', text: 'There are a few eligibility checks, and I can confirm them before you decide.' },
 { id: 6, speaker: 'Customer', text: 'I already shared my PAN earlier. Do I need to give it again?', intent: 'KYC concern', confidence: .98, topic: 'kyc' },
 { id: 7, speaker: 'Agent', text: 'I can see that KYC information is already verified, so I will not ask you to repeat it.' },
 { id: 8, speaker: 'Customer', text: 'What happens if an instalment is late?', intent: 'late fee concern', confidence: .89, topic: 'late-fees' },
 { id: 9, speaker: 'Agent', text: 'I will make sure the late-payment policy is clear before you choose.' },
 { id: 10, speaker: 'Customer', text: 'I need a little time to think about it.', intent: 'hesitation', confidence: .64, topic: 'terms' },
 { id: 11, speaker: 'Agent', text: 'Of course. I can arrange a helpful follow-up instead of rushing you.' },
 { id: 12, speaker: 'Customer', text: 'A callback in a couple of days would be useful.', intent: 'follow-up request', confidence: .94, topic: 'eligibility' },
]
export const clauses: Clause[] = [
 { id: 'terms', title: 'Pay-in-3, zero-cost EMI terms', topic: 'terms', body: 'Eligible purchases are split into three scheduled instalments. No interest is charged when each instalment is paid on time. Availability depends on merchant and approval checks.', source: 'Pay-in-3 T&Cs v4.2', lastSynced: '07 Aug 2026, 09:30 IST' },
 { id: 'late-fees', title: 'Late payment policy', topic: 'late-fees', body: 'A late fee may apply when a scheduled instalment is overdue. Quote only the current fee displayed in the approved policy; do not promise a waiver.', source: 'Collections policy v2.1', lastSynced: '31 Jul 2026, 16:00 IST', stale: true },
 { id: 'kyc', title: 'KYC verification steps', topic: 'kyc', body: 'Check existing CRM KYC fields first. Do not re-request a PAN, date of birth, or address already marked verified. Escalate mismatches through the approved workflow.', source: 'KYC operations playbook v7.0', lastSynced: '07 Aug 2026, 08:15 IST' },
 { id: 'eligibility', title: 'Eligibility criteria', topic: 'eligibility', body: 'Eligibility is subject to identity verification, merchant availability, account history, and automated affordability checks. Never guarantee approval before the check completes.', source: 'Eligibility guide v3.5', lastSynced: '06 Aug 2026, 18:20 IST' },
 { id: 'disclosure', title: 'Required customer disclosure', topic: 'terms', body: 'Before closing, disclose the number of instalments, zero-cost condition, due-date obligation, and that late payments can carry a fee.', source: 'Sales compliance script v5.3', lastSynced: '07 Aug 2026, 10:00 IST' },
]
export const suggestionRules: Record<string, { text: string; source: string; confidence: number }> = {
 'price objection': { text: 'Clarify: “Pay-in-3 is zero-cost when each scheduled instalment is paid on time; there is no interest added to the eligible purchase.”', source: 'Pay-in-3 T&Cs v4.2 — updated Aug 3', confidence: .95 },
 'eligibility question': { text: 'Set expectations: “Eligibility depends on verification, merchant availability, and automated checks. I can help confirm what applies to this purchase.”', source: 'Eligibility guide v3.5 — updated Aug 6', confidence: .91 },
 'KYC concern': { text: 'Reassure without re-collecting: “Your verified KYC fields are already on file, so I will not ask you to share them again.”', source: 'KYC operations playbook v7.0 — updated Aug 7', confidence: .98 },
 'late fee concern': { text: 'Use the current approved policy and explain that a late fee may apply to overdue instalments. Verify the exact amount before quoting.', source: 'Collections policy v2.1 — verify before quoting', confidence: .89 },
 hesitation: { text: 'Offer a low-pressure next step: “Would a callback after you have had time to review the payment schedule be helpful?”', source: 'Pattern from 340 similar calls', confidence: .72 },
 'follow-up request': { text: 'Confirm a 48-hour callback and offer the affordability calculator link as a review aid.', source: 'Pattern from 340 similar calls', confidence: .94 },
}
