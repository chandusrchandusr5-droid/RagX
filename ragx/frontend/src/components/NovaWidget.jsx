import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, MessageSquare, X, Send, Bot, User, HelpCircle, ChevronRight } from 'lucide-react';
import { fetchNovaGreeting, sendNovaMessage } from '../services/api';

export default function NovaWidget({ activeTab }) {
  const [isOpen, setIsOpen] = useState(false);
  const [greeting, setGreeting] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [showToast, setShowToast] = useState(true);
  const messagesEndRef = useRef(null);

  const loadGreeting = async () => {
    try {
      const data = await fetchNovaGreeting();
      setGreeting(data);
      setMessages([
        {
          id: 'welcome-msg',
          sender: 'nova',
          text: data.message,
          prompts: data.suggested_prompts || []
        }
      ]);
    } catch (err) {
      console.error("Failed to load NOVA greeting", err);
    }
  };

  useEffect(() => {
    loadGreeting();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (textToSend) => {
    const queryText = textToSend || inputValue;
    if (!queryText || !queryText.trim() || loading) return;

    const userMsg = { id: `user-${Date.now()}`, sender: 'user', text: queryText.trim() };
    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputValue('');
    setLoading(true);

    try {
      const res = await sendNovaMessage(queryText.trim(), activeTab);
      const novaMsg = { id: `nova-${Date.now()}`, sender: 'nova', text: res.response };
      setMessages((prev) => [...prev, novaMsg]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, sender: 'nova', text: 'Sorry, I encountered an issue connecting to NOVA AI Copilot.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {/* Floating Welcome Toast */}
      {showToast && !isOpen && (
        <div className="mb-3 max-w-xs bg-slate-900/95 border border-indigo-500/30 p-3.5 rounded-2xl shadow-xl shadow-indigo-500/10 backdrop-blur-md flex items-start gap-3 text-xs text-slate-200 animate-bounce">
          <div className="p-2 rounded-xl bg-indigo-600/20 text-indigo-400 shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="space-y-1 flex-1">
            <div className="font-bold text-white flex items-center justify-between">
              <span>NOVA AI Copilot</span>
              <button onClick={() => setShowToast(false)} className="text-slate-500 hover:text-slate-300">
                <X className="w-3 h-3" />
              </button>
            </div>
            <p className="text-[11px] text-slate-400 leading-snug">
              Hi! Need help with RAGX, Answer Reliability (S_Ans), or Hallucinations? Click to chat!
            </p>
          </div>
        </div>
      )}

      {/* Expanded Chat Drawer */}
      {isOpen && (
        <div className="w-80 sm:w-96 h-[460px] bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden mb-3 glass-panel">
          {/* Drawer Header */}
          <div className="p-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-white flex items-center gap-1.5">
                  NOVA <span className="text-[10px] font-semibold uppercase px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300">AI Copilot</span>
                </h3>
                <p className="text-[10px] text-slate-400">Context: RAGX Platform ({activeTab})</p>
              </div>
            </div>
            <button onClick={() => setIsOpen(false)} className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages Body */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 text-xs">
            {messages.map((m) => (
              <div key={m.id} className={`flex items-start gap-2.5 ${m.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                  m.sender === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-indigo-400'
                }`}>
                  {m.sender === 'user' ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
                </div>

                <div className={`p-3 rounded-2xl max-w-[82%] leading-relaxed ${
                  m.sender === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none'
                }`}>
                  <p className="whitespace-pre-line">{m.text}</p>

                  {/* Suggested Quick Prompts */}
                  {m.prompts && m.prompts.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-slate-800 space-y-1.5">
                      <span className="text-[10px] uppercase font-semibold text-slate-400">Quick Questions:</span>
                      {m.prompts.map((p, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendMessage(p)}
                          className="w-full text-left p-1.5 rounded-lg bg-slate-800/60 hover:bg-indigo-600/20 hover:border-indigo-500/30 border border-slate-700/50 text-[11px] text-indigo-300 transition flex items-center justify-between"
                        >
                          <span>{p}</span>
                          <ChevronRight className="w-3 h-3 text-slate-500" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-slate-400 text-[11px]">
                <Bot className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                <span>NOVA is thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Footer */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2"
          >
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask NOVA about RAGX..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={loading || !inputValue.trim()}
              className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl transition"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}

      {/* Floating Toggle Button */}
      <button
        onClick={() => {
          setIsOpen(!isOpen);
          setShowToast(false);
        }}
        className="w-13 h-13 rounded-2xl bg-gradient-to-tr from-indigo-600 to-teal-400 p-0.5 shadow-xl shadow-indigo-600/30 hover:scale-105 transition-all flex items-center justify-center"
      >
        <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
          <Sparkles className="w-6 h-6 text-indigo-400" />
        </div>
      </button>
    </div>
  );
}
