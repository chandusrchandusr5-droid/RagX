import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Documents from './pages/Documents';
import DataQuality from './pages/DataQuality';
import RagChat from './pages/RagChat';
import AnswerEvaluator from './pages/AnswerEvaluator';
import Analytics from './pages/Analytics';
import AdminPortal from './pages/AdminPortal';
import NovaWidget from './components/NovaWidget';
import ThreeRAGXIntro from './components/ThreeRAGXIntro';
import AuthModal from './components/AuthModal';
import SettingsModal from './components/SettingsModal';
import { fetchCurrentUser, logoutUser } from './services/api';

export default function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('ragx_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [showIntro, setShowIntro] = useState(() => {
    return !sessionStorage.getItem('ragx_intro_seen');
  });

  const [activeTab, setActiveTab] = useState('documents');
  const [showSettings, setShowSettings] = useState(false);

  // Validate session token on mount if user is saved
  useEffect(() => {
    const token = localStorage.getItem('ragx_token');
    if (token) {
      fetchCurrentUser()
        .then((data) => {
          if (data && data.user) {
            setUser(data.user);
            localStorage.setItem('ragx_user', JSON.stringify(data.user));
          }
        })
        .catch(() => {
          // Token expired or invalid
          localStorage.removeItem('ragx_token');
          localStorage.removeItem('ragx_user');
          setUser(null);
        });
    } else {
      setUser(null);
    }
  }, []);

  const handleLogout = async () => {
    await logoutUser();
    localStorage.removeItem('ragx_token');
    localStorage.removeItem('ragx_user');
    setUser(null);
    setShowSettings(false);
    setActiveTab('documents');
  };

  const handleCompleteIntro = () => {
    sessionStorage.setItem('ragx_intro_seen', 'true');
    setShowIntro(false);
  };

  const handleReplayIntro = () => {
    setShowIntro(true);
  };

  // 1. Render 3D RAGX Intro Animation
  if (showIntro) {
    return <ThreeRAGXIntro onComplete={handleCompleteIntro} />;
  }

  // 2. Render Login / Register Modal
  if (!user) {
    return <AuthModal onLoginSuccess={(userData) => setUser(userData)} />;
  }

  // 3. Render Main Authenticated Application
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onOpenSettings={() => setShowSettings(true)}
        onReplayIntro={handleReplayIntro}
        onLogout={handleLogout}
      />
      
      <main className="flex-1">
        {activeTab === 'documents' && <Documents />}
        {activeTab === 'data-quality' && <DataQuality onNavigateToDocs={() => setActiveTab('documents')} />}
        {activeTab === 'rag-chat' && <RagChat />}
        {activeTab === 'evaluator' && <AnswerEvaluator />}
        {activeTab === 'analytics' && <Analytics />}
        {activeTab === 'admin' && user?.role === 'ADMIN' && <AdminPortal />}
      </main>

      <NovaWidget activeTab={activeTab} />

      {showSettings && (
        <SettingsModal
          user={user}
          onClose={() => setShowSettings(false)}
          onUserUpdated={(updatedUser) => {
            setUser(updatedUser);
            localStorage.setItem('ragx_user', JSON.stringify(updatedUser));
          }}
          onLogout={handleLogout}
        />
      )}

      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-600">
        RAGX Platform — Data Quality &amp; Hallucination Detection for RAG Systems
      </footer>
    </div>
  );
}
