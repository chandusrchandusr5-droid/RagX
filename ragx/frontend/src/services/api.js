import axios from 'axios';

const LIVE_BACKEND_URL = 'https://niagara-aims-opera-terrorism.trycloudflare.com';

const API_BASE_URL = `${LIVE_BACKEND_URL}/api`;


const apiClient = axios.create({
  baseURL: API_BASE_URL,
});


export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const fetchDocuments = async (status = null) => {
  const params = status ? { status } : {};
  const response = await apiClient.get('/documents', { params });
  return response.data;
};

export const viewDocumentUrl = (documentId) => {
  return `${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/view`;
};


export const softDeleteDocument = async (documentId) => {
  const response = await apiClient.delete(`/documents/${encodeURIComponent(documentId)}`);
  return response.data;
};

export const restoreDocument = async (documentId) => {
  const response = await apiClient.post(`/documents/${encodeURIComponent(documentId)}/restore`);
  return response.data;
};

export const permanentlyDeleteDocument = async (documentId) => {
  const response = await apiClient.delete(`/documents/${encodeURIComponent(documentId)}/permanent`);
  return response.data;
};




export const queryRag = async (question, topK = 3) => {
  const response = await apiClient.post('/rag/query', {
    question,
    top_k: topK,
  });
  return response.data;
};

export const fetchQualityAudit = async () => {
  const response = await apiClient.get('/quality/audit');
  return response.data;
};

export const evaluateAnswer = async (query, answer, retrievedEvidence = []) => {
  const response = await apiClient.post('/evaluator/evaluate', {
    query,
    answer,
    retrieved_evidence: retrievedEvidence,
  });
  return response.data;
};

export const queryAndEvaluateRag = async (question, topK = 3) => {
  const response = await apiClient.post('/evaluator/query-and-evaluate', {
    question,
    top_k: topK,
  });
  return response.data;
};

export const fetchEvaluationAnalytics = async () => {
  const response = await apiClient.get('/evaluator/analytics');
  return response.data;
};

export const fetchEvaluationHistory = async (limit = 50) => {
  const response = await apiClient.get(`/evaluator/history?limit=${limit}`);
  return response.data;
};

export const fetchNovaGreeting = async () => {
  const response = await apiClient.get('/nova/greeting');
  return response.data;
};

export const sendNovaMessage = async (message, contextPage = 'general') => {
  const response = await apiClient.post('/nova/chat', {
    message,
    context_page: contextPage,
  });
  return response.data;
};



