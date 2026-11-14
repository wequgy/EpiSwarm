import React, { useState } from 'react';
import { Bot, Send, Sparkles, User, Shield, Info } from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'user' | 'advisor';
  text: string;
  timestamp: string;
  recommendations?: Array<{ policy: string; impact: string; confidence: string }>;
}

export const AdvisorChat: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'm1',
      sender: 'advisor',
      text: 'Hello. I am the EpiSwarm Autonomous Policy Advisor. I analyze transmission dynamics, bed capacity saturation, and equity tradeoffs to recommend optimal non-pharmaceutical interventions.',
      timestamp: 'Just now',
      recommendations: [
        {
          policy: 'Targeted Workplace Hybrid Schedule (50% reduction)',
          impact: 'Reduces R_eff by 0.38 with low economic disruption score (cost: 2.1 units)',
          confidence: 'High (30 paired seeds)',
        },
        {
          policy: 'Early Hospital ICU Surge Trigger (at 75% bed threshold)',
          impact: 'Averts estimated 18 overflow deaths in acute waves',
          confidence: 'Moderate (Model assumption Class C)',
        },
      ],
    },
  ]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      sender: 'user',
      text: input,
      timestamp: 'Just now',
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');

    // Synthetic advisor response acknowledging question
    setTimeout(() => {
      const advMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        sender: 'advisor',
        text: `Based on current regional topology and empirical benchmark cards: executing targeted interventions in high-density commute corridors (e.g. Central Business Core A01) yields 3.2x higher attack rate reduction per disrupted agent-day compared to uniform region-wide curfews.`,
        timestamp: 'Just now',
        recommendations: [
          {
            policy: 'Prioritized Transit Hub Screening',
            impact: 'Delays inter-borough spatial wavefront transmission by 6.2 days',
            confidence: 'Verified on synthetic 6-borough topology',
          },
        ],
      };
      setMessages((prev) => [...prev, advMsg]);
    }, 600);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 flex flex-col h-[calc(100vh-140px)]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Bot className="w-6 h-6 text-blue-600" />
            Epidemic Policy Advisory Agent
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Autonomous decision engine providing causal what-if explanations and resource optimization advice.
          </p>
        </div>
      </div>

      {/* Chat Thread */}
      <div className="flex-1 overflow-y-auto bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex gap-3 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {m.sender === 'advisor' && (
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div className={`max-w-xl space-y-3 ${
              m.sender === 'user'
                ? 'bg-blue-600 text-white p-4 rounded-2xl rounded-tr-none text-sm'
                : 'bg-slate-50 border border-slate-200 p-4 rounded-2xl rounded-tl-none text-slate-800 text-sm'
            }`}>
              <p className="leading-relaxed">{m.text}</p>

              {m.recommendations && m.recommendations.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">
                    Structured Policy Recommendations
                  </span>
                  {m.recommendations.map((rec, i) => (
                    <div key={i} className="bg-white p-3 rounded-lg border border-slate-200 text-xs space-y-1">
                      <div className="font-bold text-slate-900">{rec.policy}</div>
                      <div className="text-slate-600">{rec.impact}</div>
                      <div className="text-[10px] text-blue-600 font-mono">Confidence: {rec.confidence}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {m.sender === 'user' && (
              <div className="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} className="bg-white rounded-xl border border-slate-200 p-3 shadow-sm flex items-center gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask policy advisor (e.g. 'How can we prevent ICU bed overflow in Wave 2?')..."
          className="flex-1 bg-transparent border-0 px-3 py-1.5 text-sm focus:outline-none"
        />
        <button
          type="submit"
          className="p-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition-colors shadow-sm"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
