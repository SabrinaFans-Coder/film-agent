const BASE = "";

export interface SessionInfo {
  session_id: string;
  last_preview: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  healthy?: boolean;
}

export interface HistoryMessage {
  role: string;
  content: string;
  timestamp: string;
}

export interface SessionListResponse {
  sessions: SessionInfo[];
  total: number;
  limit: number;
  offset: number;
}

export async function listSessions(
  limit = 20,
  offset = 0
): Promise<SessionListResponse> {
  const res = await fetch(`${BASE}/sessions?limit=${limit}&offset=${offset}`);
  return res.json();
}

export async function getMessages(
  sessionId: string
): Promise<{ session_id: string; messages: HistoryMessage[] }> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error("Session not found");
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}`, { method: "DELETE" });
}

export function streamChat(message: string, sessionId?: string): EventSource {
  const params = new URLSearchParams({ message });
  if (sessionId) params.set("session_id", sessionId);
  return new EventSource(`${BASE}/chat/stream?${params}`);
}
