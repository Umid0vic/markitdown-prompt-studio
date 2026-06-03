/**
 * API client for MarkItDown Prompt Studio backend.
 */
const API = {
  base: '/api',

  async request(method, path, body = null, isFormData = false) {
    const opts = { method, headers: {} };
    if (body && !isFormData) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    } else if (body && isFormData) {
      opts.body = body;
    }
    const res = await fetch(this.base + path, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return res.json();
    if (ct.includes('application/zip')) return res.blob();
    return res.text();
  },

  // Config
  getConfig() { return this.request('GET', '/config'); },

  // Convert
  convertFiles(files) {
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    return this.request('POST', '/convert', fd, true);
  },

  // Prompt generation
  generatePrompt(data) { return this.request('POST', '/generate-prompt', data); },

  // Library
  getStats() { return this.request('GET', '/library/stats'); },
  getPrompts(params = {}) {
    const q = new URLSearchParams();
    if (params.folder_id) q.set('folder_id', params.folder_id);
    if (params.tag) q.set('tag', params.tag);
    if (params.search) q.set('search', params.search);
    if (params.favorites_only) q.set('favorites_only', 'true');
    return this.request('GET', '/library/prompts?' + q.toString());
  },
  savePrompt(data) { return this.request('POST', '/library/prompts', data); },
  getPromptContent(id) { return this.request('GET', `/library/prompts/${id}`); },
  deletePrompt(id) { return this.request('DELETE', `/library/prompts/${id}`); },
  toggleFavorite(id) { return this.request('POST', `/library/prompts/${id}/favorite`); },
  movePrompt(id, folderId) { return this.request('POST', `/library/prompts/${id}/move`, { folder_id: folderId }); },
  addTag(id, tag) { return this.request('POST', `/library/prompts/${id}/tags`, { tag }); },
  removeTag(id, tag) { return this.request('DELETE', `/library/prompts/${id}/tags/${encodeURIComponent(tag)}`); },
  getHistory(id) { return this.request('GET', `/library/prompts/${id}/history`); },
  restoreVersion(promptId, versionId) { return this.request('POST', `/library/prompts/${promptId}/history/${versionId}/restore`); },
  getTags() { return this.request('GET', '/library/tags'); },

  // Folders
  getFolders() { return this.request('GET', '/library/folders'); },
  createFolder(name, parentId = null) { return this.request('POST', '/library/folders', { name, parent_id: parentId }); },
  renameFolder(id, name) { return this.request('PUT', `/library/folders/${id}`, { name }); },
  deleteFolder(id) { return this.request('DELETE', `/library/folders/${id}`); },

  // Templates
  getBuiltinTemplates() { return this.request('GET', '/templates/builtin'); },
  getCustomTemplates() { return this.request('GET', '/templates/custom'); },
  saveTemplate(data) { return this.request('POST', '/templates/custom', data); },
  deleteTemplate(id) { return this.request('DELETE', `/templates/custom/${id}`); },

  // Settings
  getSettings() { return this.request('GET', '/settings'); },
  saveSettings(data) { return this.request('PUT', '/settings', data); },

  // Export
  exportLibrary() { return this.request('GET', '/library/export'); },
  importPrompt(file, folderId = null) {
    const fd = new FormData();
    fd.append('file', file);
    if (folderId) fd.append('folder_id', folderId);
    return this.request('POST', '/library/import', fd, true);
  },
};
