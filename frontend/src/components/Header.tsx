'use client';

import React from 'react';
import { Menu, Plus } from 'lucide-react';

interface HeaderProps {
  sessionTitle: string;
  onToggleSidebar: () => void;
  onNewSession: () => void;
  backendOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  sessionTitle,
  onToggleSidebar,
  onNewSession,
  backendOnline,
}) => {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-4 flex items-center justify-between z-30 shrink-0">
      <div className="flex items-center space-x-3">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden text-slate-400 hover:text-slate-100 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          title="Toggle sessions"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-2 overflow-hidden">
          <span className="w-2 h-2 rounded-full bg-indigo-500 hidden sm:inline-block" />
          <h2 className="text-sm font-medium text-slate-100 truncate max-w-[200px] sm:max-w-md">
            {sessionTitle || 'New Conversation'}
          </h2>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Backend connectivity indicator */}
        <div
          className={`flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-full border ${
            backendOnline
              ? 'text-emerald-400 bg-emerald-950/30 border-emerald-800/40'
              : 'text-amber-400 bg-amber-950/30 border-amber-800/40'
          }`}
          title={backendOnline ? 'Backend API connected' : 'Connecting to API'}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              backendOnline ? 'bg-emerald-400' : 'bg-amber-400 animate-ping'
            }`}
          />
          <span className="hidden sm:inline font-mono text-[11px]">
            {backendOnline ? 'API Connected' : 'Connecting'}
          </span>
        </div>

        <button
          onClick={onNewSession}
          className="hidden sm:flex items-center space-x-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-colors border border-slate-700/60"
        >
          <Plus className="w-3.5 h-3.5 text-indigo-400" />
          <span>New Chat</span>
        </button>
      </div>
    </header>
  );
};
