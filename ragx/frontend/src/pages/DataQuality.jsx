import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  RefreshCw, 
  Layers, 
  FileText, 
  AlertTriangle, 
  CheckCircle2, 
  Info, 
  HelpCircle, 
  Sliders,
  Database
} from 'lucide-react';
import { fetchQualityAudit } from '../services/api';

export default function DataQuality({ onNavigateToDocs }) {
  const [auditReport, setAuditReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterCategory, setFilterCategory] = useState('ALL'); // ALL, CONFIRMED, SUSPECTED

  const loadAuditReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchQualityAudit();
      setAuditReport(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch Data Quality Audit report.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditReport();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center space-y-4">
        <RefreshCw className="w-10 h-10 text-indigo-400 animate-spin mx-auto" />
        <p className="text-sm font-semibold text-slate-300">Auditing Knowledge Base Reliability & Data Quality...</p>
        <p className="text-xs text-slate-500">Scanning page extractions, file hashes, vector redundancy, and topic consistency.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12 text-center space-y-4">
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 max-w-lg mx-auto text-sm">
          {error}
        </div>
        <button
          onClick={loadAuditReport}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium border border-slate-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  // Handle NO_DATA state safely
  const isNoData = auditReport?.user_facing_status === 'NO_DATA' || auditReport?.summary?.total_documents === 0;

  const score = auditReport?.composite_reliability_score ?? 100;
  const status = auditReport?.user_facing_status ?? 'NOT_EVALUATED';
  const breakdown = auditReport?.scoring_breakdown;
  const subScores = breakdown?.sub_scores || {};
  const weights = breakdown?.configured_weights || {};
  const issues = auditReport?.issues || [];

  const filteredIssues = issues.filter((item) => {
    if (filterCategory === 'CONFIRMED') return item.issue_status === 'DETECTED_ISSUE';
    if (filterCategory === 'SUSPECTED') return item.issue_status === 'SUSPECTED_SIGNAL';
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Layers className="w-7 h-7 text-indigo-400" />
            Knowledge Base Data Quality Audit
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Automated analysis of document extractions, file redundancies, vector chunk overlaps, and candidate topic conflicts.
          </p>
        </div>
        <button
          onClick={loadAuditReport}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Re-Run Audit
        </button>
      </div>

      {/* NO DATA STATE */}
      {isNoData ? (
        <div className="glass-card p-12 rounded-3xl text-center space-y-5 border border-indigo-500/20 max-w-2xl mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
            <Database className="w-8 h-8" />
          </div>
          <div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700">
              STATE: NO_DATA / NOT_EVALUATED
            </span>
            <h2 className="text-xl font-bold text-white mt-3">Knowledge Base is Empty</h2>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              No documents have been uploaded to ChromaDB yet. Upload your PDF files in the Documents workspace to calculate your Knowledge Base Reliability Score.
            </p>
          </div>
          {onNavigateToDocs && (
            <button
              onClick={onNavigateToDocs}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition inline-flex items-center gap-2"
            >
              <FileText className="w-4 h-4" />
              Go to Documents Workspace
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Top Score Banner & Breakdown Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Main Reliability Score Gauge */}
            <div className="lg:col-span-1 glass-card p-6 rounded-2xl border border-indigo-500/30 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                  <span>Knowledge Reliability Score</span>
                  <Sliders className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="mt-4 text-center">
                  <span className="text-5xl font-extrabold text-white tracking-tight">{score}%</span>
                  <div className="mt-2">
                    <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${
                      status === 'GOOD'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : status === 'MODERATE'
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    }`}>
                      STATUS: {status}
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 border-t border-slate-800/80 pt-3 text-center">
                Configured Weights: {weights.extraction_weight * 100}% Ext | {weights.diversity_weight * 100}% Div | {weights.consistency_weight * 100}% Cons
              </div>
            </div>

            {/* Sub-Score Breakdown Cards */}
            <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Sub Score 1: Extraction Integrity */}
              <div className="glass-card p-5 rounded-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400">Extraction Health</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-white">{subScores.extraction_integrity_score}%</div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-emerald-400 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${subScores.extraction_integrity_score}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400">
                  {breakdown?.raw_measurements?.unextractable_pages || 0} un-extractable pages out of {breakdown?.raw_measurements?.total_pages || 0} total pages.
                </p>
              </div>

              {/* Sub Score 2: Vector Diversity */}
              <div className="glass-card p-5 rounded-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400">Vector Diversity</span>
                  <Layers className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="text-2xl font-bold text-white">{subScores.vector_diversity_score}%</div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-indigo-400 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${subScores.vector_diversity_score}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400">
                  {breakdown?.raw_measurements?.redundant_chunks_count || 0} redundant chunks out of {breakdown?.raw_measurements?.total_chunks || 0} total chunks.
                </p>
              </div>

              {/* Sub Score 3: Consistency Index */}
              <div className="glass-card p-5 rounded-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400">Consistency Index</span>
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-2xl font-bold text-white">{subScores.consistency_index}%</div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-amber-400 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${subScores.consistency_index}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400">
                  {breakdown?.raw_measurements?.conflicting_topics_count || 0} candidate topic conflicts across {breakdown?.raw_measurements?.total_topics_evaluated || 0} evaluated topics.
                </p>
              </div>
            </div>
          </div>

          {/* Issue Audit Log Table */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>Detailed Audit Logs ({issues.length} Issues)</span>
              </h2>

              {/* Category Filter Tabs */}
              <div className="flex items-center space-x-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-xs">
                <button
                  onClick={() => setFilterCategory('ALL')}
                  className={`px-3 py-1.5 rounded-lg font-medium transition ${
                    filterCategory === 'ALL' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  All ({issues.length})
                </button>
                <button
                  onClick={() => setFilterCategory('CONFIRMED')}
                  className={`px-3 py-1.5 rounded-lg font-medium transition ${
                    filterCategory === 'CONFIRMED' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Confirmed ({auditReport?.summary?.confirmed_issues || 0})
                </button>
                <button
                  onClick={() => setFilterCategory('SUSPECTED')}
                  className={`px-3 py-1.5 rounded-lg font-medium transition ${
                    filterCategory === 'SUSPECTED' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Suspected Signals ({auditReport?.summary?.suspected_signals || 0})
                </button>
              </div>
            </div>

            {filteredIssues.length === 0 ? (
              <div className="glass-card p-8 rounded-2xl text-center space-y-2">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                <h3 className="text-base font-semibold text-slate-200">No Quality Issues Detected in this Category</h3>
                <p className="text-xs text-slate-500">Your uploaded documents pass all data quality and reliability checks in this view.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredIssues.map((item) => (
                  <div key={item.issue_id} className="glass-card p-6 rounded-2xl space-y-4 border border-slate-800">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                      <div className="flex items-center space-x-3">
                        <span className={`px-2.5 py-0.5 rounded-md text-[11px] font-bold ${
                          item.severity === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : item.severity === 'WARNING'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                        }`}>
                          {item.severity}
                        </span>
                        <h3 className="text-sm font-semibold text-white">{item.title}</h3>
                      </div>
                      <div className="flex items-center space-x-2 text-xs">
                        <span className="text-slate-500">{item.issue_id}</span>
                        <span className="text-slate-700">•</span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono border border-slate-700">
                          {item.issue_status} (Conf: {(item.confidence * 100).toFixed(0)}%)
                        </span>
                      </div>
                    </div>

                    {/* File Location Info */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-indigo-300 font-medium">
                      <div className="flex items-center space-x-1.5">
                        <FileText className="w-4 h-4 text-indigo-400" />
                        <span>{item.source_file}</span>
                        <span className="text-slate-500">(Page {item.page_number})</span>
                      </div>
                      {item.related_file && (
                        <div className="flex items-center space-x-1.5 text-amber-300">
                          <span>vs</span>
                          <FileText className="w-4 h-4 text-amber-400" />
                          <span>{item.related_file}</span>
                        </div>
                      )}
                    </div>

                    {/* Evidence Comparison Snippets */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="bg-slate-900/90 p-3 rounded-xl border border-slate-800 space-y-1">
                        <span className="text-[10px] font-semibold text-slate-400 block">Primary Snippet / Metric</span>
                        <p className="text-slate-200 font-mono leading-relaxed">"{item.evidence_snippet}"</p>
                      </div>
                      {item.related_snippet && (
                        <div className="bg-slate-900/90 p-3 rounded-xl border border-slate-800 space-y-1">
                          <span className="text-[10px] font-semibold text-amber-400 block">Related Comparison Snippet</span>
                          <p className="text-slate-200 font-mono leading-relaxed">"{item.related_snippet}"</p>
                        </div>
                      )}
                    </div>

                    {/* Potential RAG Impact & Remediation */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs">
                      <div className="bg-rose-500/5 p-3 rounded-xl border border-rose-500/20 text-rose-300 space-y-1">
                        <span className="font-semibold text-[11px] block text-rose-400">Potential RAG Impact:</span>
                        <p className="text-[11px] leading-relaxed">{item.potential_rag_impact}</p>
                      </div>
                      <div className="bg-indigo-500/5 p-3 rounded-xl border border-indigo-500/20 text-indigo-300 space-y-1">
                        <span className="font-semibold text-[11px] block text-indigo-400">Remediation Advice:</span>
                        <p className="text-[11px] leading-relaxed">{item.remediation}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
