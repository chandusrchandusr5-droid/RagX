import React, { useState } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  HelpCircle, 
  Search, 
  Layers, 
  FileText, 
  Brain,
  Zap,
  ArrowRight,
  Sparkles,
  Sliders
} from 'lucide-react';
import { queryAndEvaluateRag, evaluateAnswer } from '../services/api';

export default function AnswerEvaluator() {
  const [query, setQuery] = useState('');
  const [useCustomOverride, setUseCustomOverride] = useState(false);
  const [customAnswer, setCustomAnswer] = useState('');
  const [customEvidenceText, setCustomEvidenceText] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [ragResult, setRagResult] = useState(null);
  const [error, setError] = useState(null);

  const handleRunEvaluation = async (e) => {
    e.preventDefault();
    if (!query || !query.trim()) return;

    setLoading(true);
    setError(null);
    setReport(null);
    setRagResult(null);

    try {
      if (!useCustomOverride) {
        // Mode 1: Dynamic RAG Retrieval & Answer Evaluation via Backend RAG Pipeline
        const res = await queryAndEvaluateRag(query.trim(), 3);
        setRagResult({
          question: res.question,
          answer: res.answer,
          retrieved_evidence: res.retrieved_evidence || []
        });
        setReport(res.evaluation_report);
      } else {
        // Mode 2: Manual Custom Answer & Context Override (For testing specific edge-case scenarios)
        const customEvidence = customEvidenceText.trim() ? [
          {
            id: 'chunk_override_001',
            chunk_id: 'chunk_override_001',
            document_name: 'Manual_Override_Doc.pdf',
            page_number: 1,
            text: customEvidenceText.trim()
          }
        ] : [];

        const res = await evaluateAnswer(query.trim(), customAnswer.trim(), customEvidence);
        const displayEvidence = customEvidence.length > 0 ? customEvidence : (
          (res.claim_analysis || [])
            .map(c => c.matched_evidence ? {
              chunk_id: c.matched_evidence.chunk_id,
              document_name: c.matched_evidence.source_file,
              page_number: c.matched_evidence.page_number,
              text: c.matched_evidence.evidence_snippet
            } : null)
            .filter(Boolean)
        );
        setRagResult({
          question: query.trim(),
          answer: customAnswer.trim(),
          retrieved_evidence: displayEvidence
        });
        setReport(res);
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to evaluate RAG answer.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'HIGHLY_RELIABLE':
        return <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5" /> Highly Reliable</span>;
      case 'PARTIALLY_RELIABLE':
        return <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> Partially Reliable</span>;
      case 'UNRELIABLE':
        return <span className="px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1.5"><XCircle className="w-3.5 h-3.5" /> Unreliable / Hallucination Risk</span>;
      default:
        return <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1.5"><HelpCircle className="w-3.5 h-3.5" /> Not Evaluable (Insufficient Evidence)</span>;
    }
  };

  const getFailureBadge = (cat) => {
    switch (cat) {
      case 'WELL_GROUNDED':
        return <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">Well Grounded</span>;
      case 'INCOMPLETE_ANSWER':
        return <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">Incomplete Answer (Missing Question Aspects)</span>;
      case 'UNSUPPORTED_CLAIMS':
      case 'GENERATION_FAILURE':
        return <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20">Unsupported Claims (Hallucination Risk)</span>;
      case 'RETRIEVAL_FAILURE':
        return <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">Retrieval Failure (Full-KB Oracle Found Evidence)</span>;
      case 'KNOWLEDGE_CONFLICT':
        return <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20">Knowledge Base Conflict</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">Evidence Insufficiency</span>;
    }
  };


  const getClaimStatusBadge = (status) => {
    switch (status) {
      case 'SUPPORTED':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">SUPPORTED (Grounded)</span>;
      case 'CONTRADICTED':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">CONTRADICTED (Direct Hallucination)</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">UNSUPPORTED (Hallucination Risk)</span>;
    }
  };

  const getHallucinationRiskBadge = (risk) => {
    switch (risk) {
      case 'LOW':
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5" /> Low Hallucination Risk</span>;
      case 'MEDIUM':
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> Medium Hallucination Risk</span>;
      case 'HIGH':
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1.5"><XCircle className="w-3.5 h-3.5" /> High Hallucination Risk</span>;
      default:
        return <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1.5"><HelpCircle className="w-3.5 h-3.5" /> Unknown Risk</span>;
    }
  };


  return (
    <div className="max-w-[1700px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 glass-panel p-6 rounded-2xl border border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-6 h-6 text-indigo-400" />
            <h1 className="text-2xl font-extrabold text-white">RAGX Answer Reliability &amp; Hallucination Evaluator</h1>
          </div>
          <p className="text-sm text-slate-400">
            Type any question to dynamically execute RAG retrieval, generate answers, assess 5-tuple citation traceability, and detect hallucinations.
          </p>
        </div>
      </div>

      {/* Input Form & Evaluation Runner */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-5 glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" /> Dynamic RAG Evaluation
          </h2>

          <form onSubmit={handleRunEvaluation} className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Editable Question / Query
                </label>
                {query && (
                  <button
                    type="button"
                    onClick={() => { setQuery(''); setReport(null); setRagResult(null); }}
                    className="text-[11px] text-slate-400 hover:text-slate-200 underline"
                  >
                    Clear Input
                  </button>
                )}
              </div>
              <textarea
                rows="3"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type any custom question to evaluate RAG answer reliability..."
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                required
              />
            </div>

            {/* Quick Sample Queries Bar */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-slate-400">Quick Sample Queries:</span>
              <div className="flex flex-wrap gap-1.5">
                {[
                  "Summarize the key requirements from the document",
                  "What are the main eligibility criteria and conditions?",
                  "Explain the core process and steps described"
                ].map((sample, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setQuery(sample)}
                    className="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-indigo-600/30 hover:border-indigo-500/50 border border-slate-700/80 text-[11px] text-slate-300 transition text-left"
                  >
                    {sample}
                  </button>
                ))}
              </div>
            </div>

            {/* Optional Manual Context Override Toggle */}
            <div className="pt-2 border-t border-slate-800/80">
              <label className="flex items-center space-x-2 text-xs text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useCustomOverride}
                  onChange={(e) => setUseCustomOverride(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="flex items-center gap-1"><Sliders className="w-3.5 h-3.5 text-indigo-400" /> Enable Custom Answer / Context Override</span>
              </label>
            </div>


            {useCustomOverride && (
              <div className="space-y-3 pt-2 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                <div>
                  <label className="block text-[11px] font-semibold uppercase text-slate-400 mb-1">
                    Custom Answer to Evaluate
                  </label>
                  <textarea
                    rows="2"
                    value={customAnswer}
                    onChange={(e) => setCustomAnswer(e.target.value)}
                    placeholder="Enter custom generated answer text..."
                    className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold uppercase text-slate-400 mb-1">
                    Custom Evidence Snippet
                  </label>
                  <textarea
                    rows="3"
                    value={customEvidenceText}
                    onChange={(e) => setCustomEvidenceText(e.target.value)}
                    placeholder="Enter custom evidence text snippet..."
                    className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20"
            >
              {loading ? (
                <>
                  <Sparkles className="w-4 h-4 animate-spin text-indigo-200" /> Executing Dynamic Evaluation...
                </>
              ) : (
                <>
                  Run Answer Reliability Evaluation <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-300">
              {error}
            </div>
          )}
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-7 space-y-6">
          {report && ragResult ? (
            <div className="space-y-6">
              {/* Query & RAG Output Summary Card */}
              <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
                <div>
                  <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">Submitted Question</span>
                  <p className="text-base font-bold text-white mt-0.5">{ragResult.question}</p>
                </div>

                <div className="bg-slate-900/80 p-3.5 rounded-xl border border-indigo-500/20 space-y-1">
                  <span className="text-xs font-semibold text-indigo-400 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" /> Synthesized Answer (Retrieved Context)
                  </span>
                  <p className="text-xs text-slate-200 leading-relaxed font-mono">
                    "{ragResult.answer}"
                  </p>
                </div>
              </div>

              {/* Score Gauge & Hallucination Assessment Card */}
              <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
                  <div className="space-y-1">
                    <span className="text-xs uppercase font-semibold text-slate-400 tracking-wider">Evaluation &amp; Hallucination Status</span>
                    <div className="flex flex-wrap items-center gap-2">
                      {getStatusBadge(report.reliability_status)}
                      {getHallucinationRiskBadge(report.hallucination_risk)}
                    </div>
                  </div>
                  <div>
                    {getFailureBadge(report.failure_category)}
                  </div>
                </div>


                {/* Score Breakdown Gauge */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
                  <div className="flex flex-col items-center justify-center p-4 bg-slate-900/60 rounded-xl border border-slate-800">
                    <span className="text-3xl font-extrabold text-white">{report.overall_reliability_score}%</span>
                    <span className="text-[11px] text-slate-400 mt-1 uppercase tracking-wider">Reliability Score</span>
                  </div>

                  <div className="md:col-span-3 space-y-3">
                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="text-slate-300">Claim Support Score (S_supp - {((report.scoring_breakdown?.configured_weights?.support_weight || 0.6) * 100).toFixed(0)}%)</span>
                        <span className="text-indigo-400 font-bold">{report.scoring_breakdown?.sub_scores?.claim_support_score}%</span>
                      </div>
                      <div className="w-full bg-slate-900 rounded-full h-2">
                        <div
                          className="bg-indigo-500 h-2 rounded-full transition-all"
                          style={{ width: `${report.scoring_breakdown?.sub_scores?.claim_support_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="text-slate-300">Citation Traceability Score (S_cov - {((report.scoring_breakdown?.configured_weights?.coverage_weight || 0.2) * 100).toFixed(0)}%)</span>
                        <span className="text-teal-400 font-bold">{report.scoring_breakdown?.sub_scores?.citation_coverage_score}%</span>
                      </div>
                      <div className="w-full bg-slate-900 rounded-full h-2">
                        <div
                          className="bg-teal-400 h-2 rounded-full transition-all"
                          style={{ width: `${report.scoring_breakdown?.sub_scores?.citation_coverage_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="text-slate-300">Retrieval Similarity Score (S_sim - {((report.scoring_breakdown?.configured_weights?.similarity_weight || 0.2) * 100).toFixed(0)}%)</span>
                        <span className="text-purple-400 font-bold">{report.scoring_breakdown?.sub_scores?.retrieval_similarity_score}%</span>
                      </div>
                      <div className="w-full bg-slate-900 rounded-full h-2">

                        <div
                          className="bg-purple-500 h-2 rounded-full transition-all"
                          style={{ width: `${report.scoring_breakdown?.sub_scores?.retrieval_similarity_score}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Claim Analysis Table */}
              <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" /> Claim-Level Evidence Traceability
                </h3>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-900/80 uppercase tracking-wider text-[10px] text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="p-3">Claim ID</th>
                        <th className="p-3">Claim Statement</th>
                        <th className="p-3">Support Status</th>
                        <th className="p-3">5-Tuple Traceability</th>
                        <th className="p-3">Disparity Detail</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {report.claim_analysis?.map((c) => (
                        <tr key={c.claim_id} className="hover:bg-slate-900/40">
                          <td className="p-3 font-mono font-bold text-indigo-400">{c.claim_id}</td>
                          <td className="p-3 max-w-xs">{c.claim_text}</td>
                          <td className="p-3">{getClaimStatusBadge(c.support_status)}</td>
                          <td className="p-3 font-mono text-[11px] text-slate-400">
                            {c.matched_evidence ? (
                              <div className="space-y-0.5">
                                <div><span className="text-slate-500">File:</span> {c.matched_evidence.source_file}</div>
                                <div><span className="text-slate-500">Page:</span> {c.matched_evidence.page_number}</div>
                                <div><span className="text-slate-500">Chunk:</span> {c.matched_evidence.chunk_id?.substring(0, 16)}...</div>
                              </div>
                            ) : (
                              <span className="text-rose-400">Untraceable</span>
                            )}
                          </td>
                          <td className="p-3 max-w-xs text-slate-400">{c.disparity_detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Phase 2 Cross-Reference Cards */}
              {report.phase2_cross_references?.length > 0 && (
                <div className="glass-panel p-6 rounded-2xl border border-purple-500/30 bg-purple-500/5 space-y-4">
                  <h3 className="text-base font-bold text-purple-300 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-purple-400" /> Linked Data Quality Audit Findings
                  </h3>

                  <div className="space-y-3">
                    {report.phase2_cross_references.map((p2, idx) => (
                      <div key={idx} className="p-3 bg-slate-900/80 rounded-xl border border-purple-500/20 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-purple-400">{p2.issue_id} — {p2.issue_type}</span>
                          <span className="text-[10px] bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded font-medium">Confidence: {p2.confidence}</span>
                        </div>
                        <p className="text-slate-300">{p2.demonstrated_impact}</p>
                        <div className="text-[11px] text-slate-500 flex gap-4 pt-1">
                          <span>Source File: {p2.source_file}</span>
                          <span>Page: {p2.page_number}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center space-y-4">
              <Brain className="w-12 h-12 text-slate-600 mx-auto" />
              <h3 className="text-lg font-bold text-white">No Evaluation Run Selected</h3>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Type any question in the left panel to execute an instant end-to-end RAG retrieval, answer generation, and claim-level reliability evaluation.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
