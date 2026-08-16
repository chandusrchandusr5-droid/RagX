import React from 'react';
import { X, ExternalLink, FileText, Download } from 'lucide-react';
import { viewDocumentUrl } from '../services/api';

export default function PdfViewerModal({ document, onClose }) {
  if (!document) return null;

  const pdfUrl = viewDocumentUrl(document.document_id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="glass-card w-full max-w-5xl h-[88vh] rounded-2xl flex flex-col overflow-hidden border border-slate-800 shadow-2xl">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                {document.document_name}
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {document.status}
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                ID: {document.document_id} • Size: {document.file_size} • Pages: {document.total_pages}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="Open in new browser tab"
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              New Tab
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* PDF Viewer Body */}
        <div className="flex-1 bg-slate-900/50 p-2 relative">
          <iframe
            src={pdfUrl}
            title={`PDF Viewer - ${document.document_name}`}
            className="w-full h-full rounded-xl border border-slate-800 bg-white"
          />
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-2.5 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between text-xs text-slate-500">
          <span>RAGX Secure Document Viewer</span>
          <span>Source: {document.active_path || document.trash_path}</span>
        </div>
      </div>
    </div>
  );
}
