export const state = {
  token: localStorage.getItem("access_token") || null,
  currentUser: null,
  conversations: [],
  activeConversation: null,
  messages: [],
};

export function setToken(token) {
  state.token = token;
  if (token) {
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
}

export function resetSession() {
  setToken(null);
  state.currentUser = null;
  state.conversations = [];
  state.activeConversation = null;
  state.messages = [];
}
