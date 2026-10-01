export type ScanStatus = 'pending' | 'awaiting_review' | 'running' | 'completed' | 'failed' | 'cancelled'
export type LlmProvider = 'ollama' | 'claude' | 'gemini' | 'openai' | 'nvidia'

export interface Scan {
  scan_id: string
  target: string
  status: ScanStatus
  created_at: string
  duration?: number | null
  vulnerabilities: number
}

export interface ScanStatusResponse {
  scan_id: string
  target: string
  status: ScanStatus
  stage: string
  progress_percentage: number
  vulnerabilities_found: number
  error?: string | null
}

export interface ScanResults {
  scan_id: string
  target: string
  status: ScanStatus
  vulnerabilities: Vulnerability[]
  recommendations: string[]
  risk_score: number
}

export interface ScopePayload {
  version: '1'
  mode: SecurityMode
  targets: Array<{ host: string; ports: number[]; paths: string[] }>
  tool_allowlist: string[]
  max_runtime_seconds: number
}

export type SecurityMode = 'safe' | 'guarded' | 'full_access' | 'human_review'

export interface Vulnerability {
  id: string
  title: string
  severity: string
  type: string
  description: string
}

export interface LlmConfig {
  active_provider: LlmProvider
  ollama_endpoint: string
  ollama_model: string
  claude_model: string
  gemini_model: string
  openai_model: string
  max_tokens: number
  context_window: number
  claude_key_configured?: boolean
  gemini_key_configured?: boolean
  openai_key_configured?: boolean
  nvidia_key_configured?: boolean
}
