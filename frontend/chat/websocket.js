const WS_BASE = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

export function createChatSocket(conversationId, { onEvent, onStatus }) {
  const socket = new WebSocket(`${WS_BASE}/ws/chat/${conversationId}/`);

  onStatus?.("connecting");

  socket.onopen = () => onStatus?.("open");
  socket.onclose = () => onStatus?.("closed");
  socket.onerror = () => onStatus?.("error");
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onEvent?.(data);
  };

  return socket;
}

export function sendChatMessage(socket, content) {
  socket?.send(
    JSON.stringify({
      type: "chat_message",
      message: content,
    }),
  );
}

export function emitTypingSignal(socket, isTyping) {
  socket?.send(
    JSON.stringify({
      type: "typing",
      is_typing: isTyping,
    }),
  );
}

export function sendEdit(socket, messageId, content) {
  socket?.send(
    JSON.stringify({
      type: "edit_message",
      message_id: messageId,
      content,
    }),
  );
}

export function sendDelete(socket, messageId) {
  socket?.send(
    JSON.stringify({
      type: "delete_message",
      message_id: messageId,
    }),
  );
}
