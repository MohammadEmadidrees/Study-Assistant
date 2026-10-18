export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokens_used?: number;
  created_at?: string;
  isStreaming?: boolean;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface StreamEventData {
  session_id: string;
  delta: string;
  done: boolean;
  error?: string;
  tokens_used?: number;
}
