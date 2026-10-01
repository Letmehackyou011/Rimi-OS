import { useEffect, useState } from 'react'
import { Activity, Bot, CheckCircle2, ShieldAlert } from 'lucide-react'
import { listAgents } from '../services/api'

type Agent = { name: string; status: string; role: string }

export default function AgentsWorkspace() {
  const [agents, setAgents] = useState<Agent[]>([])
  useEffect(() => { void listAgents().then((response) => setAgents(response.agents)).catch(() => undefined) }, [])
  return <div className="view-stack"><section className="hero-row compact"><div><p className="eyebrow">AGENT ORCHESTRA</p><h1>Connected agents</h1><p className="muted-copy">LangGraph coordinates the enabled agents through scoped stages and shared scan state.</p></div><div className="agent-execution-badge"><Activity size={15} /> LangGraph pipeline</div></section><section className="panel agent-roster">{agents.map((agent) => <div className="agent-roster-row" key={agent.name}><div className="agent-roster-icon">{agent.status === 'human_review' ? <ShieldAlert size={17} /> : <Bot size={17} />}</div><div><strong>{agent.name}</strong><small>{agent.role}</small></div><span className={`agent-roster-status agent-roster-status--${agent.status}`}>{agent.status === 'enabled' ? <CheckCircle2 size={13} /> : <ShieldAlert size={13} />}{agent.status}</span></div>)}</section></div>
}
