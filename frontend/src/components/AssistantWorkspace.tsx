import { FormEvent, useEffect, useRef, useState } from 'react'
import { Brain, FolderOpen, Paperclip, Send, SlidersHorizontal, X } from 'lucide-react'
import { chatOllama } from '../services/api'
import type { LlmConfig } from '../types'

type ChatMessage = { role: 'user' | 'assistant'; content: string; thinking?: string }
type Attachment = { id: string; name: string; size: number; content: string; binary: boolean }

const MAX_ATTACHMENT_BYTES = 200_000
const TEXT_EXTENSIONS = /\.(txt|md|json|yaml|yml|csv|log|py|js|jsx|ts|tsx|html|css|xml|toml|ini|sh|ps1|c|cpp|h|go|rs|java)$/i

export default function AssistantWorkspace({ config }: { config: LlmConfig | null }) {
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [model, setModel] = useState(config?.ollama_model ?? '')
  const [contextWindow, setContextWindow] = useState(config?.context_window ?? 32768)
  const [temperature, setTemperature] = useState(0.2)
  const [reasoning, setReasoning] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const folderInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!config) return
    setModel(config.ollama_model)
    setContextWindow(config.context_window)
  }, [config])

  async function addFiles(fileList: FileList | null) {
    if (!fileList) return
    let total = attachments.reduce((sum, file) => sum + file.size, 0)
    const next: Attachment[] = []
    for (const file of Array.from(fileList)) {
      if (total >= MAX_ATTACHMENT_BYTES) break
      const remaining = MAX_ATTACHMENT_BYTES - total
      const size = Math.min(file.size, remaining)
      const binary = !file.type.startsWith('text/') && !TEXT_EXTENSIONS.test(file.name)
      let content = `[binary attachment: ${file.name}]`
      if (!binary) content = (await file.slice(0, size).text()).slice(0, remaining)
      next.push({ id: `${file.name}-${file.lastModified}-${next.length}`, name: file.webkitRelativePath || file.name, size, content, binary })
      total += size
    }
    setAttachments((current) => [...current, ...next])
  }

  function removeAttachment(id: string) {
    setAttachments((current) => current.filter((file) => file.id !== id))
  }

  async function send(event: FormEvent) {
    event.preventDefault()
    if (!prompt.trim() || loading) return
    setError('')
    const attachmentContext = attachments.length
      ? `\n\n[ATTACHMENT CONTEXT]\n${attachments.map((file) => `--- ${file.name} ---\n${file.content}`).join('\n')}`
      : ''
    const userMessage: ChatMessage = { role: 'user', content: `${prompt.trim()}${attachmentContext}` }
    const next = [...messages, userMessage]
    setMessages(next)
    setPrompt('')
    setLoading(true)
    try {
      const response = await chatOllama(next.map(({ role, content }) => ({ role, content })), {
        model,
        num_ctx: contextWindow,
        temperature,
        think: reasoning,
      })
      const output = response.message?.content || response.response || ''
      if (!output && !response.message?.thinking) throw new Error('Ollama returned an empty response')
      setMessages([...next, { role: 'assistant', content: output || 'Reasoning completed without a visible answer.', thinking: response.message?.thinking }])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Ollama request failed')
      setMessages(messages)
    } finally {
      setLoading(false)
    }
  }

  return <div className="view-stack assistant-workspace">
    <section className="hero-row compact"><div><p className="eyebrow">LOCAL MODEL CONSOLE</p><h1>Ollama assistant</h1><p className="muted-copy">Choose a model, tune context, and add local files to the conversation.</p></div><button className={`icon-button control-toggle ${showControls ? 'control-toggle--active' : ''}`} onClick={() => setShowControls((open) => !open)} title="Toggle model controls"><SlidersHorizontal size={18} /></button></section>
    {showControls && <section className="assistant-controls panel"><label>Model name<input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Enter an installed Ollama model" /></label><label>Context <strong>{contextWindow.toLocaleString()}</strong><input type="range" min="4096" max="131072" step="4096" value={contextWindow} onChange={(event) => setContextWindow(Number(event.target.value))} /></label><label>Temperature <strong>{temperature.toFixed(1)}</strong><input type="range" min="0" max="1.5" step="0.1" value={temperature} onChange={(event) => setTemperature(Number(event.target.value))} /></label><label className="toggle-label"><input type="checkbox" checked={reasoning} onChange={(event) => setReasoning(event.target.checked)} /><Brain size={15} /> Reasoning mode</label></section>}
    <section className="panel chat-panel"><div className="chat-messages">{messages.map((message, index) => <div className={`chat-message chat-message--${message.role}`} key={`${message.role}-${index}`}><span>{message.role === 'user' ? 'You' : model || 'Ollama'}</span>{message.thinking && <details className="thinking-block"><summary>Reasoning trace</summary><p>{message.thinking}</p></details>}<p>{message.content}</p></div>)}{loading && <div className="assistant-loading"><span /><span /><span /> Generating response...</div>}</div>{error && <div className="chat-error">{error}</div>}{attachments.length > 0 && <div className="attachment-list">{attachments.map((file) => <span className="attachment-chip" key={file.id}><Paperclip size={12} />{file.name}<button type="button" onClick={() => removeAttachment(file.id)} aria-label={`Remove ${file.name}`}><X size={12} /></button></span>)}</div>}<form className="chat-input" onSubmit={send}><input ref={fileInput} type="file" multiple hidden onChange={(event) => { void addFiles(event.target.files); event.currentTarget.value = '' }} /><input ref={folderInput} type="file" multiple hidden onChange={(event) => { void addFiles(event.target.files); event.currentTarget.value = '' }} /><button type="button" className="icon-button" onClick={() => fileInput.current?.click()} title="Attach files"><Paperclip size={17} /></button><button type="button" className="icon-button" onClick={() => { folderInput.current?.setAttribute('webkitdirectory', ''); folderInput.current?.click() }} title="Attach folder"><FolderOpen size={17} /></button><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask the local model..." /><button className="primary-button" disabled={loading || !prompt.trim() || !model} title="Send message">{loading ? <span className="button-spinner" /> : <Send size={16} />}</button></form></section>
  </div>
}
