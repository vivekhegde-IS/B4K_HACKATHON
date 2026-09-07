const agentUrl = import.meta.env.VITE_AGENT_URL || 'http://localhost:8003'

export async function getAgentHealth() {
  const response = await fetch(`${agentUrl}/health`)
  if (!response.ok) throw new Error('Agent service is unavailable')
  return response.json()
}