# WebSocket Usage Guide

This guide explains how to use WebSockets in this project for real-time features like chat and notifications.

## Connecting to WebSockets

To connect to a WebSocket, you need to use a WebSocket client library (e.g., `socket.io-client` for JavaScript). The WebSocket URL is `ws://<your-domain>/ws/<endpoint>/`.

### Endpoints

*   `/ws/chat/<conversation_id>/`: For real-time chat in a conversation.
*   `/ws/notifications/`: For real-time notifications for the authenticated user.

### Authentication

To authenticate with a WebSocket, you need to include the user's authentication token in the connection URL as a query parameter.

**Example:**

```
ws://<your-domain>/ws/notifications/?token=<your-auth-token>
```

## Chat WebSocket

### Sending Messages

To send a message in a conversation, send a JSON object with the following structure to the chat WebSocket:

```json
{
  "message": "Your message content"
}
```

### Receiving Messages

When a new message is sent in the conversation, you will receive a JSON object with the following structure from the chat WebSocket:

```json
{
  "id": 123,
  "sender": {
    "id": 1,
    "username": "testuser"
  },
  "content": "The message content",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Notifications WebSocket

### Receiving Notifications

When a new notification is available for the authenticated user, you will receive a JSON object with the following structure from the notifications WebSocket:

```json
{
  "id": 1,
  "message": "The notification message",
  "is_read": false,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Marking Notifications as Read

To mark a notification as read, you need to send a request to the REST API, not through the WebSocket.
