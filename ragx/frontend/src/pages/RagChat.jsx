import React, { useState } from 'react';
import { Send, MessageSquare, BookOpen, FileText, Sparkles, ChevronDown, ChevronUp, AlertCircle, ShieldCheck, CheckCircle2, XCircle, AlertTriangle, Layers } from 'lucide-react';
import { queryAndEvaluateRag } from '../services/api';

export default function RagChat() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userQ = question.trim();
    setQuestion('');
    setError(null);
    setLoading(true);

    try {
      const response = await queryAndEvaluateRag(userQ);
      const newEntry = {
        id: Date.now(),
        question: userQ,
        answer: response.answer,
        evidence: response.retrieved_evidence || [],
        evalReport: response.evaluation_report,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        showEvidence: false,
        showEval: true
      };
      setChatHistory((prev) => [newEntry, ...prev]);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to generate RAG response.');
    } finally {
      setLoading(false);
    }
  };

  const toggleEvidence = (id) => {
    setChatHistory((prev) =>
      prev.map((item) => (item.id === id ? { ...item, showEvidence: !item.showEvidence } : item))
    );
  };

  const toggleEval = (id) => {
    setChatHistory((prev) =>
      prev.map((item) => (item.id === id ? { ...item, showEval: !item.showEval } : item))
    );
  };

  const getReliabilityBadge = (evalReport) => {
    if (!evalReport) return null;

    const status = evalReport.reliability_status;
    const score = evalReport.overall_reliability_score;
    const category = evalReport.failure_category;

    if (evalReport.evaluation_status === 'NOT_EVALUABLE') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1.5">
          NOT EVALUABLE (Insufficient Evidence)
        </span>
      );
    }

    if (status === 'HIGHLY_RELIABLE') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5" /> Reliability: {score}% ({category})
        </span>
      );
    } else if (status === 'PARTIALLY_RELIABLE') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5" /> Reliability: {score}% ({category})
        </span>
      );
    } else {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1.5">
          <XCircle className="w-3.5 h-3.5" /> Unreliable / Hallucination ({score}%)
        </span>
      );
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header Banner */}
      <div className="border-b border-slate-800 pb-5">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <MessageSquare className="w-7 h-7 text-indigo-400" />
          RAG Chat &amp; Evaluation Workspace
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Query the ChromaDB vector database with instant claim-level reliability evaluation and hallucination detection.
        </p>
      </div>

      {/* Query Input Box */}
      <form onSubmit={handleSubmit} className="glass-card p-4 rounded-2xl border border-indigo-500/20 shadow-xl space-y-3">
        <div className="relative flex items-center">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question (e.g., 'What is the minimum attendance requirement?')..."
            disabled={loading}
            className="w-full bg-slate-900/80 text-white placeholder-slate-500 text-sm rounded-xl pl-4 pr-12 py-3.5 border border-slate-700/80 focus:border-indigo-500 focus:outline-none transition"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="absolute right-2 p-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition shadow-md shadow-indigo-600/30"
          >
            {loading ? (
              <Sparkles className="w-4 h-4 animate-spin text-indigo-200" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{error}</span>
          </div>
        )}
      </form>

      {/* Chat History & Evaluated Cards */}
      <div className="space-y-6">
        {chatHistory.length === 0 && !loading && (
          <div className="glass-card p-12 rounded-2xl text-center space-y-3">
            <BookOpen className="w-12 h-12 text-slate-600 mx-auto" />
            <h3 className="text-base font-semibold text-slate-300">No RAG Queries Yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Type a question above to retrieve context chunks, synthesize RAG answers, and evaluate answer reliability.
            </p>
          </div>
        )}

        {chatHistory.map((item) => (
          <div key={item.id} className="glass-card rounded-2xl p-6 space-y-4 border border-slate-800">
            {/* User Question */}
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs font-bold">
                Q
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">{item.question}</h3>
                  <span className="text-[10px] text-slate-500">{item.timestamp}</span>
                </div>
              </div>
            </div>

            {/* RAG Generated Answer */}
            <div className="bg-slate-950/60 p-4 rounded-xl border border-indigo-500/20 space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center space-x-2 text-xs font-semibold text-indigo-400">
                  <Sparkles className="w-4 h-4" />
                  <span>RAG Response</span>
                </div>
                {getReliabilityBadge(item.evalReport)}
              </div>
              <p className="text-sm text-slate-200 leading-relaxed pl-6">
                {item.answer}
              </p>
            </div>

            {/* Collapsible Answer Reliability Evaluation Drawer */}
            {item.evalReport && (
              <div>
                <button
                  onClick={() => toggleEval(item.id)}
                  className="flex items-center justify-between w-full py-2 px-3 rounded-lg bg-indigo-950/40 hover:bg-indigo-900/40 text-xs font-medium text-indigo-300 transition border border-indigo-500/30"
                >
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    <span>RAGX Answer Reliability Evaluation Details</span>
                  </div>
                  {item.showEval ? (
                    <ChevronUp className="w-4 h-4 text-indigo-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-indigo-400" />
                  )}
                </button>

                {item.showEval && (
                  <div className="mt-3 bg-slate-900/90 p-4 rounded-xl border border-slate-800 space-y-3 text-xs">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-center">
                      <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-[10px] block">Claim Support Score</span>
                        <span className="text-sm font-bold text-indigo-400">{item.evalReport.scoring_breakdown?.sub_scores?.claim_support_score}%</span>
                      </div>
                      <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-[10px] block">Citation Traceability</span>
                        <span className="text-sm font-bold text-teal-400">{item.evalReport.scoring_breakdown?.sub_scores?.citation_coverage_score}%</span>
                      </div>
                      <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-[10px] block">Retrieval Similarity</span>
                        <span className="text-sm font-bold text-purple-400">{item.evalReport.scoring_breakdown?.sub_scores?.retrieval_similarity_score}%</span>
                      </div>
                    </div>

                    {/* Claims Breakdown */}
                    <div className="space-y-2 pt-2">
                      <span className="font-semibold text-slate-300 block">Extracted Claims &amp; Evidence Matching:</span>
                      {item.evalReport.claim_analysis?.map((c) => (
                        <div key={c.claim_id} className="p-2.5 bg-slate-950/80 rounded-lg border border-slate-800 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[11px] font-bold text-indigo-400">{c.claim_id}: {c.claim_text}</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              c.support_status === 'SUPPORTED' ? 'bg-emerald-500/10 text-emerald-400' :
                              c.support_status === 'CONTRADICTED' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400'
                            }`}>{c.support_status}</span>
                          </div>
                          <p className="text-[11px] text-slate-400">{c.disparity_detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Retrieved Evidence Citations */}
            <div>
              <button
                onClick={() => toggleEvidence(item.id)}
                className="flex items-center justify-between w-full py-2 px-3 rounded-lg bg-slate-900/60 hover:bg-slate-800/60 text-xs font-medium text-slate-300 transition border border-slate-800"
              >
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-indigo-400" />
                  <span>Retrieved Source Evidence ({item.evidence.length} Chunks)</span>
                </div>
                {item.showEvidence ? (
                  <ChevronUp className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                )}
              </button>

              {item.showEvidence && (
                <div className="mt-3 space-y-3 pl-2">
                  {item.evidence.length === 0 ? (
                    <p className="text-xs text-slate-500 italic p-3">No matching vector chunks retrieved.</p>
                  ) : (
                    item.evidence.map((chunk, cIdx) => (
                      <div key={cIdx} className="bg-slate-900/90 p-3.5 rounded-xl border border-slate-800 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center space-x-2 text-indigo-300 font-medium">
                            <FileText className="w-3.5 h-3.5" />
                            <span>{chunk.document_name}</span>
                            <span className="text-slate-500">•</span>
                            <span className="text-teal-400 font-semibold">Page {chunk.page_number}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded-md border border-slate-700">
                            Similarity: {(chunk.similarity_score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 bg-slate-950/80 p-2.5 rounded-lg font-mono leading-relaxed">
                          "{chunk.text}"
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
