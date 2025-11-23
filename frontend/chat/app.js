import { createConversation, fetchConversations, fetchCurrentUser, fetchMessages, loginUser, uploadAttachment } from "./api.js";
import { state, resetSession } from "./state.js";
import {
  elements,
  renderConversations,
  renderMessages,
  setActiveConversationTitle,
  setTypingIndicator,
  setWsStatus,
  updateUserIndicator,
} from "./ui.js";
import {
  createChatSocket,
  emitTypingSignal,
  sendChatMessage,
  sendDelete,
  sendEdit,
} from "./websocket.js";

let websocket = null;
let typingTimeout = null;

async function handleLogin(event) {
  event.preventDefault();
  try {
    await loginUser(elements.username.value, elements.password.value);
    await hydrateUser();
  } catch (error) {
    alert(error.message);
  }
}

function handleLogout() {
  resetSession();
  closeSocket();
  renderConversations([], null, () => {});
  renderMessages([], null, blankHandlers());
  updateUserIndicator(null);
  setActiveConversationTitle("هیچ مکالمه‌ای انتخاب نشده است");
  setTypingIndicator("");
  setWsStatus("closed");
}

async function hydrateUser() {
  try {
    await fetchCurrentUser();
    updateUserIndicator(state.currentUser);
    await loadConversations();
  } catch (error) {
    updateUserIndicator(null);
    alert(error.message);
  }
}

async function loadConversations() {
  if (!state.token) return;
  try {
    await fetchConversations();
    renderConversations(state.conversations, state.activeConversation?.id, selectConversation);
  } catch (error) {
    alert(error.message);
  }
}

async function selectConversation(id) {
  const conversation = state.conversations.find((c) => c.id === id);
  if (!conversation) return;

  state.activeConversation = conversation;
  setActiveConversationTitle(`مکالمه #${conversation.id}`);
  await loadMessages(conversation.id);
  openSocket(conversation.id);
}

async function loadMessages(conversationId) {
  try {
    state.messages = await fetchMessages(conversationId);
    renderMessages(
      state.messages,
      state.currentUser?.id,
      messageHandlers(),
    );
  } catch (error) {
    alert(error.message);
  }
}

function openSocket(conversationId) {
  closeSocket();
  websocket = createChatSocket(conversationId, {
    onEvent: handleSocketEvent,
    onStatus: setWsStatus,
  });
}

function closeSocket() {
  if (websocket) {
    websocket.close();
    websocket = null;
  }
}

function handleSocketEvent(data) {
  if (data.type === "user.typing") {
    setTypingIndicator(data.is_typing ? `${data.user} در حال تایپ است...` : "");
    return;
  }

  if (data.type === "message.edited") {
    const index = state.messages.findIndex((m) => m.id === data.message.id);
    if (index >= 0) {
      state.messages[index].content = data.message.content;
      state.messages[index].is_edited = true;
      renderMessages(state.messages, state.currentUser?.id, messageHandlers());
    }
    return;
  }

  if (data.type === "message.deleted") {
    const index = state.messages.findIndex((m) => m.id === data.message_id);
    if (index >= 0) {
      state.messages[index].is_deleted = true;
      renderMessages(state.messages, state.currentUser?.id, messageHandlers());
    }
    return;
  }

  if (data.id && data.sender) {
    const senderId =
      data.sender === state.currentUser?.username ? state.currentUser.id : null;
    state.messages.push({
      ...data,
      sender: { id: senderId, username: data.sender },
      is_deleted: false,
      is_edited: false,
    });
    renderMessages(state.messages, state.currentUser?.id, messageHandlers());
  }
}

function sendMessage(event) {
  event.preventDefault();
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    alert("اتصال وب‌ساکت برقرار نیست");
    return;
  }
  const content = elements.messageInput.value.trim();
  if (!content) return;
  sendChatMessage(websocket, content);
  elements.messageInput.value = "";
}

function emitTyping() {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
  emitTypingSignal(websocket, true);
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => emitTypingSignal(websocket, false), 1200);
}

function editMessage(messageId) {
  const current = state.messages.find((m) => m.id === messageId);
  const newContent = prompt("محتوای جدید پیام را وارد کنید", current?.content || "");
  if (!newContent || !websocket) return;
  sendEdit(websocket, messageId, newContent);
}

function deleteMessage(messageId) {
  if (!websocket) return;
  const confirmed = confirm("آیا از حذف پیام مطمئن هستید؟");
  if (!confirmed) return;
  sendDelete(websocket, messageId);
}

async function handleAttachment(messageId, file) {
  if (!state.activeConversation) return;
  try {
    await uploadAttachment(state.activeConversation.id, messageId, file);
    await loadMessages(state.activeConversation.id);
  } catch (error) {
    alert("آپلود فایل انجام نشد");
    console.error(error);
  }
}

async function handleConversationCreation(event) {
  event.preventDefault();
  if (!state.token) {
    alert("ابتدا وارد شوید");
    return;
  }
  try {
    const recipientId = Number(elements.recipientId.value);
    await createConversation(recipientId, elements.initialMessage.value);
    elements.initialMessage.value = "";
    elements.recipientId.value = "";
    await loadConversations();
    const [newConversation] = state.conversations
      .filter((c) => c.participants.some((p) => p.id === recipientId))
      .sort((a, b) => b.id - a.id);
    if (newConversation) selectConversation(newConversation.id);
  } catch (error) {
    alert(error.message);
  }
}

function bindEvents() {
  elements.loginForm.addEventListener("submit", handleLogin);
  elements.logout.addEventListener("click", handleLogout);
  elements.reloadConversations.addEventListener("click", loadConversations);
  elements.messageForm.addEventListener("submit", sendMessage);
  elements.typingBtn.addEventListener("click", emitTyping);
  elements.messageInput.addEventListener("input", emitTyping);
  elements.newConversationForm.addEventListener(
    "submit",
    handleConversationCreation,
  );
}

function blankHandlers() {
  return { onEdit: () => {}, onDelete: () => {}, onAttach: () => {} };
}

function messageHandlers() {
  return {
    onEdit: editMessage,
    onDelete: deleteMessage,
    onAttach: handleAttachment,
  };
}

async function bootstrap() {
  bindEvents();
  updateUserIndicator(state.currentUser);
  setWsStatus("closed");
  if (state.token) {
    await hydrateUser();
  }
}

bootstrap();
