import { Session, SessionDetail } from '@/types/chat';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/sessions`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to load sessions: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to load conversation: ${res.statusText}`);
  }
  return res.json();
}

export async function createSession(title: string = 'New Conversation'): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create session: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to delete session: ${res.statusText}`);
  }
}

export async function checkBackendHealth(): Promise<{ status: string; database: string; redis: string }> {
  const res = await fetch(`${API_BASE}/health`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error('Backend offline');
  }
  return res.json();
}
