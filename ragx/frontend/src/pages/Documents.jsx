import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, RefreshCw, HardDrive, Trash2, Eye, RotateCcw, XCircle } from 'lucide-react';
import { uploadDocument, fetchDocuments, softDeleteDocument, restoreDocument, permanentlyDeleteDocument } from '../services/api';
import PdfViewerModal from '../components/PdfViewerModal';

export default function Documents() {
  const [activeTab, setActiveTab] = useState('ACTIVE'); // 'ACTIVE' | 'DELETED'
  const [activeDocs, setActiveDocs] = useState([]);
  const [deletedDocs, setDeletedDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [actionDocId, setActionDocId] = useState(null);
  const [viewingDoc, setViewingDoc] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const loadDocuments = async (retries = 2) => {
    setLoading(true);
    setError(null);
    try {
      const [actData, delData] = await Promise.all([
        fetchDocuments('ACTIVE'),
        fetchDocuments('DELETED')
      ]);
      setActiveDocs(actData.documents || []);
      setDeletedDocs(delData.documents || []);
    } catch (err) {
      console.error(err);
      if (retries > 0) {
        setTimeout(() => loadDocuments(retries - 1), 1000);
        return;
      }
      setError('Backend connection loading... Click Refresh List above to reconnect.');
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadDocuments();
  }, []);

  const displayedDocs = activeTab === 'ACTIVE' ? activeDocs : deletedDocs;


  const handleFileUpload = async (file) => {
    if (!file) return;

    const fileExt = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'txt', 'md'].includes(fileExt)) {
      setError('Only PDF, TXT, and MD files are supported.');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const result = await uploadDocument(file);
      setSuccessMsg(`Successfully processed '${file.name}' (${result.document.total_pages} pages, ${result.document.total_chunks} vector chunks).`);
      setActiveTab('ACTIVE');
      loadDocuments();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to upload and process document.');
    } finally {
      setUploading(false);
    }
  };

  const handleSoftDelete = async (doc) => {
    if (!window.confirm(`Move '${doc.document_name}' to Deleted Documents (Trash)? It will be excluded from RAG queries and Data Quality Audits.`)) {
      return;
    }

    setActionDocId(doc.document_id);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await softDeleteDocument(doc.document_id);
      setSuccessMsg(`Document '${doc.document_name}' moved to Deleted Documents.`);
      loadDocuments();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || `Failed to delete document '${doc.document_name}'.`);
    } finally {
      setActionDocId(null);
    }
  };

  const handleRestore = async (doc) => {
    setActionDocId(doc.document_id);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await restoreDocument(doc.document_id);
      setSuccessMsg(`Document '${doc.document_name}' restored to Active Knowledge Base (${res.reindexed_chunks} vector chunks re-indexed).`);
      loadDocuments();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || `Failed to restore document '${doc.document_name}'.`);
    } finally {
      setActionDocId(null);
    }
  };

  const handlePermanentDelete = async (doc) => {
    if (!window.confirm(`PERMANENT DELETION WARNING: Are you sure you want to permanently destroy '${doc.document_name}'?\n\nThis will permanently delete the physical PDF file, metadata, and all vector chunks from ChromaDB. This action CANNOT be undone.`)) {
      return;
    }

    setActionDocId(doc.document_id);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await permanentlyDeleteDocument(doc.document_id);
      setSuccessMsg(`Document '${doc.document_name}' permanently deleted.`);
      loadDocuments();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || `Failed to permanently delete document '${doc.document_name}'.`);
    } finally {
      setActionDocId(null);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-7 h-7 text-indigo-400" />
            Knowledge Base Documents
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Upload PDFs to index vectors in ChromaDB, view PDFs in-web, and manage document lifecycles.
          </p>
        </div>
        <button
          onClick={loadDocuments}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh List
        </button>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Drag & Drop Upload Card */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`glass-card p-8 rounded-2xl border-2 border-dashed text-center transition-all ${
          dragActive
            ? 'border-indigo-400 bg-indigo-500/10 scale-[1.01]'
            : 'border-slate-700 hover:border-slate-600 bg-slate-900/40'
        }`}
      >
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
            <Upload className={`w-8 h-8 ${uploading ? 'animate-bounce' : ''}`} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">
              {uploading ? 'Parsing & Indexing PDF...' : 'Upload PDF Document'}
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Drag and drop your PDF here, or browse files from your computer.
            </p>
          </div>
          <label className="inline-block">
            <input
              type="file"
              accept=".pdf,.txt,.md"
              onChange={(e) => e.target.files && handleFileUpload(e.target.files[0])}
              disabled={uploading}
              className="hidden"
            />
            <span className="cursor-pointer inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition">
              {uploading ? 'Processing File...' : 'Select PDF File'}
            </span>
          </label>
        </div>
      </div>

      {/* Tab Switcher: Active vs. Deleted Documents */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('ACTIVE')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
                activeTab === 'ACTIVE'
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <FileText className="w-4 h-4" />
              Active Knowledge Base ({activeDocs.length})
            </button>
            <button
              onClick={() => setActiveTab('DELETED')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
                activeTab === 'DELETED'
                  ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Trash2 className="w-4 h-4" />
              Deleted Documents / Trash ({deletedDocs.length})
            </button>
          </div>
        </div>

        {/* Document Cards List */}
        {displayedDocs.length === 0 && !loading ? (
          <div className="glass-card p-12 rounded-2xl text-center space-y-3">
            <HardDrive className="w-12 h-12 text-slate-600 mx-auto" />
            <h3 className="text-base font-semibold text-slate-300">
              {activeTab === 'ACTIVE' ? 'No Active Documents Uploaded' : 'Trash is Empty'}
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {activeTab === 'ACTIVE'
                ? 'Upload a PDF document above to build your vector database and enable RAG queries.'
                : 'No soft-deleted documents in trash. Deleted documents will appear here for restoration or permanent removal.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {displayedDocs.map((doc) => (

              <div key={doc.document_id} className="glass-card p-5 rounded-xl space-y-4 flex flex-col justify-between border border-slate-800 hover:border-slate-700 transition">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white truncate max-w-[170px]" title={doc.document_name}>
                          {doc.document_name}
                        </h4>
                        <p className="text-[11px] text-slate-400">{doc.file_size} • ID: {doc.document_id.slice(0, 10)}...</p>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                      doc.status === 'ACTIVE'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>
                      {doc.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-xs">
                    <div className="bg-slate-900/60 p-2 rounded-lg">
                      <span className="text-[10px] text-slate-500 block">Total Pages</span>
                      <span className="font-semibold text-slate-200">{doc.total_pages} Pages</span>
                    </div>
                    <div className="bg-slate-900/60 p-2 rounded-lg">
                      <span className="text-[10px] text-slate-500 block">Vector Chunks</span>
                      <span className="font-semibold text-indigo-300">{doc.total_chunks} Chunks</span>
                    </div>
                  </div>
                </div>

                {/* Action Buttons Toolbar */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-[10px] text-slate-500">
                    {doc.status === 'ACTIVE' ? `Uploaded: ${doc.upload_date.split(' ')[0]}` : `Deleted: ${doc.deletion_date ? doc.deletion_date.split(' ')[0] : 'N/A'}`}
                  </span>

                  <div className="flex items-center space-x-1.5">
                    {/* View PDF Option */}
                    <button
                      onClick={() => setViewingDoc(doc)}
                      title="Open in Web PDF Viewer"
                      className="p-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 transition flex items-center gap-1 text-[11px] font-medium px-2.5"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Open
                    </button>

                    {doc.status === 'ACTIVE' ? (
                      /* Soft Delete Button */
                      <button
                        onClick={() => handleSoftDelete(doc)}
                        disabled={actionDocId === doc.document_id}
                        title="Move to Deleted Documents"
                        className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition flex items-center gap-1 text-[11px] font-medium px-2.5 disabled:opacity-50"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete
                      </button>
                    ) : (
                      /* Restore & Permanent Delete Buttons */
                      <>
                        <button
                          onClick={() => handleRestore(doc)}
                          disabled={actionDocId === doc.document_id}
                          title="Restore to Active Knowledge Base"
                          className="p-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition flex items-center gap-1 text-[11px] font-medium px-2 disabled:opacity-50"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Restore
                        </button>
                        <button
                          onClick={() => handlePermanentDelete(doc)}
                          disabled={actionDocId === doc.document_id}
                          title="Permanently Destroy Document & Vector Chunks"
                          className="p-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 transition flex items-center gap-1 text-[11px] font-medium px-2 disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          Delete Perm
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* PDF Viewer Modal */}
      {viewingDoc && (
        <PdfViewerModal
          document={viewingDoc}
          onClose={() => setViewingDoc(null)}
        />
      )}
    </div>
  );
}
