import { state, setToken } from "./state.js";

const API_BASE = window.location.origin;

async function apiFetch(path, options = {}) {
  const headers = options.headers ? { ...options.headers } : {};
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const bodyIsFormData = options.body instanceof FormData;
  const resolvedHeaders = bodyIsFormData
    ? headers
    : { "Content-Type": "application/json", ...headers };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: resolvedHeaders,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `درخواست با خطا مواجه شد (${response.status})`);
  }

  if (response.status === 204) return null;
  return response.json();
}

export async function loginUser(username, password) {
  const data = await apiFetch("/auth/jwt/create/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
    headers: {},
  });
  setToken(data.access);
  return data;
}

export async function fetchCurrentUser() {
  const user = await apiFetch("/auth/users/me/");
  state.currentUser = user;
  return user;
}

export async function fetchConversations() {
  const data = await apiFetch("/api/conversations/");
  state.conversations = data;
  return data;
}

export async function fetchMessages(conversationId) {
  return apiFetch(`/api/conversations/${conversationId}/messages/`);
}

export async function createConversation(recipientId, content) {
  return apiFetch("/api/messages/", {
    method: "POST",
    body: JSON.stringify({ recipient_id: recipientId, content }),
  });
}

export async function uploadAttachment(conversationId, messageId, file) {
  const form = new FormData();
  form.append("file", file);
  return apiFetch(
    `/api/conversations/${conversationId}/messages/${messageId}/attachments/`,
    {
      method: "POST",
      headers: {},
      body: form,
    },
  );
}
