document.addEventListener("DOMContentLoaded", async () => {
    const token = localStorage.getItem("accessToken");
    if (!token) {
        window.location.href = "/login.html";
        return;
    }

    try {
        const response = await fetch("/api/users/dashboard/", {
            headers: {
                "Authorization": `Bearer ${token}`,
            },
        });

        if (response.ok) {
            const data = await response.json();
            displayDashboardData(data);
        } else {
            alert("Failed to fetch dashboard data.");
        }
    } catch (error) {
        console.error("Error fetching dashboard data:", error);
        alert("An error occurred while fetching dashboard data.");
    }
});

function displayDashboardData(data) {
    const upcomingTournaments = document.getElementById("upcoming-tournaments");
    data.upcoming_tournaments.forEach(tournament => {
        const li = document.createElement("li");
        li.innerHTML = escapeHTML(tournament.name);
        upcomingTournaments.appendChild(li);
    });

    const sentInvitations = document.getElementById("sent-invitations");
    data.sent_invitations.forEach(invitation => {
        const li = document.createElement("li");
        li.innerHTML = `To: ${escapeHTML(invitation.to_user)} for team ${escapeHTML(invitation.team)}`;
        sentInvitations.appendChild(li);
    });

    const receivedInvitations = document.getElementById("received-invitations");
    data.received_invitations.forEach(invitation => {
        const li = document.createElement("li");
        li.innerHTML = `From: ${escapeHTML(invitation.from_user)} for team ${escapeHTML(invitation.team)}`;
        receivedInvitations.appendChild(li);
    });

    const latestTransactions = document.getElementById("latest-transactions");
    data.latest_transactions.forEach(transaction => {
        const li = document.createElement("li");
        li.innerHTML = `${escapeHTML(transaction.amount)} - ${escapeHTML(transaction.description)}`;
        latestTransactions.appendChild(li);
    });
}
