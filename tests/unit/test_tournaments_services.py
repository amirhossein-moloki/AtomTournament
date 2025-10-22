from datetime import timedelta

import pytest
from django.utils import timezone

from tournaments.models import Game, Tournament, Match
from tournaments.services import distribute_scores_for_tournament, get_tournament_winners
from users.models import Team, User


@pytest.fixture
def game():
    """Fixture to create a Game instance."""
    return Game.objects.create(name="Test Game")


@pytest.mark.django_db
def test_distribute_scores_individual(game):
    """
    Test the score distribution for an individual tournament using the service.
    """
    tournament = Tournament.objects.create(
        name="Test Tournament",
        game=game,
        start_date=timezone.now() + timedelta(days=1),
        end_date=timezone.now() + timedelta(days=2),
        type="individual",
    )
    p1 = User.objects.create_user(
        username="p1", password="p", phone_number="+1", score=100
    )
    p2 = User.objects.create_user(
        username="p2", password="p", phone_number="+2", score=100
    )
    tournament.top_players.add(p1, p2)

    initial_score_p1 = p1.score
    initial_score_p2 = p2.score

    distribute_scores_for_tournament(tournament)

    p1.refresh_from_db()
    p2.refresh_from_db()

    # Default distribution is [5, 4, 3, 2, 1]
    assert p1.score == initial_score_p1 + 5
    assert p2.score == initial_score_p2 + 4


@pytest.mark.django_db
def test_distribute_scores_team(game):
    """
    Test the score distribution for a team-based tournament.
    """
    tournament = Tournament.objects.create(
        name="Team Tournament",
        game=game,
        start_date=timezone.now() + timedelta(days=1),
        end_date=timezone.now() + timedelta(days=2),
        type="team",
    )
    captain1 = User.objects.create_user(
        username="c1", password="p", phone_number="+10", score=50
    )
    member1 = User.objects.create_user(
        username="m1", password="p", phone_number="+11", score=50
    )
    team1 = Team.objects.create(name="Team 1", captain=captain1)
    team1.members.add(member1)

    captain2 = User.objects.create_user(
        username="c2", password="p", phone_number="+20", score=50
    )
    team2 = Team.objects.create(name="Team 2", captain=captain2)

    tournament.top_teams.add(team1, team2)

    distribute_scores_for_tournament(tournament)

    captain1.refresh_from_db()
    member1.refresh_from_db()
    captain2.refresh_from_db()

    assert captain1.score == 50 + 5
    assert member1.score == 50 + 5  # Both members get points
    assert captain2.score == 50 + 4


@pytest.mark.django_db
def test_get_tournament_winners_team_duel(game):
    """Test that a team duel returns only the champion."""
    tournament = Tournament.objects.create(
        name="Duel",
        game=game,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=1),
        type="team",
        team_size=5,
    )
    captain_a = User.objects.create_user(
        username="captain_a", password="p", phone_number="+600"
    )
    captain_b = User.objects.create_user(
        username="captain_b", password="p", phone_number="+601"
    )
    team_a = Team.objects.create(name="Alpha", captain=captain_a)
    team_b = Team.objects.create(name="Beta", captain=captain_b)
    tournament.teams.add(team_a, team_b)

    Match.objects.create(
        tournament=tournament,
        match_type="team",
        round=1,
        participant1_team=team_a,
        participant2_team=team_b,
        winner_team=team_a,
        is_confirmed=True,
    )

    winners = list(get_tournament_winners(tournament))
    assert winners == [team_a]
