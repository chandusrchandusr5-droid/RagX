import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Documents from './pages/Documents';
import DataQuality from './pages/DataQuality';
import RagChat from './pages/RagChat';
import AnswerEvaluator from './pages/AnswerEvaluator';
import Analytics from './pages/Analytics';
import NovaWidget from './components/NovaWidget';

export default function App() {
  const [activeTab, setActiveTab] = useState('documents');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="flex-1">
        {activeTab === 'documents' && <Documents />}
        {activeTab === 'data-quality' && <DataQuality onNavigateToDocs={() => setActiveTab('documents')} />}
        {activeTab === 'rag-chat' && <RagChat />}
        {activeTab === 'evaluator' && <AnswerEvaluator />}
        {activeTab === 'analytics' && <Analytics />}
      </main>

      <NovaWidget activeTab={activeTab} />





      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-600">
        RAGX Platform — Data Quality &amp; Hallucination Detection for RAG Systems
      </footer>

    </div>
  );
}


