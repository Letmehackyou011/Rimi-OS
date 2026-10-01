import { useState } from 'react'
import { CalendarClock, Play, RotateCcw, Square } from 'lucide-react'
import { cancelScan, rescan, scheduleScan } from '../services/api'

export default function ScanActions({ scanId, status, onChanged }: { scanId: string; status?: string; onChanged: (scanId: string) => void }) {
  const [runAt, setRunAt] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  async function cancel() { setBusy(true); try { await cancelScan(scanId); setMessage('Scan cancelled.'); onChanged(scanId) } catch { setMessage('Could not cancel scan.') } finally { setBusy(false) } }
  async function repeat() { setBusy(true); try { const result = await rescan(scanId); setMessage('Rescan queued.'); onChanged(result.scan_id) } catch { setMessage('Could not queue rescan.') } finally { setBusy(false) } }
  async function schedule() { if (!runAt) return; setBusy(true); try { await scheduleScan(scanId, new Date(runAt).toISOString()); setMessage('Scan scheduled.'); } catch { setMessage('Could not schedule scan.') } finally { setBusy(false) } }
  return <div className="scan-actions"><button className="secondary-button" type="button" onClick={cancel} disabled={busy || ['completed', 'failed', 'cancelled'].includes(status ?? '')}><Square size={13} /> Cancel</button><button className="secondary-button" type="button" onClick={repeat} disabled={busy}><RotateCcw size={13} /> Rescan</button><input type="datetime-local" value={runAt} onChange={(event) => setRunAt(event.target.value)} /><button className="secondary-button" type="button" onClick={schedule} disabled={busy || !runAt}><CalendarClock size={13} /> Schedule</button><small>{message}</small></div>
}