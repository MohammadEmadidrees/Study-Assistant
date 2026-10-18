'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { MessageItem } from '@/components/MessageItem';
import { ChatInput } from '@/components/ChatInput';
import { useChatStream } from '@/hooks/useChatStream';
import { fetchSessions, deleteSession, checkBackendHealth } from '@/lib/api';
import { Session } from '@/types/chat';
import { AlertCircle, BookOpen, GraduationCap, Brain, Cpu } from 'lucide-react';

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadAllSessions = useCallback(async () => {
    try {
      const data = await fetchSessions();
      setSessions(data);
    } catch (e) {
      console.warn('Could not load sessions list:', e);
    }
  }, []);

  const {
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
  } = useChatStream(loadAllSessions);

  // Poll backend health and load sessions
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await checkBackendHealth();
        setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }
    };

    checkHealth();
    loadAllSessions();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, [loadAllSessions]);

  // Auto-scroll to bottom on incoming message deltas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        startNewSession();
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to delete session: ${message}`);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Session Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={loadSession}
        onNewSession={startNewSession}
        onDeleteSession={handleDeleteSession}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Header
          sessionTitle={activeSessionTitle}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          onNewSession={startNewSession}
          backendOnline={backendOnline}
        />

        {/* Error notification banner */}
        {error && (
          <div className="mx-4 mt-3 p-3 bg-red-950/60 border border-red-800/60 rounded-xl flex items-center justify-between text-xs text-red-200">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-200 font-bold ml-2 text-sm"
            >
              ×
            </button>
          </div>
        )}

        {/* Message Viewport */}
        <div className="flex-1 overflow-y-auto px-4 py-6 scrollbar-thin scrollbar-thumb-slate-800">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.length === 0 ? (
              <div className="py-12 sm:py-20 text-center flex flex-col items-center">
                <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 p-0.5 shadow-xl shadow-indigo-500/25 mb-6 flex items-center justify-center">
                  <div className="w-full h-full bg-slate-950 rounded-[22px] flex items-center justify-center">
                    <GraduationCap className="w-8 h-8 text-indigo-400" />
                  </div>
                </div>

                <h2 className="text-2xl font-bold text-slate-100 mb-2 tracking-tight">
                  Welcome to Study Assistant
                </h2>
                <p className="text-sm text-slate-400 max-w-md mb-8">
                  Your dedicated AI learning companion powered by Claude. Ask questions, explore difficult topics, and study with token-streamed responses.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-2xl text-left">
                  <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 hover:border-indigo-500/40 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-indigo-950/80 text-indigo-400 flex items-center justify-center mb-2.5">
                      <Brain className="w-4 h-4" />
                    </div>
                    <h3 className="text-xs font-semibold text-slate-200 mb-1">Concept Explanations</h3>
                    <p className="text-[11px] text-slate-400">Step-by-step clarity on math, physics, code, and science.</p>
                  </div>

                  <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 hover:border-purple-500/40 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-purple-950/80 text-purple-400 flex items-center justify-center mb-2.5">
                      <Cpu className="w-4 h-4" />
                    </div>
                    <h3 className="text-xs font-semibold text-slate-200 mb-1">Token-by-Token SSE</h3>
                    <p className="text-[11px] text-slate-400">Real-time streaming via robust Server-Sent Events architecture.</p>
                  </div>

                  <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 hover:border-pink-500/40 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-pink-950/80 text-pink-400 flex items-center justify-center mb-2.5">
                      <BookOpen className="w-4 h-4" />
                    </div>
                    <h3 className="text-xs font-semibold text-slate-200 mb-1">Dual-Tier Memory</h3>
                    <p className="text-[11px] text-slate-400">PostgreSQL persistence with Redis caching for instant reload.</p>
                  </div>
                </div>
              </div>
            ) : (
              messages.map((msg) => <MessageItem key={msg.id} message={msg} />)
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Bar */}
        <ChatInput
          onSendMessage={sendMessage}
          onStopStreaming={abortStream}
          isStreaming={isStreaming}
          hasMessages={messages.length > 0}
        />
      </div>
    </div>
  );
}
