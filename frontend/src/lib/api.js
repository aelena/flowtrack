import { get } from 'svelte/store';
import { apiKey } from './stores.js';

const BASE_URL = typeof window !== 'undefined'
  ? (window.__PUBLIC_API_URL || 'http://localhost:7028')
  : (process.env.INTERNAL_API_URL || 'http://api:8000');

function headers() {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': get(apiKey),
  };
}

function extractDetail(body, fallback) {
  if (body && typeof body === 'object' && body.detail) return body.detail;
  return fallback;
}

async function request(method, path, body = null) {
  const opts = { method, headers: headers() };
  if (body && method !== 'GET') {
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(`${BASE_URL}${path}`, opts);
  if (resp.status === 204) return null;
  if (!resp.ok) {
    const err = await resp.json().catch(() => null);
    throw new Error(extractDetail(err, resp.statusText));
  }
  const contentType = resp.headers.get('content-type') || '';
  if (contentType.includes('application/json') || contentType.includes('application/problem+json')) {
    return resp.json();
  }
  return resp;
}

// Areas
export const listAreas = () => request('GET', '/api/areas/');
export const createArea = (name) => request('POST', '/api/areas/', { name });
export const updateArea = (id, name) => request('PUT', `/api/areas/${id}`, { name });
export const deleteArea = (id) => request('DELETE', `/api/areas/${id}`);

// Projects
export const listProjects = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request('GET', `/api/projects/${qs ? '?' + qs : ''}`);
};
export const getAllTags = () => request('GET', '/api/projects/tags/all');
export const getProject = (id) => request('GET', `/api/projects/${id}`);
export const createProject = (data) => request('POST', '/api/projects/', data);
export const updateProject = (id, data) => request('PUT', `/api/projects/${id}`, data);
export const archiveProject = (id) => request('POST', `/api/projects/${id}/archive`);
export const unarchiveProject = (id) => request('POST', `/api/projects/${id}/unarchive`);
export const setProjectArchived = (id, archived) =>
  archived ? archiveProject(id) : unarchiveProject(id);
export const exportProject = async (id) => {
  const resp = await fetch(`${BASE_URL}/api/projects/${id}/export`, {
    method: 'GET',
    headers: { 'X-API-Key': get(apiKey) },
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || 'Export failed');
  }
  return resp.blob();
};
export const getPending = (id) => request('GET', `/api/projects/${id}/pending`);
export const addCollaborator = (id, collab) => request('POST', `/api/projects/${id}/collaborators`, collab);

// Tasks
export const listTasks = (projectId) => request('GET', `/api/projects/${projectId}/tasks/`);
export const createTasks = (projectId, content, description = null) =>
  request('POST', `/api/projects/${projectId}/tasks/`, { content, description });
export const updateTask = (projectId, taskId, data) =>
  request('PUT', `/api/projects/${projectId}/tasks/${taskId}`, data);
export const deleteTask = (projectId, taskId) =>
  request('DELETE', `/api/projects/${projectId}/tasks/${taskId}`);

// Notes
export const listNotes = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request('GET', `/api/notes/${qs ? '?' + qs : ''}`);
};
export const createNote = (data) => request('POST', '/api/notes/', data);
export const updateNote = (id, content) => request('PUT', `/api/notes/${id}`, { content });
export const deleteNote = (id) => request('DELETE', `/api/notes/${id}`);

// Files
export const listFiles = (projectId) => request('GET', `/api/projects/${projectId}/files/`);
export const uploadFile = async (projectId, file, folder = null) => {
  const formData = new FormData();
  formData.append('file', file);
  if (folder) formData.append('folder', folder);
  const resp = await fetch(`${BASE_URL}/api/projects/${projectId}/files/`, {
    method: 'POST',
    headers: { 'X-API-Key': get(apiKey) },
    body: formData,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => null);
    throw new Error(extractDetail(err, 'File upload failed'));
  }
  return resp.json();
};
export const deleteFile = (projectId, fileId) =>
  request('DELETE', `/api/projects/${projectId}/files/${fileId}`);

// LLM
export const generatePRD = (id) => request('POST', `/api/llm/generate/prd/${id}`);
export const generateBRD = (id) => request('POST', `/api/llm/generate/brd/${id}`);
export const generateMRD = (id) => request('POST', `/api/llm/generate/mrd/${id}`);
export const generateSocial = (id) => request('POST', `/api/llm/generate/social/${id}`);
export const chatWithProject = (id, message) => request('POST', `/api/llm/chat/${id}`, { message });
export const suggestNextSteps = (id) => request('POST', `/api/llm/suggest/${id}`);

// Config
export const getConfigYaml = () => request('GET', '/api/config/yaml');
export const putConfigYaml = (yaml) => request('PUT', '/api/config/yaml', { yaml });
export const resetConfig = () => request('POST', '/api/config/reset');

// Backup
export const exportBackup = () => request('GET', '/api/backup/export');
export const importBackup = (data) => request('POST', '/api/backup/import', data);
