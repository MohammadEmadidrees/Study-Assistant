'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Message, StreamEventData } from '@/types/chat';
import { fetchSession, createSession } from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export function useChatStream(onSessionUpdated?: () => void) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSessionTitle, setActiveSessionTitle] = useState<string>('New Conversation');
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const loadSession = useCallback(async (sessionId: string) => {
    setError(null);
    try {
      const detail = await fetchSession(sessionId);
      setActiveSessionId(detail.id);
      setActiveSessionTitle(detail.title);
      setMessages(detail.messages || []);
      localStorage.setItem('study_assistant_active_session', detail.id);
    } catch (err: unknown) {
      console.warn('Could not restore previous session:', err);
      localStorage.removeItem('study_assistant_active_session');
      setActiveSessionId(null);
      setActiveSessionTitle('New Conversation');
      setMessages([]);
    }
  }, []);

  // Initialize or restore session from localStorage
  useEffect(() => {
    const savedSessionId = localStorage.getItem('study_assistant_active_session');
    if (savedSessionId) {
      loadSession(savedSessionId);
    }
  }, [loadSession]);

  const startNewSession = useCallback(async () => {
    setError(null);
    if (isStreaming && abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    try {
      const newSess = await createSession();
      setActiveSessionId(newSess.id);
      setActiveSessionTitle(newSess.title);
      setMessages([]);
      localStorage.setItem('study_assistant_active_session', newSess.id);
      if (onSessionUpdated) onSessionUpdated();
    } catch {
      const localId = crypto.randomUUID();
      setActiveSessionId(localId);
      setActiveSessionTitle('New Conversation');
      setMessages([]);
      localStorage.setItem('study_assistant_active_session', localId);
    }
  }, [isStreaming, onSessionUpdated]);

  const abortStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setMessages((prev) =>
        prev.map((msg, idx) =>
          idx === prev.length - 1 && msg.isStreaming
            ? { ...msg, isStreaming: false, content: msg.content + ' [Generation stopped]' }
            : msg
        )
      );
    }
  }, []);

  const sendMessage = useCallback(
    async (text: string, providerOverride?: string) => {
      if (!text.trim() || isStreaming) return;

      setError(null);

      let currentSessionId = activeSessionId;
      if (!currentSessionId) {
        currentSessionId = crypto.randomUUID();
        setActiveSessionId(currentSessionId);
        localStorage.setItem('study_assistant_active_session', currentSessionId);
      }

      const userMsgId = crypto.randomUUID();
      const assistantMsgId = crypto.randomUUID();

      const userMessage: Message = {
        id: userMsgId,
        role: 'user',
        content: text.trim(),
        created_at: new Date().toISOString(),
      };

      const pendingAssistantMessage: Message = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        isStreaming: true,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage, pendingAssistantMessage]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: currentSessionId,
            message: text.trim(),
            provider: providerOverride,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const errBody = await response.text();
          throw new Error(`Server returned status ${response.status}: ${errBody}`);
        }

        if (!response.body) {
          throw new Error('ReadableStream not supported by server response');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let accumulatedText = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith(':')) continue;

            if (trimmed.startsWith('data:')) {
              const rawJson = trimmed.substring(5).trim();
              if (!rawJson) continue;

              try {
                const parsed: StreamEventData = JSON.parse(rawJson);

                if (parsed.error) {
                  setError(parsed.error);
                }

                if (parsed.delta) {
                  accumulatedText += parsed.delta;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMsgId
                        ? { ...msg, content: accumulatedText }
                        : msg
                    )
                  );
                }

                if (parsed.done) {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMsgId
                        ? { ...msg, isStreaming: false, tokens_used: parsed.tokens_used }
                        : msg
                    )
                  );
                  if (onSessionUpdated) onSessionUpdated();
                }
              } catch {
                console.warn('Failed to parse SSE JSON payload:', rawJson);
              }
            }
          }
        }

        // Finalize stream state
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg
          )
        );
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
          console.log('Stream generation aborted by user.');
        } else {
          console.error('Streaming error:', err);
          const errMsg = err instanceof Error ? err.message : 'Failed to complete streaming response.';
          setError(errMsg);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId && msg.isStreaming
                ? {
                    ...msg,
                    isStreaming: false,
                    content:
                      msg.content ||
                      '⚠️ The AI provider encountered an issue while generating a response. Please try again.',
                  }
                : msg
            )
          );
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [activeSessionId, isStreaming, onSessionUpdated]
  );

  return {
    messages,
    isStreaming,
    activeSessionId,
    activeSessionTitle,
    error,
    sendMessage,
    abortStream,
    loadSession,
    startNewSession,
    setError,
  };
}
