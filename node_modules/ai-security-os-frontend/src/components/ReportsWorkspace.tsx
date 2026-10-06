import { useEffect, useState } from 'react'
import { Download, FileText, LoaderCircle, CheckCircle2 } from 'lucide-react'
import { generateReport, listReports } from '../services/api'
import type { Scan } from '../types'

export default function ReportsWorkspace({ scans }: { scans: Scan[] }) {
  const [reports, setReports] = useState<Array<{ id: string; scan_id: string; title: string; generated_at: string; download: string }>>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const completed = scans.filter((scan) => scan.status === 'completed')

  const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

  async function refresh() {
    try {
      const response = await listReports()
      setReports(response.reports || [])
    } catch {
      setReports([])
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function create(scanId: string) {
    setLoading(true)
    setMessage('')
    try {
      await generateReport(scanId)
      await refresh()
      setMessage('PDF report generated successfully.')
    } catch {
      setMessage('Could not generate the PDF report.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="view-stack">
      <section className="hero-row compact">
        <div>
          <p className="eyebrow">OUTPUT STUDIO</p>
          <h1>Security Reports</h1>
          <p className="muted-copy">
            Professional PDF assessment reports generated from multi-agent security scans and saved in <code>/reports</code>.
          </p>
        </div>
      </section>

      {/* Completed Scans with instant Download or Re-generate */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">COMPLETED MISSIONS</p>
            <h2>Instant PDF Download</h2>
          </div>
          <FileText size={18} />
        </div>

        {completed.length === 0 ? (
          <div className="empty-state">
            <span>Complete a scan to unlock downloadable reports.</span>
          </div>
        ) : (
          completed.map((scan) => {
            const existingReport = reports.find((r) => r.scan_id === scan.scan_id)
            const downloadUrl = existingReport?.download
              ? `${baseUrl}${existingReport.download}`
              : `${baseUrl}/api/reports/scan/${scan.scan_id}/download`

            return (
              <div
                className="report-source"
                key={scan.scan_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  margin: '6px 0',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <div>
                  <strong style={{ fontSize: '15px' }}>{scan.target}</strong>
                  <small style={{ display: 'block', color: '#94a3b8', marginTop: '3px' }}>
                    Scan ID: <code>{scan.scan_id}</code> • {new Date(scan.created_at).toLocaleString()}
                  </small>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <a
                    className="primary-button"
                    href={downloadUrl}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      textDecoration: 'none',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '7px',
                      padding: '8px 14px',
                    }}
                  >
                    <Download size={15} /> Download PDF
                  </a>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => void create(scan.scan_id)}
                    disabled={loading}
                    title="Regenerate new PDF copy"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    {loading ? <LoaderCircle size={14} className="spin" /> : <FileText size={14} />}
                    Re-generate
                  </button>
                </div>
              </div>
            )
          })
        )}
        {message && (
          <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981' }}>
            <CheckCircle2 size={15} /> <small>{message}</small>
          </div>
        )}
      </section>

      {/* Report Archive List */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">ARCHIVE REPOSITORY</p>
            <h2>Generated PDFs in <code>/reports</code></h2>
          </div>
          <span className="count-badge">{reports.length}</span>
        </div>

        {reports.length === 0 ? (
          <div className="empty-state">
            <span>No reports in archive yet.</span>
          </div>
        ) : (
          reports.map((report) => {
            const fileUrl = report.download
              ? `${baseUrl}${report.download}`
              : `${baseUrl}/api/reports/${report.id}/download`

            return (
              <div
                className="report-source"
                key={report.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  margin: '6px 0',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <div>
                  <strong style={{ fontSize: '15px' }}>{report.title}</strong>
                  <small style={{ display: 'block', color: '#94a3b8', marginTop: '3px' }}>
                    Report ID: <code>{report.id}</code> • {new Date(report.generated_at).toLocaleString()}
                  </small>
                </div>
                <a
                  className="secondary-button"
                  href={fileUrl}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '7px',
                    padding: '8px 14px',
                  }}
                >
                  <Download size={15} /> Download PDF
                </a>
              </div>
            )
          })
        )}
      </section>
    </div>
  )
}
