/**
 * API client for the LLM Knesset backend.
 */

const API_BASE = '';

function handleUnauth() {
  window.location.reload();
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, { credentials: 'include', ...options });
  if (response.status === 401) {
    handleUnauth();
    throw new Error('Not authenticated');
  }
  return response;
}

export const api = {
  async getMe() {
    try {
      const response = await fetch(`${API_BASE}/api/me`, { credentials: 'include' });
      if (!response.ok) return null;
      return response.json();
    } catch {
      return null;
    }
  },

  async logout() {
    const { firebaseSignOut } = await import('./firebase');
    await firebaseSignOut().catch(() => {});
    await fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'include' });
    window.location.reload();
  },

  async listConversations() {
    const response = await fetchJSON(`${API_BASE}/api/conversations`);
    if (!response.ok) throw new Error('Failed to list conversations');
    return response.json();
  },

  async createConversation() {
    const response = await fetchJSON(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!response.ok) throw new Error('Failed to create conversation');
    return response.json();
  },

  async getConversation(conversationId) {
    const response = await fetchJSON(`${API_BASE}/api/conversations/${conversationId}`);
    if (!response.ok) throw new Error('Failed to get conversation');
    return response.json();
  },

  async sendMessageStream(conversationId, content, onEvent, signal) {
    const response = await fetchJSON(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
        signal,
      }
    );
    if (!response.ok) throw new Error('Failed to send message');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        for (const line of part.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              onEvent(event.type, event);
            } catch (e) {
              console.error('Failed to parse SSE event:', e);
            }
          }
        }
      }
    }
  },

  // ── User model preferences (all authenticated users) ────────────
  async getPrefs() {
    const response = await fetchJSON(`${API_BASE}/api/prefs`);
    if (!response.ok) throw new Error('Failed to get prefs');
    return response.json();
  },

  async updatePrefs(updates) {
    const response = await fetchJSON(`${API_BASE}/api/prefs`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update prefs');
    return response.json();
  },

  // ── Models ────────────────────────────────────────────────────────
  async listModels() {
    const response = await fetchJSON(`${API_BASE}/api/models`);
    if (!response.ok) throw new Error('Failed to fetch models');
    return response.json();
  },

  // ── Admin settings ────────────────────────────────────────────────
  async getSettings() {
    const response = await fetchJSON(`${API_BASE}/api/settings`);
    if (response.status === 403) throw new Error('forbidden');
    if (!response.ok) throw new Error('Failed to get settings');
    return response.json();
  },

  async updateSettings(updates) {
    const response = await fetchJSON(`${API_BASE}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update settings');
    return response.json();
  },

  async testConnection() {
    const response = await fetchJSON(`${API_BASE}/api/settings/test`, { method: 'POST' });
    if (!response.ok) throw new Error('Failed to test connection');
    return response.json();
  },
};
