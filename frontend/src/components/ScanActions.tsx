import { useState } from 'react'
import { CalendarClock, Download, LoaderCircle, RotateCcw, ShieldAlert, Square, Zap } from 'lucide-react'
import { cancelScan, rescan, runExploitation, scheduleScan } from '../services/api'

export default function ScanActions({ scanId, status, onChanged }: { scanId: string; status?: string; onChanged: (scanId: string) => void }) {
  const [runAt, setRunAt] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [exploiting, setExploiting] = useState(false)

  const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

  async function cancel() {
    setBusy(true)
    try {
      await cancelScan(scanId)
      setMessage('Scan cancelled.')
      onChanged(scanId)
    } catch {
      setMessage('Could not cancel scan.')
    } finally {
      setBusy(false)
    }
  }

  async function repeat() {
    setBusy(true)
    try {
      const result = await rescan(scanId)
      setMessage('Rescan queued.')
      onChanged(result.scan_id)
    } catch {
      setMessage('Could not queue rescan.')
    } finally {
      setBusy(false)
    }
  }

  async function schedule() {
    if (!runAt) return
    setBusy(true)
    try {
      await scheduleScan(scanId, new Date(runAt).toISOString())
      setMessage('Scan scheduled.')
    } catch {
      setMessage('Could not schedule scan.')
    } finally {
      setBusy(false)
    }
  }

  async function triggerExploitation() {
    setExploiting(true)
    setMessage('')
    try {
      const res = await runExploitation(scanId)
      setMessage(res.message || 'Exploitation verified.')
      onChanged(scanId)
    } catch {
      setMessage('Exploitation verification failed.')
    } finally {
      setExploiting(false)
    }
  }

  return (
    <div className="scan-actions" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
      {status === 'completed' && (
        <a
          className="primary-button"
          href={`${baseUrl}/api/reports/scan/${scanId}/download`}
          target="_blank"
          rel="noreferrer"
          style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <Download size={14} /> Download PDF Report
        </a>
      )}

      {/* Perform Exploitation Button */}
      <button
        className="secondary-button"
        type="button"
        onClick={triggerExploitation}
        disabled={busy || exploiting || status === 'running'}
        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', borderColor: '#f59e0b', color: '#f59e0b' }}
        title="Run safe exploitation & verification on findings"
      >
        {exploiting ? <LoaderCircle size={13} className="spin" /> : <Zap size={13} />}
        Run Exploitation
      </button>

      <button
        className="secondary-button"
        type="button"
        onClick={cancel}
        disabled={busy || ['completed', 'failed', 'cancelled'].includes(status ?? '')}
      >
        <Square size={13} /> Cancel
      </button>
      <button className="secondary-button" type="button" onClick={repeat} disabled={busy}>
        <RotateCcw size={13} /> Rescan
      </button>
      <input
        type="datetime-local"
        value={runAt}
        onChange={(event) => setRunAt(event.target.value)}
        style={{ padding: '6px 8px', borderRadius: '4px' }}
      />
      <button className="secondary-button" type="button" onClick={schedule} disabled={busy || !runAt}>
        <CalendarClock size={13} /> Schedule
      </button>
      {message && <small style={{ marginLeft: '6px', color: '#10b981' }}>{message}</small>}
    </div>
  )
}