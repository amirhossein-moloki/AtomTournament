document.addEventListener('DOMContentLoaded', async () => {
    const accessToken = localStorage.getItem('accessToken');

    if (!accessToken) {
        // No token found, redirect to login page
        window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch('/api/users/dashboard/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`,
            },
        });

        if (response.ok) {
            const data = await response.json();
            populateDashboard(data);
        } else if (response.status === 401) {
            // Unauthorized, token might be invalid or expired
            alert('Your session has expired. Please log in again.');
            localStorage.removeItem('accessToken');
            window.location.href = 'login.html';
        } else {
            // Handle other errors
            console.error('Failed to fetch dashboard data:', response.status);
            alert('Failed to load dashboard data.');
        }
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
        alert('An error occurred while loading the dashboard.');
    }

    // Logout functionality
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('accessToken');
            window.location.href = 'login.html';
        });
    }
});

function populateDashboard(data) {
    // --- Populate User Profile ---
    const user = data.user_profile; // Assuming the API returns a 'user_profile' object
    if (user) {
        document.querySelectorAll('.user-name').forEach(el => el.textContent = user.username);
        document.getElementById('user-email').textContent = user.email;
        if(user.rank) {
            document.getElementById('user-rank').textContent = user.rank.name;
        }

        const avatarElements = document.querySelectorAll('.user-avatar');
        if (user.verification && user.verification.profile_picture) {
            avatarElements.forEach(el => el.style.backgroundImage = `url('${user.verification.profile_picture.url}')`);
        }

        document.getElementById('stats-points').textContent = user.score || '0';
        const joinDate = new Date(user.date_joined);
        document.getElementById('stats-date').innerHTML = `${joinDate.getFullYear()} <span class="text-base">${joinDate.getMonth() + 1}</span> ${joinDate.getDate()}`;
    }

    // --- Populate Teams ---
    const teams = data.teams || [];
    const teamsContainer = document.getElementById('teams-container');
    if (teamsContainer) {
        teamsContainer.innerHTML = ''; // Clear placeholders
        if (teams.length > 0) {
            teams.forEach(team => {
                const teamElement = `
                    <div class="flex items-center justify-between bg-gray-900 p-4 rounded-lg">
                        <div class="flex items-center">
                            <div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center mr-4">
                                <span class="text-2xl font-bold">${team.name.charAt(0)}</span>
                            </div>
                            <div>
                                <p class="font-bold">${team.name}</p>
                                <p class="text-sm text-gray-400">${team.members_count} عضو</p>
                            </div>
                        </div>
                        <div class="flex items-center space-x-2">
                            ${team.is_captain ? `
                                <button class="text-gray-400 hover:text-white"><i class="fas fa-users"></i></button>
                                <button class="text-gray-400 hover:text-white"><i class="fas fa-edit"></i></button>
                                <button class="text-gray-400 hover:text-white"><i class="fas fa-trash"></i></button>
                            ` : ''}
                            <button class="text-gray-400 hover:text-white"><i class="fas fa-sign-in-alt transform rotate-180"></i></button>
                        </div>
                    </div>
                `;
                teamsContainer.innerHTML += teamElement;
            });
        } else {
            teamsContainer.innerHTML = '<p class="text-gray-400">شما در هیچ تیمی عضو نیستید.</p>';
        }
        document.getElementById('stats-teams').textContent = teams.length;
    }

    // --- Populate Tournament History ---
    const history = data.tournament_history || [];
    const historyBody = document.getElementById('tournament-history-body');
    if (historyBody) {
        historyBody.innerHTML = ''; // Clear placeholders
        if (history.length > 0) {
            history.forEach(item => {
                const row = `
                    <tr class="border-b border-gray-700">
                        <td class="py-4 px-2">${item.tournament.title}</td>
                        <td class="py-4 px-2">${item.tournament.game.name}</td>
                        <td class="py-4 px-2">${item.team ? item.team.name : 'انفرادی'}</td>
                        <td class="py-4 px-2">${new Date(item.tournament.start_date).toLocaleDateString('fa-IR')}</td>
                        <td class="py-4 px-2">${item.final_rank || '-'}</td>
                        <td class="py-4 px-2 text-green-400">+${item.tournament.prize_pool || '0'}</td>
                    </tr>
                `;
                historyBody.innerHTML += row;
            });
        } else {
            historyBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-400">شما در هیچ تورنومنتی شرکت نکرده‌اید.</td></tr>';
        }
        document.getElementById('stats-tournaments').textContent = history.length;
    }
}
