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

    // List Tournaments
    const tournamentsList = document.getElementById("tournaments-list");
    if (tournamentsList) {
        fetch("/api/tournaments/", { headers })
            .then(response => response.json())
            .then(data => {
                data.forEach(tournament => {
                    const li = document.createElement("li");
                    const a = document.createElement("a");
                    a.href = `/tournament-details.html?id=${tournament.id}`;
                    a.innerHTML = escapeHTML(tournament.name);
                    li.appendChild(a);
                    tournamentsList.appendChild(li);
                });
            });
    }

    // Tournament Details
    const tournamentName = document.getElementById("tournament-name");
    if (tournamentName) {
        const urlParams = new URLSearchParams(window.location.search);
        const tournamentId = urlParams.get("id");

        fetch(`/api/tournaments/${tournamentId}/`, { headers })
            .then(response => response.json())
            .then(data => {
                tournamentName.innerHTML = escapeHTML(data.name);
                document.getElementById("tournament-description").innerHTML = escapeHTML(data.description);
            });

        // Join Tournament
        const joinTournamentForm = document.getElementById("join-tournament-form");
        joinTournamentForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(joinTournamentForm);
            try {
                const response = await fetch(`/api/tournaments/${tournamentId}/join/`, {
                    method: "POST",
                    headers,
                });

                if (response.ok) {
                    alert("Successfully joined the tournament!");
                } else {
                    const errorData = await response.json();
                    for (const key in errorData) {
                        displayError(joinTournamentForm, `${key}: ${errorData[key]}`);
                    }
                }
            } catch (error) {
                console.error("Error joining tournament:", error);
                displayError(joinTournamentForm, "An error occurred while joining the tournament.");
            }
        });

        // Report Violation
        const reportViolationForm = document.getElementById("report-violation-form");
        reportViolationForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(reportViolationForm);
            const formData = new FormData(reportViolationForm);
            const data = Object.fromEntries(formData.entries());
            data.tournament = tournamentId;

            try {
                const response = await fetch("/api/reports/", {
                    method: "POST",
                    headers,
                    body: JSON.stringify(data),
                });

                if (response.ok) {
                    alert("Report submitted successfully!");
                } else {
                    const errorData = await response.json();
                    for (const key in errorData) {
                        displayError(reportViolationForm, `${key}: ${errorData[key]}`);
                    }
                }
            } catch (error) {
                console.error("Error submitting report:", error);
                displayError(reportViolationForm, "An error occurred while submitting the report.");
            }
        });

        // Winner Submission
        const winnerSubmissionForm = document.getElementById("winner-submission-form");
        winnerSubmissionForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(winnerSubmissionForm);
            const formData = new FormData(winnerSubmissionForm);
            const data = Object.fromEntries(formData.entries());
            data.tournament = tournamentId;

            try {
                const response = await fetch("/api/winner-submissions/", {
                    method: "POST",
                    headers,
                    body: JSON.stringify(data),
                });

                if (response.ok) {
                    alert("Winner submission successful!");
                } else {
                    const errorData = await response.json();
                    for (const key in errorData) {
                        displayError(winnerSubmissionForm, `${key}: ${errorData[key]}`);
                    }
                }
            } catch (error) {
                console.error("Error submitting winner video:", error);
                displayError(winnerSubmissionForm, "An error occurred while submitting the winner video.");
            }
        });
    }
});
