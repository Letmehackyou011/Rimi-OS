import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  Archive,
  ArrowUp,
  Bot,
  ChevronRight,
  CircleUserRound,
  Download,
  FileText,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Play,
  Radio,
  Search,
  Settings,
  Shield,
  SlidersHorizontal,
  Sparkles,
  TerminalSquare,
  X,
} from 'lucide-react'
import { approveScan, chatOllama, getLlmConfig, getScanResults, getScanStatus, listScans, saveOllama, startScan, testOllama } from './services/api'
import type { LlmConfig, Scan, ScanResults, ScanStatusResponse, ScopePayload, SecurityMode } from './types'
import AssistantWorkspace from './components/AssistantWorkspace'
import SettingsWorkspace from './components/SettingsWorkspace'
import ScanActions from './components/ScanActions'
import ReportsWorkspace from './components/ReportsWorkspace'
import AgentsWorkspace from './components/AgentsWorkspace'

type View = 'dashboard' | 'scans' | 'findings' | 'reports' | 'agents' | 'assistant' | 'settings'

const navItems: Array<{ id: View; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
  { id: 'scans', label: 'Scans', icon: Radio },
  { id: 'findings', label: 'Findings', icon: Shield },
  { id: 'reports', label: 'Reports', icon: FileText },
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'assistant', label: 'Assistant', icon: MessageSquare },
  { id: 'settings', label: 'Settings', icon: Settings },
]

const defaultLlmConfig: LlmConfig = {
  active_provider: 'ollama',
  ollama_endpoint: 'http://127.0.0.1:11434',
  ollama_model: 'hf.co/llmfan46/gemma-4-E4B-it-ultra-uncensored-heretic-GGUF:Q5_K_M',
  claude_model: 'claude-3-5-sonnet-20241022',
  gemini_model: 'gemini-2.0-flash',
  openai_model: 'gpt-4',
  max_tokens: 8000,
  context_window: 32000,
}

function App() {
  const [view, setView] = useState<View>('dashboard')
  const [scans, setScans] = useState<Scan[]>([])
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null)
  const [selectedResults, setSelectedResults] = useState<ScanResults | null>(null)
  const [activeStatus, setActiveStatus] = useState<ScanStatusResponse | null>(null)
  const [llmConfig, setLlmConfig] = useState<LlmConfig | null>(defaultLlmConfig)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [refreshError, setRefreshError] = useState('')

  async function refreshScans() {
    try {
      const response = await listScans()
      setScans(response.scans)
      setRefreshError('')
    } catch {
      setRefreshError('Backend unavailable')
    }
  }

  useEffect(() => {
    void refreshScans()
    void getLlmConfig().then(setLlmConfig).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!selectedScanId) return
    let cancelled = false
    const poll = async () => {
      try {
        const status = await getScanStatus(selectedScanId)
        if (!cancelled) setActiveStatus(status)
        if (!cancelled && (status.status === 'completed' || status.status === 'failed')) {
          const results = await getScanResults(selectedScanId).catch(() => null)
          if (results && !cancelled) setSelectedResults(results)
          await refreshScans()
        }
      } catch {
        // The list view remains usable while a scan is unavailable.
      }
    }
    void poll()
    const timer = window.setInterval(() => void poll(), 4000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [selectedScanId])

  function selectScan(scanId: string) {
    setSelectedScanId(scanId)
    setSelectedResults(null)
    setView('scans')
    setSidebarOpen(false)
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar--open' : ''}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><Shield size={17} strokeWidth={2.4} /></div>
          <div><strong>Rimi</strong><span>OS</span></div>
          <button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>

        <label className="search-box">
          <Search size={15} />
          <input placeholder="Search workspace" aria-label="Search workspace" />
          <kbd>/</kbd>
        </label>

        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button className={`nav-item ${view === id ? 'nav-item--active' : ''}`} key={id} onClick={() => { setView(id); setSidebarOpen(false) }}>
              <Icon size={17} />
              <span>{label}</span>
              {id === 'scans' && scans.some((scan) => scan.status === 'running') && <i className="live-dot" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="runtime-card">
            <span className="status-pulse" />
            <div><strong>ORCHESTRA ONLINE</strong><small>{llmConfig?.active_provider ?? 'ollama'} / local runtime</small></div>
          </div>
          <div className="user-row"><div className="avatar"><CircleUserRound size={18} /></div><div><strong>Operator</strong><small>Research console</small></div><SlidersHorizontal size={15} /></div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={19} /></button>
          <div className="breadcrumb"><span>workspace</span><ChevronRight size={14} /><strong>{navItems.find((item) => item.id === view)?.label}</strong></div>
          <div className="topbar-actions"><span className="connection"><span className={`status-pulse ${refreshError ? 'status-pulse--offline' : ''}`} /> {refreshError ? 'API offline' : 'API connected'}</span><button className="icon-button" title="Open settings" onClick={() => setView('settings')}><Settings size={17} /></button></div>
        </header>

        {refreshError && <div className="backend-banner"><Activity size={15} /> {refreshError}. Start the FastAPI service to load live data.</div>}
        <div className="content-wrap">
          {view === 'dashboard' && <Dashboard scans={scans} onSelectScan={selectScan} onStart={() => setView('scans')} />}
          {view === 'scans' && <ScansView scans={scans} selectedScanId={selectedScanId} status={activeStatus} results={selectedResults} onSelect={selectScan} onStarted={(scanId) => { setSelectedScanId(scanId); setActiveStatus(null); void refreshScans() }} />}
          {view === 'findings' && <FindingsView scans={scans} results={selectedResults} onSelect={selectScan} />}
          {view === 'reports' && <ReportsWorkspace scans={scans} />}
          {view === 'agents' && <AgentsWorkspace />}
          {view === 'assistant' && <AssistantWorkspace config={llmConfig} />}
          {view === 'settings' && <SettingsWorkspace config={llmConfig} />}
        </div>
      </main>
    </div>
  )
}

function Dashboard({ scans, onSelectScan, onStart }: { scans: Scan[]; onSelectScan: (id: string) => void; onStart: () => void }) {
  const metrics = useMemo(() => ({
    total: scans.length,
    active: scans.filter((scan) => scan.status === 'running' || scan.status === 'pending').length,
    completed: scans.filter((scan) => scan.status === 'completed').length,
    findings: scans.reduce((total, scan) => total + (scan.vulnerabilities || 0), 0),
  }), [scans])
  return <>
    <section className="hero-row"><div><p className="eyebrow">SECURITY RESEARCH / COMMAND CENTER</p><h1>Command center</h1><p className="muted-copy">Authorized assessments, evidence, and reports.</p></div><button className="primary-button" onClick={onStart}><Play size={16} fill="currentColor" /> New scan</button></section>
    <section className="metric-grid">
      <Metric label="Total scans" value={metrics.total} icon={<Archive size={16} />} />
      <Metric label="Active missions" value={metrics.active} icon={<Radio size={16} />} accent={metrics.active > 0} />
      <Metric label="Verified findings" value={metrics.findings} icon={<Shield size={16} />} />
      <Metric label="Completed" value={metrics.completed} icon={<Sparkles size={16} />} />
    </section>
    <section className="dashboard-grid">
      <div className="panel recent-panel"><div className="panel-heading"><div><p className="eyebrow">MISSION LOG</p><h2>Recent scans</h2></div><button className="text-button" onClick={onStart}>Open scans <ArrowUp size={14} /></button></div>{scans.length === 0 ? <EmptyState text="No missions recorded yet" /> : scans.slice(0, 5).map((scan) => <ScanRow key={scan.scan_id} scan={scan} onClick={() => onSelectScan(scan.scan_id)} />)}</div>
      <div className="panel signal-panel"><div className="panel-heading"><div><p className="eyebrow">AGENT SIGNAL</p><h2>Orchestration</h2></div><Bot size={20} /></div><div className="signal-graphic"><div className="signal-core"><Bot size={24} /></div><span className="orbit orbit-one" /><span className="orbit orbit-two" /><span className="orbit orbit-three" /></div><div className="signal-legend"><span><i className="legend-dot cyan" /> Reconnaissance</span><span><i className="legend-dot violet" /> Verification</span><span><i className="legend-dot lime" /> Reporting</span></div></div>
    </section>
    <section className="assistant-strip"><div className="assistant-icon"><TerminalSquare size={17} /></div><div><strong>Ask the research assistant</strong><span>Start with a target, question, or scan instruction.</span></div><button className="icon-button" onClick={onStart} title="Open scan console"><ArrowUp size={17} /></button></section>
  </>
}

function Metric({ label, value, icon, accent = false }: { label: string; value: number; icon: React.ReactNode; accent?: boolean }) { return <div className={`metric-card ${accent ? 'metric-card--accent' : ''}`}><div className="metric-icon">{icon}</div><span>{label}</span><strong>{value.toLocaleString()}</strong></div> }
function ScanRow({ scan, onClick }: { scan: Scan; onClick: () => void }) { return <button className="scan-row" onClick={onClick}><span className={`severity-dot severity-dot--${scan.status}`} /><div><strong>{scan.target}</strong><small>{new Date(scan.created_at).toLocaleString()}</small></div><span className={`status-pill status-pill--${scan.status}`}>{scan.status}</span><ChevronRight size={15} /></button> }
function EmptyState({ text }: { text: string }) { return <div className="empty-state"><Archive size={21} /><span>{text}</span></div> }

function ScansView({ scans, selectedScanId, status, results, onSelect, onStarted }: { scans: Scan[]; selectedScanId: string | null; status: ScanStatusResponse | null; results: ScanResults | null; onSelect: (id: string) => void; onStarted: (id: string) => void }) {
  return <div className="view-stack"><section className="hero-row compact"><div><p className="eyebrow">MISSION CONTROL</p><h1>Scan console</h1><p className="muted-copy">Launch an authorized assessment and watch the agent orchestra work.</p></div></section><div className="scan-layout"><NewScanForm onStarted={onStarted} /><div className="panel scan-list-panel"><div className="panel-heading"><div><p className="eyebrow">ARCHIVE</p><h2>All scans</h2></div><span className="count-badge">{scans.length}</span></div>{scans.length ? scans.map((scan) => <ScanRow key={scan.scan_id} scan={scan} onClick={() => onSelect(scan.scan_id)} />) : <EmptyState text="Your scan archive is empty" />}</div></div>{selectedScanId && <><ScanActions scanId={selectedScanId} status={status?.status} onChanged={onStarted} /><ScanDetail scanId={selectedScanId} status={status} results={results} /></>}</div>
}

function NewScanForm({ onStarted }: { onStarted: (id: string) => void }) {
  const [target, setTarget] = useState(''); const [scope, setScope] = useState(''); const [mode, setMode] = useState<SecurityMode>('safe'); const [provider, setProvider] = useState('ollama'); const [loading, setLoading] = useState(false); const [error, setError] = useState('')
  async function submit(event: FormEvent) { event.preventDefault(); if (!target.trim()) return; setLoading(true); setError(''); const scopePayload: ScopePayload = { version: '1', mode, targets: [{ host: target.trim(), ports: [], paths: scope.trim() ? [scope.trim()] : [] }], tool_allowlist: mode === 'safe' ? ['nmap', 'curl'] : ['nmap', 'curl', 'tcpdump'], max_runtime_seconds: mode === 'safe' ? 120 : 300 }; try { const response = await startScan({ target: target.trim(), scope: scopePayload, mode, llm_provider: provider }); onStarted(response.scan_id); setTarget(''); } catch { setError('Could not start the scan. Check the scope and API connection.'); } finally { setLoading(false) } }
  return <form className="panel scan-form" onSubmit={submit}><div className="panel-heading"><div><p className="eyebrow">NEW MISSION</p><h2>Configure target</h2></div><Radio size={18} /></div><label>Target<input value={target} onChange={(event) => setTarget(event.target.value)} placeholder="example.com or 10.0.0.1" required /></label><label>Path <span className="label-hint">optional</span><input value={scope} onChange={(event) => setScope(event.target.value)} placeholder="/health or /admin" /></label><div className="form-pair"><label>Mode<select value={mode} onChange={(event) => setMode(event.target.value as SecurityMode)}><option value="safe">Safe</option><option value="guarded">Guarded</option><option value="full_access">Full access</option><option value="human_review">Human review</option></select></label><label>Model<select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="ollama">Ollama local</option><option value="openai">OpenAI</option><option value="claude">Claude</option><option value="gemini">Gemini</option><option value="nvidia">Nvidia</option></select></label></div>{error && <p className="form-error">{error}</p>}<button className="primary-button full-button" disabled={loading}>{loading ? <><Activity size={16} className="spin" /> Starting</> : <><Play size={16} fill="currentColor" /> Start assessment</>}</button></form>
}

function ScanDetail({ scanId, status, results }: { scanId: string; status: ScanStatusResponse | null; results: ScanResults | null }) {
  const [token, setToken] = useState('')
  const [message, setMessage] = useState('')
  const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

  async function approve() {
    try {
      await approveScan(scanId, token)
      setMessage('Approval recorded. The scan is queued.')
    } catch {
      setMessage('Approval failed.')
    }
  }

  return (
    <section className="panel detail-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">LIVE TELEMETRY</p>
          <h2>{status?.target ?? 'Selected scan'}</h2>
        </div>
        <span className={`status-pill status-pill--${status?.status ?? 'pending'}`}>{status?.status ?? 'loading'}</span>
      </div>
      <div className="progress-line">
        <span style={{ width: `${status?.progress_percentage ?? 0}%` }} />
      </div>
      <div className="detail-meta">
        <span>Stage <strong>{status?.stage ?? 'initializing'}</strong></span>
        <span>Findings <strong>{results?.vulnerabilities.length ?? status?.vulnerabilities_found ?? 0}</strong></span>
        <span>Progress <strong>{Math.round(status?.progress_percentage ?? 0)}%</strong></span>
      </div>

      {status?.status === 'completed' && (
        <div style={{
          margin: '14px 0',
          padding: '12px 16px',
          background: 'rgba(56, 189, 248, 0.08)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px'
        }}>
          <div>
            <strong style={{ color: '#38bdf8' }}>📄 PDF Assessment Report Ready</strong>
            <p style={{ margin: '2px 0 0', fontSize: '13px', color: '#94a3b8' }}>
              The report was compiled and saved to <code>/reports</code>.
            </p>
          </div>
          <a
            className="primary-button"
            href={`${baseUrl}/api/reports/scan/${scanId}/download`}
            target="_blank"
            rel="noreferrer"
            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '7px', padding: '8px 14px' }}
          >
            <Download size={15} /> Download PDF Report
          </a>
        </div>
      )}

      {status?.status === 'awaiting_review' && (
        <div className="review-gate">
          <p>Human review is required before tools can run.</p>
          <div>
            <input value={token} onChange={(event) => setToken(event.target.value)} placeholder="Reviewer token" />
            <button className="primary-button" type="button" onClick={approve} disabled={!token.trim()}>
              Approve
            </button>
          </div>
          <small>{message}</small>
        </div>
      )}

      {results && (
        <div className="finding-list">
          {results.vulnerabilities.map((vulnerability) => (
            <div className="finding-row" key={vulnerability.id}>
              <span className={`severity-label severity-label--${vulnerability.severity}`}>{vulnerability.severity}</span>
              <div>
                <strong>{vulnerability.title}</strong>
                <p>{vulnerability.description}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function FindingsView({ scans, results, onSelect }: { scans: Scan[]; results: ScanResults | null; onSelect: (id: string) => void }) { return <div className="view-stack"><section className="hero-row compact"><div><p className="eyebrow">EVIDENCE INDEX</p><h1>Verified findings</h1><p className="muted-copy">Select a completed scan to inspect the evidence and risk picture.</p></div></section><div className="panel"><div className="panel-heading"><h2>Scan sources</h2><span className="count-badge">{scans.length}</span></div>{scans.map((scan) => <ScanRow key={scan.scan_id} scan={scan} onClick={() => onSelect(scan.scan_id)} />)}{results && <div className="finding-summary"><p className="eyebrow">SELECTED RESULT</p><h2>{results.target}</h2><p className="muted-copy">Risk score: <strong>{results.risk_score.toFixed(1)}</strong></p></div>}</div></div> }
function ReportsView({ scans }: { scans: Scan[] }) { return <div className="view-stack"><section className="hero-row compact"><div><p className="eyebrow">OUTPUT STUDIO</p><h1>Reports</h1><p className="muted-copy">Generated assessment artifacts will appear here.</p></div></section><div className="panel empty-large"><FileText size={27} /><h2>No reports generated</h2><p>Complete a scan to make a report available. {scans.length} scan{scans.length === 1 ? '' : 's'} in the archive.</p></div></div> }
function AssistantView() { const [prompt, setPrompt] = useState(''); const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]); const [loading, setLoading] = useState(false); async function send(event: FormEvent) { event.preventDefault(); if (!prompt.trim() || loading) return; const next = [...messages, { role: 'user', content: prompt.trim() }]; setMessages(next); setPrompt(''); setLoading(true); try { const response = await chatOllama(next); setMessages([...next, { role: 'assistant', content: response.message?.content ?? 'No response returned.' }]); } catch { setMessages([...next, { role: 'assistant', content: 'Ollama is unavailable. Check the endpoint in Settings.' }]); } finally { setLoading(false) } } return <div className="view-stack"><section className="hero-row compact"><div><p className="eyebrow">LOCAL MODEL CONSOLE</p><h1>Ollama assistant</h1><p className="muted-copy">Chat with the configured local or network-exposed model.</p></div></section><div className="panel chat-panel"><div className="chat-messages">{messages.length === 0 && <div className="empty-state"><Bot size={24} /><span>Ready for a local model session</span></div>}{messages.map((message, index) => <div className={`chat-message chat-message--${message.role}`} key={`${message.role}-${index}`}><span>{message.role === 'user' ? 'You' : 'Ollama'}</span><p>{message.content}</p></div>)}</div><form className="chat-input" onSubmit={send}><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask the local model..." /><button className="primary-button" disabled={loading || !prompt.trim()}>{loading ? <Activity size={16} className="spin" /> : <ArrowUp size={16} />}</button></form></div></div> }
function SettingsView({ config }: { config: LlmConfig | null }) { const [host, setHost] = useState(() => { try { return new URL(config?.ollama_endpoint ?? 'http://127.0.0.1:11434').hostname } catch { return '127.0.0.1' } }); const [port, setPort] = useState(() => { try { return Number(new URL(config?.ollama_endpoint ?? 'http://127.0.0.1:11434').port || 11434) } catch { return 11434 } }); const [model, setModel] = useState(config?.ollama_model ?? 'mistral'); const [message, setMessage] = useState(''); async function test() { try { const result = await testOllama({ host, port, model }); setMessage(`${result.status}: ${result.model_available ? model + ' is available' : 'model not found'}`) } catch { setMessage('Connection failed. Check IP, port, firewall, and OLLAMA_HOST.') } } async function save() { try { await saveOllama({ host, port, model }); setMessage('Ollama connection saved.') } catch { setMessage('Could not save this endpoint.') } } return <div className="view-stack"><section className="hero-row compact"><div><p className="eyebrow">SYSTEM PREFERENCES</p><h1>Settings</h1><p className="muted-copy">The active research runtime and model configuration.</p></div></section><div className="settings-grid"><div className="panel settings-panel"><div className="panel-heading"><div><p className="eyebrow">OLLAMA CONNECTION</p><h2>Local or network model</h2></div><Bot size={18} /></div><label className="settings-field">Host or IP<input value={host} onChange={(event) => setHost(event.target.value)} placeholder="127.0.0.1 or 192.168.1.20" /></label><label className="settings-field">Port<input type="number" value={port} onChange={(event) => setPort(Number(event.target.value))} /></label><label className="settings-field">Model<input value={model} onChange={(event) => setModel(event.target.value)} placeholder="gemma-4-E4B-it-ultra-uncensored-heretic" /></label><div className="settings-actions"><button className="secondary-button" type="button" onClick={test}>Test connection</button><button className="primary-button" type="button" onClick={save}>Save endpoint</button></div><small className="settings-message">{message}</small></div><div className="panel settings-panel"><div className="panel-heading"><div><p className="eyebrow">LANGUAGE MODEL</p><h2>Provider routing</h2></div><Activity size={18} /></div><div className="setting-line"><span>Active provider</span><strong>{config?.active_provider ?? 'ollama'}</strong></div><div className="setting-line"><span>Endpoint</span><strong>{config?.ollama_endpoint ?? 'http://127.0.0.1:11434'}</strong></div><div className="setting-line"><span>Context window</span><strong>{(config?.context_window ?? 32000).toLocaleString()} tokens</strong></div><div className="setting-line"><span>Maximum output</span><strong>{(config?.max_tokens ?? 8000).toLocaleString()} tokens</strong></div></div></div></div> }

export default App
