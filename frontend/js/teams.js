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

    // Create Team Form
    const createTeamForm = document.getElementById("create-team-form");
    if (createTeamForm) {
        createTeamForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(createTeamForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch("/api/teams/", {
                    method: "POST",
                    headers,
                    body: JSON.stringify(data),
                });

                if (response.ok) {
                    alert("Team created successfully!");
                    window.location.reload();
                } else {
                    const errorData = await response.json();
                    for (const key in errorData) {
                        displayError(createTeamForm, `${key}: ${errorData[key]}`);
                    }
                }
            } catch (error) {
                console.error("Error creating team:", error);
                displayError(createTeamForm, "An error occurred while creating the team.");
            }
        });
    }

    // List Teams
    const teamsList = document.getElementById("teams-list");
    if (teamsList) {
        fetch("/api/teams/", { headers })
            .then(response => response.json())
            .then(data => {
                data.forEach(team => {
                    const li = document.createElement("li");
                    const a = document.createElement("a");
                    a.href = `/team-details.html?id=${team.id}`;
                    a.innerHTML = escapeHTML(team.name);
                    li.appendChild(a);
                    teamsList.appendChild(li);
                });
            });
    }

    // Team Details
    const teamName = document.getElementById("team-name");
    if (teamName) {
        const urlParams = new URLSearchParams(window.location.search);
        const teamId = urlParams.get("id");

        fetch(`/api/teams/${teamId}/`, { headers })
            .then(response => response.json())
            .then(data => {
                teamName.innerHTML = escapeHTML(data.name);
                const teamMembers = document.getElementById("team-members");
                data.members.forEach(member => {
                    const li = document.createElement("li");
                    li.innerHTML = escapeHTML(member.username);
                    teamMembers.appendChild(li);
                });
            });

        // Invite Member
        const inviteMemberForm = document.getElementById("invite-member-form");
        inviteMemberForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(inviteMemberForm);
            const formData = new FormData(inviteMemberForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch(`/api/teams/${teamId}/invite_member/`, {
                    method: "POST",
                    headers,
                    body: JSON.stringify(data),
                });

                if (response.ok) {
                    alert("Invitation sent successfully!");
                } else {
                    const errorData = await response.json();
                    for (const key in errorData) {
                        displayError(inviteMemberForm, `${key}: ${errorData[key]}`);
                    }
                }
            } catch (error) {
                console.error("Error sending invitation:", error);
                displayError(inviteMemberForm, "An error occurred while sending the invitation.");
            }
        });

        // Leave Team
        const leaveTeamBtn = document.getElementById("leave-team-btn");
        leaveTeamBtn.addEventListener("click", async () => {
            try {
                const response = await fetch(`/api/teams/${teamId}/leave_team/`, {
                    method: "POST",
                    headers,
                });

                if (response.ok) {
                    alert("You have left the team.");
                    window.location.href = "/teams.html";
                } else {
                    alert("Failed to leave team.");
                }
            } catch (error) {
                console.error("Error leaving team:", error);
                alert("An error occurred while leaving the team.");
            }
        });
    }

    // Respond to Invitation
    const respondInvitationForm = document.getElementById("respond-invitation-form");
    if (respondInvitationForm) {
        respondInvitationForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearErrors(respondInvitationForm);
            const formData = new FormData(respondInvitationForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch("/api/teams/respond-invitation/", {
                    method: "POST",
                    headers,
                    body: JSON.stringify(data),
                });

                if (response.ok) {
                    alert("Responded to invitation successfully!");
                } else {
                    const errorData = await response.json();
                    for (const key in errorData) {
                        displayError(respondInvitationForm, `${key}: ${errorData[key]}`);
                    }
                }
            } catch (error) {
                console.error("Error responding to invitation:", error);
                displayError(respondInvitationForm, "An error occurred while responding to the invitation.");
            }
        });
    }
});
