import React from 'react';
import { 
  FileText, 
  MessageSquare, 
  ShieldCheck, 
  Sparkles, 
  BarChart2, 
  Layers,
  Lock
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'data-quality', label: 'Data Quality', icon: Layers },
    { id: 'rag-chat', label: 'RAG Chat', icon: MessageSquare },
    { id: 'evaluator', label: 'RAGX Evaluator', icon: ShieldCheck },
    { id: 'analytics', label: 'Analytics', icon: BarChart2 },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-[1700px] w-full mx-auto px-4 sm:px-6 lg:px-8">

        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-teal-400 p-0.5 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-indigo-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-xl tracking-wider text-white">RAG<span className="text-indigo-400">X</span></span>
                <span className="text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  Answer Reliability &amp; Hallucination Evaluator
                </span>
              </div>


              <p className="text-xs text-slate-400 hidden md:block">
                Data Quality &amp; Hallucination Detection for RAG Systems
              </p>
            </div>

          </div>


          {/* Navigation Links */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              const isDisabled = item.disabled;

              return (
                <button
                  key={item.id}
                  onClick={() => !isDisabled && setActiveTab(item.id)}
                  disabled={isDisabled}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                      : isDisabled
                      ? 'text-slate-600 cursor-not-allowed opacity-60'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                  {isDisabled && (
                    <span className="flex items-center text-[10px] text-slate-500 bg-slate-800/80 px-1.5 py-0.5 rounded">
                      <Lock className="w-2.5 h-2.5 mr-0.5" />
                      {item.phase}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
