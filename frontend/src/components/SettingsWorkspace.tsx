import { useEffect, useState } from 'react'
import { Bot, KeyRound, Save, ShieldCheck } from 'lucide-react'
import { saveOllama, testOllama, updateLlmConfig } from '../services/api'
import type { LlmConfig } from '../types'

export default function SettingsWorkspace({ config }: { config: LlmConfig | null }) {
  const [host, setHost] = useState('127.0.0.1')
  const [port, setPort] = useState(11434)
  const [model, setModel] = useState('')
  const [contextWindow, setContextWindow] = useState(32768)
  const [maxTokens, setMaxTokens] = useState(8000)
  const [keys, setKeys] = useState({ claude: '', gemini: '', openai: '', nvidia: '' })
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!config) return
    try {
      const endpoint = new URL(config.ollama_endpoint)
      setHost(endpoint.hostname)
      setPort(Number(endpoint.port || 11434))
    } catch {
      setHost('127.0.0.1')
      setPort(11434)
    }
    setModel(config.ollama_model)
    setContextWindow(config.context_window)
    setMaxTokens(config.max_tokens)
  }, [config])

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
      setMessage(`${result.status}: ${result.model_available ? 'model is available' : 'model was not found'}`)
    } catch {
      setMessage('Connection failed. Check the IP, port, firewall, and OLLAMA_HOST.')
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
        claude_api_key: keys.claude || undefined,
        gemini_api_key: keys.gemini || undefined,
        openai_api_key: keys.openai || undefined,
        nvidia_api_key: keys.nvidia || undefined,
      })
      setKeys({ claude: '', gemini: '', openai: '', nvidia: '' })
      setMessage('API keys updated in memory. Use .env for persistent secrets.')
    } catch {
      setMessage('Could not update API keys.')
    }
  }

  return <div className="view-stack"><section className="hero-row compact"><div><p className="eyebrow">SYSTEM PREFERENCES</p><h1>Settings</h1><p className="muted-copy">Explicit model, generation, and provider configuration.</p></div></section><div className="settings-grid"><section className="panel settings-panel"><div className="panel-heading"><div><p className="eyebrow">OLLAMA CONNECTION</p><h2>Local or network model</h2></div><Bot size={18} /></div><label className="settings-field">Host or IP<input value={host} onChange={(event) => setHost(event.target.value)} placeholder="127.0.0.1 or 192.168.1.20" /></label><label className="settings-field">Port<input type="number" value={port} onChange={(event) => setPort(Number(event.target.value))} /></label><label className="settings-field">Model name<input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Enter an installed Ollama model" /></label><div className="settings-actions"><button className="secondary-button" type="button" onClick={testConnection}>Test connection</button><button className="primary-button" type="button" onClick={saveConnection}><Save size={14} /> Save</button></div></section><section className="panel settings-panel"><div className="panel-heading"><div><p className="eyebrow">GENERATION</p><h2>Context and output</h2></div><ShieldCheck size={18} /></div><label className="settings-field">Context length <strong>{contextWindow.toLocaleString()} tokens</strong><input type="range" min="4096" max="131072" step="4096" value={contextWindow} onChange={(event) => setContextWindow(Number(event.target.value))} /></label><label className="settings-field">Maximum output <strong>{maxTokens.toLocaleString()} tokens</strong><input type="range" min="512" max="32768" step="512" value={maxTokens} onChange={(event) => setMaxTokens(Number(event.target.value))} /></label><div className="settings-actions"><button className="primary-button" type="button" onClick={saveGeneration}><Save size={14} /> Save generation</button></div></section></div><section className="panel settings-panel api-key-panel"><div className="panel-heading"><div><p className="eyebrow">PROVIDER CREDENTIALS</p><h2>API keys</h2></div><KeyRound size={18} /></div><p className="settings-note">Keys are never returned by the API. Empty fields leave existing values unchanged.</p><div className="key-grid"><label className="settings-field">Anthropic / Claude<input type="password" value={keys.claude} onChange={(event) => setKeys({ ...keys, claude: event.target.value })} placeholder={config?.claude_key_configured ? 'Configured' : 'Not configured'} /></label><label className="settings-field">Google / Gemini<input type="password" value={keys.gemini} onChange={(event) => setKeys({ ...keys, gemini: event.target.value })} placeholder={config?.gemini_key_configured ? 'Configured' : 'Not configured'} /></label><label className="settings-field">OpenAI<input type="password" value={keys.openai} onChange={(event) => setKeys({ ...keys, openai: event.target.value })} placeholder={config?.openai_key_configured ? 'Configured' : 'Not configured'} /></label><label className="settings-field">Nvidia<input type="password" value={keys.nvidia} onChange={(event) => setKeys({ ...keys, nvidia: event.target.value })} placeholder={config?.nvidia_key_configured ? 'Configured' : 'Not configured'} /></label></div><div className="settings-actions"><button className="primary-button" type="button" onClick={saveKeys}><KeyRound size={14} /> Save API keys</button></div></section><small className="settings-message">{message}</small></div>
}
