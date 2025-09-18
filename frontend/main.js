document.addEventListener('DOMContentLoaded', () => {
    const mockData = {
        user: {
            username: "Test User",
            email: "test.user@example.com",
            level_up_progress: "ارتقاع به سطح 3",
            avatar_url: "https://i.pravatar.cc/150?u=a042581f4e29026704d",
            stats: {
                points: "3,120",
                tournaments_played: 15,
                team_count: 4,
                member_since: "2024-01-15"
            }
        },
        teams: [
            {
                name: "Alpha Wolves",
                member_count: 5,
                avatar_char: "A",
                is_admin: true
            },
            {
                name: "Cyber Dragons",
                member_count: 4,
                avatar_char: "C",
                is_admin: false
            },
            {
                name: "Pixel Predators",
                member_count: 4,
                avatar_char: "P",
                is_admin: false
            }
        ],
        tournament_history: [
            {
                name: "تورنومنت قهرمانی ایران",
                game: "CS:GO",
                team: "Alpha Wolves",
                date: "1404/03/20",
                rank: "رتبه اول",
                points: "+1500"
            },
            {
                name: "جام بزرگ تهران",
                game: "FORTNITE",
                team: "Cyber Dragons",
                date: "1404/02/13",
                rank: "رتبه سوم",
                points: "+800"
            },
            {
                name: "مسابقه آنلاین هفتگی",
                game: "Valorant",
                team: "Alpha Wolves",
                date: "1404/01/28",
                rank: "رتبه دوم",
                points: "+1000"
            }
        ]
    };

    // --- Element Selectors ---
    const usernameElements = document.querySelectorAll('.user-name');
    const userEmailElement = document.getElementById('user-email');
    const userAvatarElements = document.querySelectorAll('.user-avatar');
    const profileStats = {
        points: document.getElementById('stats-points'),
        tournaments: document.getElementById('stats-tournaments'),
        teams: document.getElementById('stats-teams'),
        date: document.getElementById('stats-date')
    };
    const teamsContainer = document.getElementById('teams-container');
    const tournamentHistoryBody = document.getElementById('tournament-history-body');

    // --- Data Population Functions ---

    function populateProfile() {
        if (!userEmailElement) return; // Exit if elements are not on the page

        usernameElements.forEach(el => el.textContent = mockData.user.username);
        userEmailElement.textContent = mockData.user.email;

        userAvatarElements.forEach(el => {
            if(el.tagName === 'IMG') {
                el.src = mockData.user.avatar_url;
            } else {
                el.style.backgroundImage = `url('${mockData.user.avatar_url}')`;
            }
        });

        profileStats.points.textContent = mockData.user.stats.points;
        profileStats.tournaments.textContent = mockData.user.stats.tournaments_played;
        profileStats.teams.textContent = mockData.user.stats.team_count;

        const joinDate = new Date(mockData.user.member_since);
        profileStats.date.innerHTML = `${joinDate.getFullYear()} <span class="text-base">${joinDate.getMonth() + 1}</span> ${joinDate.getDate()}`;
    }

    function populateTeams() {
        if (!teamsContainer) return;
        teamsContainer.innerHTML = ''; // Clear existing content

        mockData.teams.forEach(team => {
            const adminButtons = `
                <button class="text-gray-400 hover:text-white"><i class="fas fa-users"></i></button>
                <button class="text-gray-400 hover:text-white"><i class="fas fa-edit"></i></button>
                <button class="text-gray-400 hover:text-white"><i class="fas fa-trash"></i></button>
            `;
            const memberButtons = `<button class="text-gray-400 hover:text-white"><i class="fas fa-sign-in-alt transform rotate-180"></i></button>`;

            const teamElement = `
                <div class="flex items-center justify-between bg-gray-900 p-4 rounded-lg">
                    <div class="flex items-center">
                        <div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center mr-4">
                            <span class="text-2xl font-bold">${team.avatar_char}</span>
                        </div>
                        <div>
                            <p class="font-bold">${team.name}</p>
                            <p class="text-sm text-gray-400">${team.member_count} عضو</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        ${team.is_admin ? adminButtons : ''}
                        ${memberButtons}
                    </div>
                </div>
            `;
            teamsContainer.innerHTML += teamElement;
        });
    }

    function populateTournamentHistory() {
        if (!tournamentHistoryBody) return;
        tournamentHistoryBody.innerHTML = ''; // Clear existing content

        mockData.tournament_history.forEach(tourney => {
            const row = `
                <tr class="border-b border-gray-700">
                    <td class="py-4 px-2">${tourney.name}</td>
                    <td class="py-4 px-2">${tourney.game}</td>
                    <td class="py-4 px-2">${tourney.team}</td>
                    <td class="py-4 px-2">${tourney.date}</td>
                    <td class="py-4 px-2">${tourney.rank}</td>
                    <td class="py-4 px-2 text-green-400">${tourney.points}</td>
                </tr>
            `;
            tournamentHistoryBody.innerHTML += row;
        });
    }

    // --- Initial Population ---
    populateProfile();
    populateTeams();
    populateTournamentHistory();
});
