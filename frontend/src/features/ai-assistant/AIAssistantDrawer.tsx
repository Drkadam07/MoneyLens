import React, { useState } from 'react';
import { Bot, Send, Sparkles, AlertTriangle, Layers, Calendar, ArrowRight } from 'lucide-react';
import api from '../../services/api';
import { AIChatResponse } from '../../types';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  responsePayload?: AIChatResponse;
}

export const AIAssistantDrawer: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      content:
        'Hello! I am your MoneyLens AI Financial Assistant. Ask me anything about your cash flow, category breakdowns, recurring subscriptions, or transaction history. All my answers are grounded strictly in your verified bank ledger records.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sampleQuestions = [
    'How much did I spend this month?',
    'What is my category breakdown for October?',
    'Show transactions above ₹5,000',
    'Compare my expenses in September and October',
    'What are my recurring payments?',
  ];

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      content: textToSend,
    };
    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInput('');
    setLoading(true);

    try {
      const resp = await api.post<AIChatResponse>('/ai/chat', { message: textToSend });
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        content: resp.data.answer,
        responsePayload: resp.data,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        content: 'I encountered an error querying the financial ledger. Please try again.',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const formatINR = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(num);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0B0F19] overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-[#1F2937] bg-[#111827] flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-500 to-emerald-500 flex items-center justify-center text-gray-950 font-bold shadow-lg shadow-teal-500/20">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              MoneyLens Agentic Assistant
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 font-semibold border border-teal-500/30">
                SQL Grounded
              </span>
            </h2>
            <p className="text-xs text-gray-400">
              Deterministic calculations via read-only tools • Zero hallucinations
            </p>
          </div>
        </div>
      </div>

      {/* Suggested Prompt Chips */}
      <div className="px-6 py-3 bg-[#0E1524] border-b border-[#1F2937] flex items-center gap-2 overflow-x-auto">
        <span className="text-xs text-gray-500 font-medium shrink-0">Try asking:</span>
        {sampleQuestions.map((q, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(q)}
            className="text-xs px-3 py-1.5 rounded-full bg-[#111827] hover:bg-teal-500/10 hover:border-teal-500/30 text-gray-300 hover:text-teal-300 border border-[#1F2937] whitespace-nowrap transition"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-2xl rounded-2xl p-5 text-sm ${
                msg.sender === 'user'
                  ? 'bg-teal-500 text-gray-950 font-medium rounded-br-none shadow-lg shadow-teal-500/10'
                  : 'bg-[#111827] border border-[#1F2937] text-gray-200 rounded-bl-none shadow-sm space-y-4'
              }`}
            >
              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

              {/* Render Evidence / Structured Cards if Assistant returned data */}
              {msg.responsePayload && (
                <div className="pt-2 border-t border-[#1F2937] space-y-3">
                  {/* Warnings */}
                  {msg.responsePayload.data_warnings.length > 0 && (
                    <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl text-yellow-300 text-xs flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>{msg.responsePayload.data_warnings.join(', ')}</span>
                    </div>
                  )}

                  {/* Summary Card */}
                  {msg.responsePayload.visualization?.type === 'summary_cards' && (
                    <div className="grid grid-cols-3 gap-2 text-center p-3 bg-[#0E1524] rounded-xl border border-[#1F2937]">
                      <div>
                        <div className="text-[10px] uppercase text-gray-400 font-semibold">Income</div>
                        <div className="text-xs font-mono font-bold text-emerald-400 mt-1">
                          {formatINR(msg.responsePayload.visualization.data.income)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase text-gray-400 font-semibold">Expense</div>
                        <div className="text-xs font-mono font-bold text-red-400 mt-1">
                          {formatINR(msg.responsePayload.visualization.data.expenses)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase text-gray-400 font-semibold">Net Cash</div>
                        <div className="text-xs font-mono font-bold text-teal-400 mt-1">
                          {formatINR(msg.responsePayload.visualization.data.net_cash_flow)}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Category Breakdown List */}
                  {msg.responsePayload.visualization?.type === 'category_pie' && (
                    <div className="space-y-1.5 p-3 bg-[#0E1524] rounded-xl border border-[#1F2937]">
                      <div className="text-xs font-semibold text-gray-300 mb-2">Category Breakdown:</div>
                      {msg.responsePayload.visualization.data.map((cat: any, i: number) => (
                        <div key={i} className="flex justify-between text-xs font-mono">
                          <span className="text-gray-400">{cat.category}</span>
                          <span className="text-teal-300 font-semibold">{formatINR(cat.amount)} ({cat.percentage}%)</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Transaction Search Table */}
                  {msg.responsePayload.visualization?.type === 'transaction_table' && (
                    <div className="p-3 bg-[#0E1524] rounded-xl border border-[#1F2937] space-y-2">
                      <div className="text-xs font-semibold text-gray-300">Supporting Transactions:</div>
                      <div className="space-y-1.5 max-h-48 overflow-y-auto">
                        {msg.responsePayload.visualization.data.map((tx: any, i: number) => (
                          <div key={i} className="flex justify-between items-center text-xs p-2 bg-[#111827] rounded-lg">
                            <div>
                              <div className="font-semibold text-white">{tx.description}</div>
                              <div className="text-[10px] text-gray-500 font-mono">{tx.date} • {tx.payment_method}</div>
                            </div>
                            <div className="font-mono text-red-400 font-semibold">
                              {parseFloat(tx.debit) > 0 ? `- ${formatINR(tx.debit)}` : `+ ${formatINR(tx.credit)}`}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl rounded-bl-none p-4 flex items-center space-x-3 text-xs text-gray-400">
              <Sparkles className="w-4 h-4 text-teal-400 animate-spin" />
              <span>Querying authorized SQL tools and verifying evidence...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Box */}
      <div className="p-4 bg-[#111827] border-t border-[#1F2937]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center space-x-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your bank statements or financial activity..."
            className="flex-1 px-4 py-3 bg-[#0E1524] border border-[#1F2937] rounded-xl text-white placeholder-gray-500 text-sm focus:outline-none focus:border-teal-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="px-5 py-3 bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-gray-950 font-semibold rounded-xl text-sm transition flex items-center space-x-2 shadow-lg shadow-teal-500/20"
          >
            <span>Ask</span>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
