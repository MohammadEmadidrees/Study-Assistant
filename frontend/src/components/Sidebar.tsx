'use client';

import React from 'react';
import { Session } from '@/types/chat';
import { Plus, MessageSquare, Trash2, Sparkles, BookOpen } from 'lucide-react';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  isOpen,
  onClose,
}) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 z-50 w-72 bg-slate-900 border-r border-slate-800 flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* App Logo & Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-slate-100 text-sm tracking-wide flex items-center gap-1.5">
                Study Assistant <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              </h1>
              <p className="text-xs text-slate-400">Claude AI Companion</p>
            </div>
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={() => {
              onNewSession();
              onClose();
            }}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-sm font-medium transition-all shadow-md shadow-indigo-600/20 active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 scrollbar-thin scrollbar-thumb-slate-800">
          <div className="px-2 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Recent Conversations
          </div>

          {sessions.length === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-slate-400">
              No conversations yet. Start a new session above!
            </div>
          ) : (
            sessions.map((session) => {
              const isActive = session.id === activeSessionId;
              return (
                <div
                  key={session.id}
                  className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl text-xs transition-all cursor-pointer ${
                    isActive
                      ? 'bg-slate-800 text-slate-100 font-medium shadow-sm'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                  }`}
                  onClick={() => {
                    onSelectSession(session.id);
                    onClose();
                  }}
                >
                  <div className="flex items-center space-x-2.5 overflow-hidden pr-2">
                    <MessageSquare className={`w-4 h-4 shrink-0 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                    <span className="truncate">{session.title || 'Untitled Session'}</span>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    title="Delete session"
                    className="opacity-0 group-hover:opacity-100 hover:text-red-400 text-slate-400 p-1 rounded-md transition-opacity"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Provider Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-900/50">
          <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-slate-800/70 border border-slate-700/50">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-slate-300 font-medium">Claude 3.5 Sonnet</span>
            </div>
            <span className="text-[10px] text-slate-400 bg-slate-700/60 px-1.5 py-0.5 rounded">Adapter</span>
          </div>
        </div>
      </aside>
    </>
  );
};
