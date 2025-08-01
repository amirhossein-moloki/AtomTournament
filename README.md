# Tournament Management System

This is a Django-based tournament management system that allows users to create and manage tournaments, participate in matches, and interact with other users through a built-in chat system. The project also includes a wallet system for managing tournament entry fees and prizes.

## Features

*   **Tournament Management:** Create, edit, and delete tournaments. Support for both individual and team-based tournaments.
*   **Match Management:** Automatic match generation, result confirmation, and dispute resolution.
*   **User Management:** User registration, authentication, and profile management. Role-based access control (admin, user).
*   **Team Management:** Create and manage teams, add or remove members.
*   **Wallet System:** Manage user wallets, including deposits, withdrawals, entry fees, and prize money.
*   **Chat System:** Real-time chat between users.
*   **Notification System:** Real-time notifications for users.
*   **API Documentation:** Automatically generated API documentation using `drf-spectacular`.

## Getting Started

### Prerequisites

*   Python 3.8+
*   PostgreSQL 12+
*   Redis

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/tournament-project.git
    cd tournament-project
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the environment variables:**

    Copy the example environment file and fill in your details.

    ```bash
    cp env.example .env
    ```

    You must set the `SECRET_KEY` and `DATABASE_URL` for your local PostgreSQL instance. The other variables have sensible defaults for local development.

    **Example `.env`:**
    ```
    SECRET_KEY="your-super-secret-key-here"
    DEBUG=True
    DATABASE_URL="postgres://user:password@localhost:5432/tournament_db"
    REDIS_URL="redis://localhost:6379/0"
    ```

5.  **Run the database migrations:**

    ```bash
    python tournament_project/manage.py migrate
    ```

6.  **Create a superuser:**

    ```bash
    python tournament_project/manage.py createsuperuser
    ```

7.  **Run the development server:**

    ```bash
    python tournament_project/manage.py runserver
    ```

The API will be available at `http://127.0.0.1:8000/api/`.

### API Documentation

The API documentation is available at `http://127.0.0.1:8000/api/docs/`.

## Project Structure

```
.
├── chat/                 # Chat application
├── notifications/        # Notifications application
├── tournament_project/   # Django project
│   ├── tournaments/      # Tournaments application
│   ├── users/            # Users application
│   └── wallet/           # Wallet application
├── .github/              # GitHub Actions workflows
├── requirements.txt      # Python dependencies
├── websockets.md         # WebSocket usage guide
└── README.md
```

## Contributing

Contributions are welcome! Please read the `CONTRIBUTING.md` file for more information.
