import React, { useState, useEffect } from 'react';
import { 
  BarChart2, 
  RefreshCw, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle, 
  Layers, 
  Search,
  ChevronDown,
  ChevronUp,
  Brain,
  FileText
} from 'lucide-react';
import { fetchEvaluationAnalytics } from '../services/api';

export default function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedEvalId, setExpandedEvalId] = useState(null);

  const loadAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEvaluationAnalytics();
      setAnalytics(data);
    } catch (err) {
      console.error(err);
      setError('Failed to load evaluation analytics from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center space-y-4">
        <RefreshCw className="w-10 h-10 text-indigo-400 animate-spin mx-auto" />
        <p className="text-sm font-semibold text-slate-300">Loading RAGX Analytics &amp; Historical Metrics...</p>

      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center space-y-4">
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
          {error}
        </div>
        <button
          onClick={loadAnalytics}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium border border-slate-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  const totalEvaluations = analytics?.total_evaluations || 0;
  const avgScore = analytics?.average_reliability_score || 0.0;
  const relDist = analytics?.reliability_status_distribution || {};
  const failDist = analytics?.failure_category_distribution || {};
  const recentEvals = analytics?.recent_evaluations || [];

  const getStatusBadge = (status) => {
    switch (status) {
      case 'HIGHLY_RELIABLE':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Highly Reliable</span>;
      case 'PARTIALLY_RELIABLE':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Partially Reliable</span>;
      case 'UNRELIABLE':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">Unreliable</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">Not Evaluable</span>;
    }
  };

  const getFailureBadge = (cat) => {
    switch (cat) {
      case 'WELL_GROUNDED':
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">Well Grounded</span>;
      case 'GENERATION_FAILURE':
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20">Generation Failure / Hallucination</span>;
      case 'RETRIEVAL_FAILURE':
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">Retrieval Failure</span>;
      case 'KNOWLEDGE_CONFLICT':
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20">KB Conflict</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700">Evidence Insufficiency</span>;
    }
  };

  const getHallucinationBadge = (risk) => {
    switch (risk) {
      case 'LOW':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Low Risk</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Medium Risk</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">High Risk</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">Unknown Risk</span>;
    }
  };


  return (
    <div className="max-w-[1700px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart2 className="w-7 h-7 text-indigo-400" />
            RAG Evaluation Analytics &amp; History
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time aggregate reliability scores, failure category distributions, and historical evaluation traceability.
          </p>
        </div>
        <button
          onClick={loadAnalytics}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Analytics
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Total Runs */}
        <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Evaluations</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">{totalEvaluations}</div>
          <p className="text-[11px] text-slate-500">Persisted evaluation runs on disk</p>
        </div>

        {/* Card 2: Average Answer Reliability Score */}
        <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Avg Reliability (S_Ans)</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">{avgScore}%</div>
          <p className="text-[11px] text-slate-500">Mean composite score across evaluated runs</p>
        </div>

        {/* Card 3: Well-Grounded Answers */}
        <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Well Grounded</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">{failDist["WELL_GROUNDED"] || 0}</div>
          <p className="text-[11px] text-slate-500">Answers fully backed by evidence</p>
        </div>

        {/* Card 4: Hallucination & Failures */}
        <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Failures Detected</span>
            <XCircle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-3xl font-extrabold text-rose-400">
            {(failDist["GENERATION_FAILURE"] || 0) + (failDist["RETRIEVAL_FAILURE"] || 0) + (failDist["KNOWLEDGE_CONFLICT"] || 0)}
          </div>
          <p className="text-[11px] text-slate-500">Generation, retrieval, &amp; conflict failures</p>
        </div>
      </div>

      {/* Failure Category Distribution Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Box 1: Reliability Status Breakdown */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-indigo-400" /> Reliability Status Breakdown
          </h3>
          <div className="space-y-3">
            {[
              { label: 'Highly Reliable (85-100%)', count: relDist["HIGHLY_RELIABLE"] || 0, color: 'bg-emerald-500' },
              { label: 'Partially Reliable (65-84%)', count: relDist["PARTIALLY_RELIABLE"] || 0, color: 'bg-amber-500' },
              { label: 'Unreliable / Hallucination (<65%)', count: relDist["UNRELIABLE"] || 0, color: 'bg-rose-500' },
              { label: 'Not Evaluable (No Evidence)', count: relDist["NOT_EVALUABLE"] || 0, color: 'bg-slate-600' }
            ].map((item, idx) => {
              const pct = totalEvaluations > 0 ? Math.round((item.count / totalEvaluations) * 100) : 0;
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs font-medium text-slate-300">
                    <span>{item.label}</span>
                    <span>{item.count} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                    <div className={`h-full ${item.color} transition-all duration-500`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Box 2: Failure Category Distribution */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-400" /> Failure Category Attribution
          </h3>
          <div className="space-y-3">
            {[
              { label: 'Well Grounded', count: failDist["WELL_GROUNDED"] || 0, color: 'bg-emerald-500' },
              { label: 'Generation Failure (Hallucination)', count: failDist["GENERATION_FAILURE"] || 0, color: 'bg-rose-500' },
              { label: 'Retrieval Failure (Full-KB Oracle Found)', count: failDist["RETRIEVAL_FAILURE"] || 0, color: 'bg-amber-500' },
              { label: 'Knowledge Base Conflict', count: failDist["KNOWLEDGE_CONFLICT"] || 0, color: 'bg-purple-500' },
              { label: 'Evidence Insufficiency', count: failDist["EVIDENCE_INSUFFICIENCY"] || 0, color: 'bg-slate-600' }
            ].map((item, idx) => {
              const pct = totalEvaluations > 0 ? Math.round((item.count / totalEvaluations) * 100) : 0;
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs font-medium text-slate-300">
                    <span>{item.label}</span>
                    <span>{item.count} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                    <div className={`h-full ${item.color} transition-all duration-500`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Recent Evaluation Runs Table */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" /> Recent Evaluation Run Logs
          </h3>
          <span className="text-xs text-slate-400">Showing latest {recentEvals.length} runs</span>
        </div>

        {recentEvals.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No evaluation runs logged yet. Execute questions in RAG Chat or Answer Evaluator to populate analytics.
          </div>
        ) : (
          <div className="space-y-3">
            {recentEvals.map((item) => {
              const isExpanded = expandedEvalId === item.evaluation_id;
              return (
                <div key={item.evaluation_id} className="border border-slate-800 rounded-xl bg-slate-900/50 overflow-hidden">
                  <div 
                    onClick={() => setExpandedEvalId(isExpanded ? null : item.evaluation_id)}
                    className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer hover:bg-slate-800/40 transition"
                  >
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {item.evaluation_id}
                        </span>
                        <span className="text-[11px] text-slate-500">{item.timestamp?.replace('T', ' ')?.slice(0, 19)}</span>
                      </div>
                      <p className="text-xs font-semibold text-slate-200">{item.query}</p>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div className="text-right">
                        <div className="text-xs font-bold text-white">{item.overall_reliability_score}%</div>
                        <div className="text-[10px] text-slate-400">{item.supported_claims}/{item.total_claims} claims supported</div>
                      </div>
                      <div>{getStatusBadge(item.reliability_status)}</div>
                      <div>{getHallucinationBadge(item.hallucination_risk)}</div>
                      <div>{getFailureBadge(item.failure_category)}</div>

                      {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </div>
                  </div>

                  {/* Expanded Traceability Detail */}
                  {isExpanded && (
                    <div className="p-4 bg-slate-950/80 border-t border-slate-800 space-y-3 text-xs">
                      <div>
                        <span className="font-semibold text-slate-400 uppercase text-[10px]">Generated Answer:</span>
                        <p className="text-slate-300 mt-0.5">{item.generated_answer}</p>
                      </div>

                      {item.claim_analysis && item.claim_analysis.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-slate-900">
                          <span className="font-semibold text-slate-400 uppercase text-[10px]">5-Tuple Claim Traceability:</span>
                          <div className="space-y-2">
                            {item.claim_analysis.map((claim, cIdx) => (
                              <div key={cIdx} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1 text-slate-300">
                                <div className="flex justify-between items-center text-[11px]">
                                  <span className="font-medium text-indigo-300">{claim.claim_id}: {claim.claim_text}</span>
                                  <span className="font-bold text-slate-400">{claim.support_status}</span>
                                </div>
                                {claim.matched_evidence && (
                                  <p className="text-[11px] text-slate-400 font-mono">
                                    Evidence: {claim.matched_evidence.source_file} (Page {claim.matched_evidence.page_number}, Chunk {claim.matched_evidence.chunk_id}) | Sim: {claim.matched_evidence.similarity_score}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
