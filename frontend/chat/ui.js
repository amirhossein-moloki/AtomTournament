export const elements = {
  loginForm: document.getElementById("login-form"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  logout: document.getElementById("logout-btn"),
  reloadConversations: document.getElementById("reload-conversations"),
  userIndicator: document.getElementById("user-indicator"),
  conversationList: document.getElementById("conversations"),
  conversationCount: document.getElementById("conversation-count"),
  messageList: document.getElementById("messages"),
  messageForm: document.getElementById("message-form"),
  messageInput: document.getElementById("message-input"),
  typingBtn: document.getElementById("typing-btn"),
  typingIndicator: document.getElementById("typing-indicator"),
  wsStatusDot: document.getElementById("ws-status"),
  wsStatusText: document.getElementById("ws-text"),
  activeConversationTitle: document.getElementById("active-conversation-title"),
  newConversationForm: document.getElementById("new-conversation-form"),
  recipientId: document.getElementById("recipient-id"),
  initialMessage: document.getElementById("initial-message"),
  messageTemplate: document.getElementById("message-template"),
};

export function updateUserIndicator(user) {
  if (user) {
    elements.userIndicator.textContent = `ورود با ${user.username} (شناسه ${user.id})`;
    elements.userIndicator.style.color = "#34d399";
  } else {
    elements.userIndicator.textContent = "وضعیت ورود: نامشخص";
    elements.userIndicator.style.color = "#e5e7eb";
  }
}

export function renderConversations(conversations, activeConversationId, onSelect) {
  elements.conversationList.innerHTML = "";
  elements.conversationCount.textContent = conversations.length;
  conversations.forEach((conversation) => {
    const item = document.createElement("div");
    item.className = "conversation-item";
    if (activeConversationId === conversation.id) {
      item.classList.add("active");
    }
    item.innerHTML = `
      <p class="conversation-title">مکالمه #${conversation.id}</p>
      <p class="conversation-meta">
        <span>${conversation.participants.map((p) => p.username).join("، ")}</span>
        <span>${conversation.last_message ? new Date(conversation.last_message.timestamp).toLocaleString("fa-IR") : "بدون پیام"}</span>
      </p>
    `;
    item.addEventListener("click", () => onSelect(conversation.id));
    elements.conversationList.appendChild(item);
  });
}

export function renderMessages(messages, currentUserId, handlers) {
  elements.messageList.innerHTML = "";

  messages.forEach((message) => {
    const clone = elements.messageTemplate.content.cloneNode(true);
    const article = clone.querySelector(".message-item");
    if (message.is_deleted) article.classList.add("deleted");

    clone.querySelector(".sender").textContent = message.sender.username;
    clone.querySelector(".timestamp").textContent = new Date(
      message.timestamp,
    ).toLocaleString("fa-IR");
    clone.querySelector(".message-content").textContent = message.is_deleted
      ? "این پیام حذف شده است"
      : message.content;

    const attachmentsContainer = clone.querySelector(".attachments");
    if (message.attachments?.length) {
      message.attachments.forEach((att) => {
        const pill = document.createElement("a");
        pill.href = att.file;
        pill.target = "_blank";
        pill.rel = "noopener noreferrer";
        pill.textContent = `فایل #${att.id}`;
        pill.className = "attachment-pill";
        attachmentsContainer.appendChild(pill);
      });
    }

    const isOwner = message.sender.id === currentUserId;
    const editBtn = clone.querySelector(".edit-btn");
    const deleteBtn = clone.querySelector(".delete-btn");
    const attachInput = clone.querySelector(".attach-input");
    const attachLabel = clone.querySelector(".attach-label");

    if (!isOwner) {
      editBtn.style.display = "none";
      deleteBtn.style.display = "none";
      attachLabel.style.display = "none";
    } else {
      editBtn.addEventListener("click", () => handlers.onEdit(message.id));
      deleteBtn.addEventListener("click", () => handlers.onDelete(message.id));
      attachInput.addEventListener("change", (event) => {
        const file = event.target.files?.[0];
        if (file) handlers.onAttach(message.id, file);
      });
    }

    elements.messageList.appendChild(clone);
  });
}

export function setActiveConversationTitle(title) {
  elements.activeConversationTitle.textContent = title;
}

export function setTypingIndicator(text) {
  elements.typingIndicator.textContent = text || "\u00a0";
}

export function setWsStatus(status) {
  const colorMap = {
    connecting: "#fbbf24",
    open: "#34d399",
    closed: "#ef4444",
    error: "#ef4444",
  };
  const textMap = {
    connecting: "اتصال...",
    open: "متصل",
    closed: "غیرفعال",
    error: "خطا در اتصال",
  };

  elements.wsStatusDot.style.background = colorMap[status] || "#ef4444";
  elements.wsStatusText.textContent = textMap[status] || "غیرفعال";
}
