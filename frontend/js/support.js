document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("accessToken");
    if (!token) {
        window.location.href = "/login.html";
        return;
    }

    const csrftoken = getCookie('csrftoken');
    const headers = {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken,
    };

    // Create Ticket Form
    const createTicketForm = document.getElementById("create-ticket-form");
    if (createTicketForm) {
        createTicketForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(createTicketForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch("/api/support/tickets/", {
                    method: "POST",
                    headers,
                    body: JSON.stringify(data),
                });

                if (response.ok) {
                    alert("Ticket created successfully!");
                    window.location.reload();
                } else {
                    const errorData = await response.json();
                    for (const key in errorData) {
                        displayError(createTicketForm, `${key}: ${errorData[key]}`);
                    }
                }
            } catch (error) {
                console.error("Error creating ticket:", error);
                displayError(createTicketForm, "An error occurred while creating the ticket.");
            }
        });
    }

    // List Tickets
    const ticketsList = document.getElementById("tickets-list");
    if (ticketsList) {
        fetch("/api/support/tickets/", { headers })
            .then(response => response.json())
            .then(data => {
                data.forEach(ticket => {
                    const li = document.createElement("li");
                    const a = document.createElement("a");
                    a.href = `/ticket-details.html?id=${ticket.id}`;
                    a.innerHTML = escapeHTML(ticket.title);
                    li.appendChild(a);
                    ticketsList.appendChild(li);
                });
            });
    }

    // Ticket Details
    const ticketTitle = document.getElementById("ticket-title");
    if (ticketTitle) {
        const urlParams = new URLSearchParams(window.location.search);
        const ticketId = urlParams.get("id");

        fetch(`/api/support/tickets/${ticketId}/`, { headers })
            .then(response => response.json())
            .then(data => {
                ticketTitle.innerHTML = escapeHTML(data.title);
            });

        const ticketMessages = document.getElementById("ticket-messages");
        fetch(`/api/support/tickets/${ticketId}/messages/`, { headers })
            .then(response => response.json())
            .then(data => {
                data.forEach(message => {
                    const p = document.createElement("p");
                    p.innerHTML = `${escapeHTML(message.sender)}: ${escapeHTML(message.text)}`;
                    ticketMessages.appendChild(p);
                });
            });

        // Send Message
        const sendMessageForm = document.getElementById("send-message-form");
        sendMessageForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(sendMessageForm);
            const formData = new FormData(sendMessageForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch(`/api/support/tickets/${ticketId}/messages/`, {
                    method: "POST",
                    headers,
                    body: JSON.stringify(data),
                });

                if (response.ok) {
                    window.location.reload();
                } else {
                    const errorData = await response.json();
                    for (const key in errorData) {
                        displayError(sendMessageForm, `${key}: ${errorData[key]}`);
                    }
                }
            } catch (error) {
                console.error("Error sending message:", error);
                displayError(sendMessageForm, "An error occurred while sending the message.");
            }
        });
    }
});
