'use client';

import React, { useState } from 'react';
import { Message } from '@/types/chat';
import { Bot, User, Copy, Check, Sparkles } from 'lucide-react';

interface MessageItemProps {
  message: Message;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const [copied, setCopied] = useState(false);
  const isAssistant = message.role === 'assistant';

  const handleCopy = () => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Helper to render formatted code blocks and paragraphs cleanly
  const renderFormattedContent = (content: string) => {
    if (!content && message.isStreaming) {
      return (
        <span className="inline-flex items-center space-x-1 text-slate-400 italic">
          <span>Thinking</span>
          <span className="animate-bounce">.</span>
          <span className="animate-bounce delay-100">.</span>
          <span className="animate-bounce delay-200">.</span>
        </span>
      );
    }

    // Split on code fences (```)
    const parts = content.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const lines = part.slice(3, -3).trim().split('\n');
        const language = lines[0].trim() || 'code';
        const code = lines.slice(1).join('\n') || lines[0];

        return (
          <div key={index} className="my-3 rounded-lg overflow-hidden border border-slate-700 bg-slate-950 font-mono text-xs">
            <div className="bg-slate-800/80 px-3 py-1.5 flex justify-between items-center text-[11px] text-slate-400">
              <span>{language}</span>
              <button
                onClick={() => navigator.clipboard.writeText(code)}
                className="hover:text-slate-200 transition-colors"
              >
                Copy
              </button>
            </div>
            <pre className="p-3 overflow-x-auto text-emerald-400">
              <code>{code}</code>
            </pre>
          </div>
        );
      }

      return (
        <div key={index} className="whitespace-pre-wrap leading-relaxed text-sm">
          {part}
        </div>
      );
    });
  };

  return (
    <div
      className={`flex items-start gap-3 py-4 px-4 rounded-2xl transition-all ${
        isAssistant
          ? 'bg-slate-900/60 border border-slate-800/80'
          : 'bg-indigo-950/20 border border-indigo-900/30'
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center shadow-md ${
          isAssistant
            ? 'bg-gradient-to-tr from-purple-600 to-indigo-600 text-white shadow-indigo-600/20'
            : 'bg-indigo-600 text-white shadow-indigo-500/20'
        }`}
      >
        {isAssistant ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
      </div>

      {/* Message Body */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-xs tracking-wide text-slate-200">
              {isAssistant ? 'Study Assistant (Claude)' : 'You'}
            </span>
            {isAssistant && message.isStreaming && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium text-purple-400 bg-purple-950/60 px-1.5 py-0.5 rounded border border-purple-800/40">
                <Sparkles className="w-2.5 h-2.5 animate-spin" /> Streaming
              </span>
            )}
          </div>

          {isAssistant && message.content && (
            <button
              onClick={handleCopy}
              className="text-slate-400 hover:text-slate-200 p-1 rounded transition-colors"
              title="Copy message"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        <div className="text-slate-100 text-sm">
          {renderFormattedContent(message.content)}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 ml-1 bg-indigo-400 animate-pulse align-middle" />
          )}
        </div>

        {message.tokens_used ? (
          <div className="mt-2 text-[10px] text-slate-400 flex items-center space-x-2">
            <span>Tokens: {message.tokens_used}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
};
