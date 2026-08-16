import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api` 
  : '/api';



export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(`${API_BASE_URL}/documents/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const fetchDocuments = async (status = null) => {
  const params = status ? { status } : {};
  const response = await axios.get(`${API_BASE_URL}/documents`, { params });
  return response.data;
};

export const viewDocumentUrl = (documentId) => {
  return `${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/view`;
};

export const softDeleteDocument = async (documentId) => {
  const response = await axios.delete(`${API_BASE_URL}/documents/${encodeURIComponent(documentId)}`);
  return response.data;
};

export const restoreDocument = async (documentId) => {
  const response = await axios.post(`${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/restore`);
  return response.data;
};

export const permanentlyDeleteDocument = async (documentId) => {
  const response = await axios.delete(`${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/permanent`);
  return response.data;
};



export const queryRag = async (question, topK = 3) => {
  const response = await axios.post(`${API_BASE_URL}/rag/query`, {
    question,
    top_k: topK,
  });

  return response.data;
};

export const fetchQualityAudit = async () => {
  const response = await axios.get(`${API_BASE_URL}/quality/audit`);
  return response.data;
};

export const evaluateAnswer = async (query, answer, retrievedEvidence = []) => {
  const response = await axios.post(`${API_BASE_URL}/evaluator/evaluate`, {
    query,
    answer,
    retrieved_evidence: retrievedEvidence,
  });
  return response.data;
};

export const queryAndEvaluateRag = async (question, topK = 3) => {
  const response = await axios.post(`${API_BASE_URL}/evaluator/query-and-evaluate`, {
    question,
    top_k: topK,
  });
  return response.data;
};

export const fetchEvaluationAnalytics = async () => {
  const response = await axios.get(`${API_BASE_URL}/evaluator/analytics`);
  return response.data;
};

export const fetchEvaluationHistory = async (limit = 50) => {
  const response = await axios.get(`${API_BASE_URL}/evaluator/history?limit=${limit}`);
  return response.data;
};

export const fetchNovaGreeting = async () => {
  const response = await axios.get(`${API_BASE_URL}/nova/greeting`);
  return response.data;
};

export const sendNovaMessage = async (message, contextPage = 'general') => {
  const response = await axios.post(`${API_BASE_URL}/nova/chat`, {
    message,
    context_page: contextPage,
  });
  return response.data;
};


