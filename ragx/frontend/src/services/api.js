import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api` 
  : (import.meta.env.DEV ? 'http://127.0.0.1:8000/api' : 'https://ragx-production.up.railway.app/api');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// Dynamic Authorization Header Interceptor
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('ragx_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- AUTHENTICATION APIS ---
export const registerUser = async (email, fullName, password) => {
  const response = await apiClient.post('/auth/register', { email, full_name: fullName, password });
  return response.data;
};

export const loginUser = async (email, password) => {
  const response = await apiClient.post('/auth/login', { email, password });
  return response.data;
};

export const logoutUser = async () => {
  try {
    const response = await apiClient.post('/auth/logout');
    return response.data;
  } catch (e) {
    return { message: "Logged out locally" };
  }
};

export const fetchCurrentUser = async () => {
  const response = await apiClient.get('/auth/me');
  return response.data;
};

export const updateProfile = async (fullName) => {
  const response = await apiClient.put('/auth/profile', { full_name: fullName });
  return response.data;
};

export const changePassword = async (currentPassword, newPassword) => {
  const response = await apiClient.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
};

export const deleteAccount = async () => {
  const response = await apiClient.delete('/auth/account');
  return response.data;
};

// --- ADMIN APIS ---
export const fetchAdminDashboard = async () => {
  const response = await apiClient.get('/admin/dashboard');
  return response.data;
};

export const fetchAdminUsers = async () => {
  const response = await apiClient.get('/admin/users');
  return response.data;
};

export const fetchAdminUserDocuments = async (userId) => {
  const response = await apiClient.get(`/admin/users/${encodeURIComponent(userId)}/documents`);
  return response.data;
};

export const deleteUserAdmin = async (userId) => {
  const response = await apiClient.delete(`/admin/users/${encodeURIComponent(userId)}`);
  return response.data;
};

export const fetchAdminActivity = async (limit = 100) => {
  const response = await apiClient.get(`/admin/activity?limit=${limit}`);
  return response.data;
};

// --- RAG & DOCUMENT APIS ---
export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const fetchDocuments = async (status = null) => {
  const params = status ? { status } : {};
  const response = await apiClient.get('/documents', { params });
  return response.data;
};

export const viewDocumentUrl = (documentId) => {
  const token = localStorage.getItem('ragx_token');
  return `${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/view${token ? `?token=${encodeURIComponent(token)}` : ''}`;
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
  const response = await apiClient.post('/rag/query', { question, top_k: topK });
  return response.data;
};

export const fetchQualityAudit = async (documentId = null) => {
  const params = documentId && documentId !== 'all' ? { document_id: documentId } : {};
  const response = await apiClient.get('/quality/audit', { params });
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
