'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, Sparkles } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  onStopStreaming: () => void;
  isStreaming: boolean;
  hasMessages: boolean;
}

const SUGGESTIONS = [
  'Explain Newton\'s laws of motion with everyday analogies',
  'How does gradient descent work in machine learning?',
  'Help me design a 5-day study plan for organic chemistry',
  'Solve step-by-step: Find the derivative of f(x) = x^3 * e^(2x)',
];

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onStopStreaming,
  isStreaming,
  hasMessages,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isStreaming) return;
    onSendMessage(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-4">
      {/* Suggestions for empty state */}
      {!hasMessages && (
        <div className="mb-4">
          <div className="text-xs font-semibold text-slate-400 mb-2.5 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Try asking a study question:</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {SUGGESTIONS.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => onSendMessage(suggestion)}
                className="text-left text-xs text-slate-300 bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 hover:border-indigo-500/50 p-2.5 rounded-xl transition-all shadow-sm group"
              >
                <span className="group-hover:text-indigo-300 transition-colors">
                  {suggestion}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input container */}
      <form
        onSubmit={handleSubmit}
        className="relative flex items-end gap-2 bg-slate-900/80 border border-slate-700/80 rounded-2xl p-2 shadow-xl shadow-slate-950/40 backdrop-blur-md focus-within:border-indigo-500/80 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all"
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question or paste concepts to study... (Press Enter to send)"
          rows={1}
          disabled={isStreaming}
          className="flex-1 max-h-44 bg-transparent text-slate-100 placeholder-slate-400 text-sm px-3 py-2 outline-none resize-none leading-relaxed disabled:opacity-50"
        />

        {isStreaming ? (
          <button
            type="button"
            onClick={onStopStreaming}
            className="w-10 h-10 rounded-xl bg-red-600/80 hover:bg-red-500 text-white flex items-center justify-center shrink-0 transition-all active:scale-95 shadow-md shadow-red-600/20"
            title="Stop generating"
          >
            <Square className="w-4 h-4 fill-white" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-400 text-white flex items-center justify-center shrink-0 transition-all active:scale-95 shadow-md shadow-indigo-600/20 disabled:shadow-none"
            title="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </form>

      <div className="mt-2 text-center text-[11px] text-slate-400">
        AI responses are streamed token-by-token and persisted automatically to your session history.
      </div>
    </div>
  );
};
