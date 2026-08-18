import React from 'react';
import { 
  FileText, 
  MessageSquare, 
  ShieldCheck, 
  Sparkles, 
  BarChart2, 
  Layers,
  Shield,
  Settings,
  LogOut,
  Zap
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, user, onOpenSettings, onReplayIntro, onLogout }) {
  const navItems = [
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'data-quality', label: 'Data Quality', icon: Layers },
    { id: 'rag-chat', label: 'RAG Chat', icon: MessageSquare },
    { id: 'evaluator', label: 'RAGX Evaluator', icon: ShieldCheck },
    { id: 'analytics', label: 'Analytics', icon: BarChart2 },
  ];

  if (user?.role === 'ADMIN') {
    navItems.push({ id: 'admin', label: 'Admin Portal', icon: Shield, isAdmin: true });
  }

  return (
    <header className="sticky top-0 z-40 glass-panel border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-[1700px] w-full mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('documents')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 p-0.5 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-xl tracking-wider text-white">RAG<span className="text-cyan-400">X</span></span>
                <span className="text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
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

              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                    isActive
                      ? item.isAdmin 
                        ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40 shadow-sm'
                        : 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                      : item.isAdmin
                        ? 'text-purple-300 hover:bg-purple-950/40'
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? (item.isAdmin ? 'text-purple-400' : 'text-cyan-400') : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* User Profile & Actions */}
          <div className="flex items-center space-x-2">
            {/* Replay Intro */}
            <button
              onClick={onReplayIntro}
              title="Replay 3D Intro Animation"
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <Zap className="w-4 h-4" />
            </button>

            {/* User Badge */}
            <div className="hidden sm:flex items-center space-x-2 bg-slate-900 border border-slate-800/80 px-3 py-1.5 rounded-xl">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-semibold text-slate-200">{user?.full_name}</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md uppercase ${
                user?.role === 'ADMIN' ? 'bg-purple-950 text-purple-300 border border-purple-800' : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
              }`}>
                {user?.role}
              </span>
            </div>

            {/* Settings Button */}
            <button
              onClick={onOpenSettings}
              title="Account Settings"
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <Settings className="w-4 h-4" />
            </button>

            {/* Logout Button */}
            <button
              onClick={onLogout}
              title="Sign Out"
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
