import axios from 'axios'
import type { LlmConfig, Scan, ScanResults, ScanStatusResponse, ScopePayload } from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export async function listScans(): Promise<{ scans: Scan[]; total: number }> {
  const { data } = await api.get('/api/scan/list/all')
  return data
}

export async function startScan(input: {
  target: string
  scope: ScopePayload
  mode: string
  llm_provider: string
  llm_model?: string
}) {
  const { data } = await api.post('/api/scan/start', input)
  return data as { scan_id: string; target: string; status: string; message: string }
}

export async function approveScan(scanId: string, approvalToken: string) {
  const { data } = await api.post(`/api/scan/${scanId}/approve`, { approval_token: approvalToken })
  return data
}

export async function cancelScan(scanId: string) {
  const { data } = await api.post(`/api/scan/${scanId}/cancel`)
  return data
}

export async function rescan(scanId: string) {
  const { data } = await api.post(`/api/scan/${scanId}/rescan`)
  return data as { scan_id: string; status: string; message: string }
}

export async function scheduleScan(scanId: string, runAt: string) {
  const { data } = await api.post(`/api/scan/${scanId}/schedule`, { run_at: runAt })
  return data
}

export async function runExploitation(scanId: string, options?: { mode?: string; llm_provider?: string; llm_model?: string }) {
  const { data } = await api.post(`/api/scan/${scanId}/exploit`, options ?? {})
  return data as { scan_id: string; status: string; verified_count: number; total_findings: number; message: string }
}

export async function testGemini(apiKey?: string, model?: string) {
  const { data } = await api.post('/api/config/gemini/test', { api_key: apiKey, model })
  return data as { status: string; provider: string; model: string; message: string }
}

export async function listReports() {
  const { data } = await api.get('/api/reports/')
  return data as { reports: Array<{ id: string; scan_id: string; title: string; generated_at: string; download: string }>; total: number }
}

export async function generateReport(scanId: string) {
  const { data } = await api.post('/api/reports/generate', { scan_id: scanId, format: 'pdf' })
  return data as { id: string; scan_id: string; format: string; download: string }
}

export async function listAgents() {
  const { data } = await api.get('/api/capabilities/agents')
  return data as { execution: string; agents: Array<{ name: string; status: string; role: string }> }
}

export async function getScanStatus(scanId: string): Promise<ScanStatusResponse> {
  const { data } = await api.get(`/api/scan/${scanId}/status`)
  return data
}

export async function getScanResults(scanId: string): Promise<ScanResults> {
  const { data } = await api.get(`/api/scan/${scanId}/results`)
  return data
}

export async function getLlmConfig(): Promise<LlmConfig> {
  const { data } = await api.get('/api/config/llm')
  return data
}

export async function updateLlmConfig(input: {
  active_provider?: string
  gemini_model?: string
  context_window?: number
  max_tokens?: number
  claude_api_key?: string
  gemini_api_key?: string
  openai_api_key?: string
  nvidia_api_key?: string
}) {
  const { data } = await api.put('/api/config/llm', input)
  return data as LlmConfig
}

export async function testOllama(input: { host: string; port: number; model: string }) {
  const { data } = await api.post('/api/config/ollama/test', input)
  return data as { status: string; endpoint: string; model: string; model_available: boolean; models: Array<{ name: string }> }
}

export async function saveOllama(input: { host: string; port: number; model: string }) {
  const { data } = await api.put('/api/config/ollama', input)
  return data as { status: string; ollama_endpoint: string; ollama_model: string }
}

export async function listOllamaModels() {
  const { data } = await api.get('/api/config/ollama/models')
  return data.models as Array<{ name: string }>
}

export async function chatOllama(messages: Array<{ role: string; content: string }>, options?: { model: string; num_ctx: number; temperature: number; think: boolean }) {
  const { data } = await api.post('/api/config/ollama/chat', { messages, ...options })
  return data as { message?: { role: string; content?: string; thinking?: string }; response?: string }
}

export default api
