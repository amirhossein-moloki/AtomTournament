# Sitemap

This document outlines the URL structure of the tournament project's API.

## Main API Endpoints (`tournament_project/urls.py`)

- `/api/token/`: JWT Token Authentication
- `/api/token/refresh/`: Refresh JWT Token
- `/admin/`: Admin Panel
- `/api/select2/`: Django Select2
- `/api/schema/`: API Schema (drf-spectacular)
- `/api/schema/swagger-ui/`: Swagger UI
- `/api/schema/redoc/`: Redoc
- `/api/private-media/<path>`: Private Media
- `/api/editor/upload/`: CKEditor Upload

## Applications

### Users (`users/urls.py`)

- `/api/users/`: User list and creation
- `/api/users/<id>/`: User detail, update, delete
- `/api/users/<pk>/match-history/`: User match history
- `/api/roles/`: Role list and creation
- `/api/roles/<id>/`: Role detail, update, delete
- `/api/users/dashboard/`: Dashboard
- `/api/users/top-players/`: Top players
- `/api/users/top-players-by-rank/`: Top players by rank
- `/api/users/total-players/`: Total players
- `/api/users/auth/admin-login/`: Admin login
- `/api/users/auth/google/login/`: Google login

### Teams (`teams/urls.py`)

- `/api/teams/`: Team list and creation
- `/api/teams/<id>/`: Team detail, update, delete
- `/api/teams/<pk>/match-history/`: Team match history
- `/api/teams/top-teams/`: Top teams

### Tournaments (`tournaments/urls.py`)

- `/api/tournaments/`: Tournament list and creation
- `/api/tournaments/<id>/`: Tournament detail, update, delete
- `/api/tournaments/my-tournaments/`: My tournament history
- `/api/tournaments/admin/reports/`: Admin reports
- `/api/tournaments/admin/winner-submissions/`: Admin winner submissions
- `/api/tournaments/top-tournaments/`: Top tournaments
- `/api/tournaments/total-prize-money/`: Total prize money
- `/api/tournaments/total-tournaments/`: Total tournaments

### Chat (`chat/urls.py`)

- `/api/chat/conversations/`: Conversation list and creation
- `/api/chat/conversations/<id>/`: Conversation detail, update, delete
- `/api/chat/conversations/<conversation_pk>/messages/`: Message list and creation
- `/api/chat/conversations/<conversation_pk>/messages/<id>/`: Message detail, update, delete
- `/api/chat/conversations/<conversation_pk>/messages/<message_pk>/attachments/`: Attachment list and creation
- `/api/chat/conversations/<conversation_pk>/messages/<message_pk>/attachments/<id>/`: Attachment detail, update, delete
- `/api/chat/messages/`: Message list
- `/api/chat/messages/<id>/`: Message detail

### Wallet (`wallet/urls.py`)

- `/api/wallet/wallets/`: Wallet list and creation
- `/api/wallet/wallets/<id>/`: Wallet detail, update, delete
- `/api/wallet/transactions/`: Transaction list
- `/api/wallet/transactions/<id>/`: Transaction detail
- `/api/wallet/admin/withdrawal-requests/`: Admin withdrawal request list and creation
- `/api/wallet/admin/withdrawal-requests/<id>/`: Admin withdrawal request detail, update, delete
- `/api/wallet/deposit/`: Deposit
- `/api/wallet/verify-deposit/`: Verify deposit
- `/api/wallet/withdrawal-requests/`: Create withdrawal request
- `/api/wallet/refund/`: Refund
- `/api/wallet/admin/zibal-wallets/`: Zibal wallets

### Notifications (`notifications/urls.py`)

- `/api/notifications/`: Notification list and creation
- `/api/notifications/<id>/`: Notification detail, update, delete

### Support (`support/urls.py`)

- `/api/support/tickets/`: Ticket list and creation
- `/api/support/tickets/<id>/`: Ticket detail, update, delete
- `/api/support/tickets/<ticket_pk>/messages/`: Ticket message list and creation
- `/api/support/tickets/<ticket_pk>/messages/<id>/`: Ticket message detail, update, delete
- `/api/support/support-assignments/`: Support assignment list and creation
- `/api/support/support-assignments/<id>/`: Support assignment detail, update, delete

### Verification (`verification/urls.py`)

- `/api/verification/`: Verification list and creation
- `/api/verification/<id>/`: Verification detail, update, delete

### Rewards (`rewards/urls.py`)

- `/api/rewards/wheels/`: Wheel list and creation
- `/api/rewards/wheels/<id>/`: Wheel detail, update, delete
- `/api/rewards/spins/`: Spin list and creation
- `/api/rewards/spins/<id>/`: Spin detail, update, delete

### Reporting (`reporting/urls.py`)

- `/api/reporting/statistics/`: Statistics
- `/api/reporting/revenue/`: Revenue report
- `/api/reporting/players/`: Players report
- `/api/reporting/tournaments/`: Tournament report
- `/api/reporting/financial/`: Financial report
- `/api/reporting/marketing/`: Marketing report

### Management Dashboard (`management_dashboard/urls.py`)

- (No URLs currently active)

### AtomGameBot (`atomgamebot/urls.py`)

- `/api/atomgamebot/status/`: Bot status

### Blog (`blog/urls.py`)

- `/api/blog/posts/`: Post list and creation
- `/api/blog/posts/<slug>/`: Post detail, update, delete
- `/api/blog/posts/<slug>/publish/`: Publish post
- `/api/blog/posts/<slug>/related/`: Related posts
- `/api/blog/media/<media_id>/download/`: Download media
- `/api/blog/authors/`: Author list
- `/api/blog/authors/<id>/`: Author detail
- `/api/blog/categories/`: Category list
- `/api/blog/categories/<id>/`: Category detail
- `/api/blog/tags/`: Tag list
- `/api/blog/tags/<id>/`: Tag detail
- `/api/blog/series/`: Series list
- `/api/blog/series/<id>/`: Series detail
- `/api/blog/media/`: Media list
- `/api/blog/media/<id>/`: Media detail
- `/api/blog/revisions/`: Revision list
- `/api/blog/revisions/<id>/`: Revision detail
- `/api/blog/comments/`: Comment list
- `/api/blog/comments/<id>/`: Comment detail
- `/api/blog/reactions/`: Reaction list
- `/api/blog/reactions/<id>/`: Reaction detail
- `/api/blog/pages/`: Page list
- `/api/blog/pages/<id>/`: Page detail
- `/api/blog/menus/`: Menu list
- `/api/blog/menus/<id>/`: Menu detail
- `/api/blog/menu-items/`: Menu item list
- `/api/blog/menu-items/<id>/`: Menu item detail
