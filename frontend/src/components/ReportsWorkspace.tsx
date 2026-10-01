import { useEffect, useState } from 'react'
import { Download, FileText, LoaderCircle } from 'lucide-react'
import { generateReport, listReports } from '../services/api'
import type { Scan } from '../types'

export default function ReportsWorkspace({ scans }: { scans: Scan[] }) {
  const [reports, setReports] = useState<Array<{ id: string; scan_id: string; title: string; generated_at: string; download: string }>>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const completed = scans.filter((scan) => scan.status === 'completed')

  async function refresh() {
    const response = await listReports().catch(() => ({ reports: [] }))
    setReports(response.reports)
  }
  useEffect(() => { void refresh() }, [])

  async function create(scanId: string) {
    setLoading(true)
    setMessage('')
    try {
      await generateReport(scanId)
      await refresh()
      setMessage('PDF report generated.')
    } catch {
      setMessage('Could not generate the PDF report.')
    } finally {
      setLoading(false)
    }
  }

  return <div className="view-stack"><section className="hero-row compact"><div><p className="eyebrow">OUTPUT STUDIO</p><h1>Reports</h1><p className="muted-copy">Generate professional PDF documentation from completed scoped assessments.</p></div></section><section className="panel"><div className="panel-heading"><div><p className="eyebrow">COMPLETED ASSESSMENTS</p><h2>Generate report</h2></div><FileText size={18} /></div>{completed.length === 0 ? <div className="empty-state"><span>Complete a scan before generating a report.</span></div> : completed.map((scan) => <div className="report-source" key={scan.scan_id}><div><strong>{scan.target}</strong><small>{new Date(scan.created_at).toLocaleString()}</small></div><button className="secondary-button" type="button" onClick={() => void create(scan.scan_id)} disabled={loading}>{loading ? <LoaderCircle size={14} className="spin" /> : <FileText size={14} />} Generate PDF</button></div>)}{message && <small className="settings-message">{message}</small>}</section><section className="panel"><div className="panel-heading"><div><p className="eyebrow">REPORT ARCHIVE</p><h2>Available PDFs</h2></div><span className="count-badge">{reports.length}</span></div>{reports.length === 0 ? <div className="empty-state"><span>No reports generated.</span></div> : reports.map((report) => <div className="report-source" key={report.id}><div><strong>{report.title}</strong><small>{new Date(report.generated_at).toLocaleString()}</small></div><a className="secondary-button" href={`http://localhost:8000${report.download}`} target="_blank" rel="noreferrer"><Download size={14} /> Download PDF</a></div>)}</section></div>
}
