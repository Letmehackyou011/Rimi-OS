import { useEffect, useState } from 'react'
import { Bot, CheckCircle2, KeyRound, LoaderCircle, Save, ShieldCheck, Sparkles } from 'lucide-react'
import { saveOllama, testGemini, testOllama, updateLlmConfig } from '../services/api'
import type { LlmConfig, LlmProvider } from '../types'

export default function SettingsWorkspace({ config }: { config: LlmConfig | null }) {
  const [activeProvider, setActiveProvider] = useState<LlmProvider>('ollama')
  const [host, setHost] = useState('127.0.0.1')
  const [port, setPort] = useState(11434)
  const [model, setModel] = useState('')
  const [geminiModel, setGeminiModel] = useState('gemini-2.0-flash')
  const [contextWindow, setContextWindow] = useState(32768)
  const [maxTokens, setMaxTokens] = useState(8000)
  const [keys, setKeys] = useState({ claude: '', gemini: '', openai: '', nvidia: '' })
  const [message, setMessage] = useState('')
  const [testingGemini, setTestingGemini] = useState(false)

  useEffect(() => {
    if (!config) return
    setActiveProvider(config.active_provider || 'ollama')
    try {
      const endpoint = config.ollama_endpoint 
     ? new URL(config.ollama_endpoint) 
     : { hostname: '127.0.0.1', port: '11434' }
      setHost(endpoint.hostname)
      setPort(Number(endpoint.port || 11434))
    } catch {
      setHost('127.0.0.1')
      setPort(11434)
    }
    setModel(config.ollama_model || '')
    setGeminiModel(config.gemini_model || 'gemini-3-flash-preview')
    setContextWindow(config.context_window || 32768)
    setMaxTokens(config.max_tokens || 8000)
  }, [config])

  async function saveProvider() {
    try {
      await updateLlmConfig({ active_provider: activeProvider, gemini_model: geminiModel })
      setMessage(`Active AI provider updated to: ${activeProvider.toUpperCase()}`)
    } catch {
      setMessage('Could not update active provider.')
    }
  }

  async function saveConnection() {
    try {
      await saveOllama({ host, port, model })
      setMessage('Ollama connection saved.')
    } catch {
      setMessage('Could not save the Ollama connection.')
    }
  }

  async function testConnection() {
    try {
      const result = await testOllama({ host, port, model })
      setMessage(`${result.status}: ${result.model_available ? model + ' is available' : 'model was not found'}`)
    } catch {
      setMessage('Connection failed. Check the IP, port, firewall, and OLLAMA_HOST.')
    }
  }

  async function testGeminiKey() {
    setTestingGemini(true)
    setMessage('')
    try {
      const res = await testGemini(keys.gemini || undefined, geminiModel)
      setMessage(`✅ ${res.message}`)
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || 'Could not verify Gemini key.'
      setMessage(`❌ ${errMsg}`)
    } finally {
      setTestingGemini(false)
    }
  }

  async function saveGeneration() {
    try {
      await updateLlmConfig({ context_window: contextWindow, max_tokens: maxTokens })
      setMessage('Generation settings saved.')
    } catch {
      setMessage('Could not save generation settings.')
    }
  }

  async function saveKeys() {
    try {
      await updateLlmConfig({
        active_provider: activeProvider,
        gemini_model: geminiModel,
        claude_api_key: keys.claude || undefined,
        gemini_api_key: keys.gemini || undefined,
        openai_api_key: keys.openai || undefined,
        nvidia_api_key: keys.nvidia || undefined,
      })
      setKeys({ claude: '', gemini: '', openai: '', nvidia: '' })
      setMessage('API credentials saved and applied to running agents.')
    } catch {
      setMessage('Could not update API keys.')
    }
  }

  return (
    <div className="view-stack">
      <section className="hero-row compact">
        <div>
          <p className="eyebrow">SYSTEM PREFERENCES</p>
          <h1>AI Engine & Credentials</h1>
          <p className="muted-copy">
            Select your preferred AI model provider (Google Gemini, Local Ollama, Claude, or OpenAI) and manage API keys.
          </p>
        </div>
      </section>

      {/* Active AI Provider Switcher */}
      <section className="panel" style={{ marginBottom: '16px' }}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">ORCHESTRATOR BRAIN</p>
            <h2>Active AI Provider</h2>
          </div>
          <Sparkles size={18} />
        </div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap', padding: '10px 0' }}>
          <label style={{ minWidth: '220px' }}>
            Primary Provider
            <select
              value={activeProvider}
              onChange={(e) => setActiveProvider(e.target.value as LlmProvider)}
              style={{ width: '100%', marginTop: '6px' }}
            >
              <option value="gemini">Google Gemini (Cloud Ultra-Fast)</option>
              <option value="ollama">Ollama (Local Offline)</option>
              <option value="openai">OpenAI (GPT-4o)</option>
              <option value="claude">Anthropic (Claude 3.5 Sonnet)</option>
            </select>
          </label>

          {activeProvider === 'gemini' && (
            <label style={{ minWidth: '220px' }}>
              Gemini Model
              <select
                value={geminiModel}
                onChange={(e) => setGeminiModel(e.target.value)}
                style={{ width: '100%', marginTop: '6px' }}
              >
                <option value="gemini-3-flash-preview">gemini-3-flash-preview (Preview)</option>
                <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                <option value="gemini-1.5-pro">gemini-1.5-pro</option>
              </select>
            </label>
          )}

          <div style={{ marginTop: '22px' }}>
            <button className="primary-button" type="button" onClick={saveProvider}>
              <Save size={14} /> Apply Provider
            </button>
          </div>
        </div>
      </section>

      <div className="settings-grid">
        {/* Local Ollama Settings */}
        <section className="panel settings-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">OLLAMA RUNTIME</p>
              <h2>Local or Network Model</h2>
            </div>
            <Bot size={18} />
          </div>
          <label className="settings-field">
            Host or IP
            <input value={host} onChange={(event) => setHost(event.target.value)} placeholder="127.0.0.1 or 192.168.1.20" />
          </label>
          <label className="settings-field">
            Port
            <input type="number" value={port} onChange={(event) => setPort(Number(event.target.value))} />
          </label>
          <label className="settings-field">
            Model name
            <input value={model} onChange={(event) => setModel(event.target.value)} placeholder="e.g. mistral or llama3" />
          </label>
          <div className="settings-actions">
            <button className="secondary-button" type="button" onClick={testConnection}>
              Test connection
            </button>
            <button className="primary-button" type="button" onClick={saveConnection}>
              <Save size={14} /> Save Ollama
            </button>
          </div>
        </section>

        {/* Generation Token Bounds */}
        <section className="panel settings-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">GENERATION BOUNDS</p>
              <h2>Context & Output Tokens</h2>
            </div>
            <ShieldCheck size={18} />
          </div>
          <label className="settings-field">
            Context length <strong>{contextWindow.toLocaleString()} tokens</strong>
            <input
              type="range"
              min="4096"
              max="131072"
              step="4096"
              value={contextWindow}
              onChange={(event) => setContextWindow(Number(event.target.value))}
            />
          </label>
          <label className="settings-field">
            Maximum output <strong>{maxTokens.toLocaleString()} tokens</strong>
            <input
              type="range"
              min="512"
              max="32768"
              step="512"
              value={maxTokens}
              onChange={(event) => setMaxTokens(Number(event.target.value))}
            />
          </label>
          <div className="settings-actions">
            <button className="primary-button" type="button" onClick={saveGeneration}>
              <Save size={14} /> Save generation
            </button>
          </div>
        </section>
      </div>

      {/* Cloud API Keys & Credentials */}
      <section className="panel settings-panel api-key-panel" style={{ marginTop: '16px' }}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">PROVIDER CREDENTIALS</p>
            <h2>API Keys & Secret Setup</h2>
          </div>
          <KeyRound size={18} />
        </div>
        <p className="settings-note">
          Enter your API key below. Keys are securely stored and applied to all agents with automatic fallback.
        </p>

        <div className="key-grid">
          {/* Google Gemini */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label className="settings-field" style={{ margin: 0 }}>
              Google Gemini API Key
              <input
                type="password"
                value={keys.gemini}
                onChange={(event) => setKeys({ ...keys, gemini: event.target.value })}
                placeholder={config?.gemini_key_configured ? 'Key configured (enter to replace)' : 'AIzaSy...'}
              />
            </label>
            <button
              className="secondary-button"
              type="button"
              onClick={testGeminiKey}
              disabled={testingGemini}
              style={{ alignSelf: 'flex-start', marginTop: '4px', fontSize: '12px' }}
            >
              {testingGemini ? <LoaderCircle size={13} className="spin" /> : <Sparkles size={13} />} Test Gemini Key
            </button>
          </div>

          {/* Anthropic Claude */}
          <label className="settings-field">
            Anthropic Claude Key
            <input
              type="password"
              value={keys.claude}
              onChange={(event) => setKeys({ ...keys, claude: event.target.value })}
              placeholder={config?.claude_key_configured ? 'Configured' : 'sk-ant-...'}
            />
          </label>

          {/* OpenAI */}
          <label className="settings-field">
            OpenAI Key
            <input
              type="password"
              value={keys.openai}
              onChange={(event) => setKeys({ ...keys, openai: event.target.value })}
              placeholder={config?.openai_key_configured ? 'Configured' : 'sk-...'}
            />
          </label>

          {/* Nvidia */}
          <label className="settings-field">
            Nvidia NIM Key
            <input
              type="password"
              value={keys.nvidia}
              onChange={(event) => setKeys({ ...keys, nvidia: event.target.value })}
              placeholder={config?.nvidia_key_configured ? 'Configured' : 'nvapi-...'}
            />
          </label>
        </div>

        <div className="settings-actions" style={{ marginTop: '16px' }}>
          <button className="primary-button" type="button" onClick={saveKeys}>
            <KeyRound size={14} /> Save API Credentials
          </button>
        </div>
      </section>

      {message && (
        <div style={{ marginTop: '12px', padding: '10px 14px', borderRadius: '6px', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
          <small className="settings-message">{message}</small>
        </div>
      )}
    </div>
  )
}
