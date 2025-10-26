"""
Tests for the tournament services in tournaments/services.py.
These tests cover the business logic for creating, managing,
and advancing tournaments.
"""
import pytest
from unittest.mock import patch, call
from tournaments.services import (
    join_tournament,
    generate_matches,
    confirm_match_result,
    advance_to_next_round,
    get_tournament_winners,
)
from tournaments.models import Tournament, Match, Participant
from tournaments.exceptions import ApplicationError
from users.models import Team
from verification.models import Verification


from datetime import timedelta
from django.utils import timezone
from tournaments.models import Game

@pytest.fixture
def game(db):
    """Creates a dummy game."""
    return Game.objects.create(name="Test Game")


@pytest.fixture
def individual_tournament(db, game):
    """Creates a standard individual tournament."""
    return Tournament.objects.create(
        name="Individual Showdown",
        type="individual",
        game=game,
        max_participants=4,
        entry_fee=100,
        is_free=False,
        required_verification_level=1,
        start_date=timezone.now() + timedelta(days=1),
        end_date=timezone.now() + timedelta(days=2),
    )


@pytest.fixture
def team_tournament(db, game):
    """Creates a standard team tournament."""
    return Tournament.objects.create(
        name="Team Battle",
        type="team",
        game=game,
        max_participants=2,  # Max 2 teams
        team_size=2,
        entry_fee=50,
        is_free=False,
        required_verification_level=1,
        start_date=timezone.now() + timedelta(days=1),
        end_date=timezone.now() + timedelta(days=2),
    )


@pytest.fixture
def verified_user(user_factory):
    """Creates a user with level 1 verification."""
    user = user_factory(username="verified_user")
    Verification.objects.create(user=user, level=1)
    # Give user a wallet balance
    user.wallet.total_balance = 1000
    user.wallet.withdrawable_balance = 1000
    user.wallet.save()
    return user


@pytest.mark.django_db
@patch("tournaments.services.process_transaction", return_value=(True, None))
class TestJoinTournament:
    def test_join_individual_tournament_success(
        self, mock_process_tx, individual_tournament, verified_user
    ):
        """
        GIVEN a verified user and an individual tournament
        WHEN the user joins the tournament
        THEN they should be added as a participant and the entry fee processed.
        """
        join_tournament(tournament=individual_tournament, user=verified_user)

        assert individual_tournament.participants.filter(id=verified_user.id).exists()
        mock_process_tx.assert_called_once_with(
            user=verified_user,
            amount=individual_tournament.entry_fee,
            transaction_type="entry_fee",
            description=f"Entry fee for tournament: {individual_tournament.name}",
        )

    def test_join_tournament_is_full(
        self, mock_process_tx, individual_tournament, user_factory
    ):
        """
        GIVEN a tournament that is at maximum capacity
        WHEN another user tries to join
        THEN an ApplicationError should be raised.
        """
        # Fill the tournament
        for i in range(4):
            user = user_factory(
                username=f"player_{i}", phone_number=f"+9891234567{i}"
            )
            Verification.objects.create(user=user, level=1)
            Participant.objects.create(user=user, tournament=individual_tournament)

        new_user = user_factory(
            username="late_user", phone_number="+989123456799"
        )
        Verification.objects.create(user=new_user, level=1)

        with pytest.raises(ApplicationError, match="This tournament is full."):
            join_tournament(tournament=individual_tournament, user=new_user)

    def test_join_tournament_insufficient_verification(
        self, mock_process_tx, individual_tournament, default_user
    ):
        """
        GIVEN a user without the required verification level
        WHEN they try to join a tournament
        THEN an ApplicationError should be raised.
        """
        with pytest.raises(
            ApplicationError, match="You do not have the required verification level"
        ):
            join_tournament(tournament=individual_tournament, user=default_user)

    def test_join_tournament_insufficient_funds(
        self, mock_process_tx, individual_tournament, verified_user
    ):
        """
        GIVEN a user with insufficient funds
        WHEN they try to join a paid tournament
        THEN an ApplicationError should be raised.
        """
        mock_process_tx.return_value = (None, "Insufficient funds.")
        with pytest.raises(ApplicationError, match="Insufficient funds."):
            join_tournament(tournament=individual_tournament, user=verified_user)

    def test_join_tournament_already_joined(
        self, mock_process_tx, individual_tournament, verified_user
    ):
        """
        GIVEN a user who has already joined a tournament
        WHEN they try to join again
        THEN an ApplicationError should be raised.
        """
        # First join
        join_tournament(tournament=individual_tournament, user=verified_user)
        # Second attempt
        with pytest.raises(
            ApplicationError, match="You have already joined this tournament."
        ):
            join_tournament(tournament=individual_tournament, user=verified_user)

    @patch("tournaments.services.send_email_notification.delay")
    @patch("tournaments.services.send_sms_notification.delay")
    def test_join_team_tournament_success(
        self,
        mock_sms,
        mock_email,
        mock_process_tx,
        team_tournament,
        user_factory,
    ):
        """
        GIVEN a valid team whose captain tries to join a tournament
        THEN the team should be added and fees processed for all members.
        """
        captain = user_factory(username="captain", phone_number="+989123456711")
        member = user_factory(username="member", phone_number="+989123456722")
        Verification.objects.create(user=captain, level=1)
        Verification.objects.create(user=member, level=1)
        team = Team.objects.create(name="The Winners", captain=captain)
        team.members.add(member)

        join_tournament(tournament=team_tournament, user=captain, team_id=team.id)

        assert team_tournament.teams.filter(id=team.id).exists()
        # Check that both members are now participants
        assert team_tournament.participants.count() == 2
        # Check that fees were processed for both members
        assert mock_process_tx.call_count == 2
        calls = [
            call(
                user=captain,
                amount=team_tournament.entry_fee,
                transaction_type="entry_fee",
                description=f"Entry fee for tournament: {team_tournament.name}",
            ),
            call(
                user=member,
                amount=team_tournament.entry_fee,
                transaction_type="entry_fee",
                description=f"Entry fee for tournament: {team_tournament.name}",
            ),
        ]
        mock_process_tx.assert_has_calls(calls, any_order=True)

    def test_join_team_tournament_rollback_on_failure(
        self, mock_process_tx, team_tournament, user_factory
    ):
        """
        GIVEN a team joining a tournament
        WHEN one member's payment fails
        THEN the entire transaction should be rolled back, and no one is charged
              or registered.
        """
        captain = user_factory(username="captain", phone_number="+989123456711")
        member = user_factory(username="member", phone_number="+989123456722")
        Verification.objects.create(user=captain, level=1)
        Verification.objects.create(user=member, level=1)
        team = Team.objects.create(name="The Winners", captain=captain)
        team.members.add(member)

        # Simulate the second team member having insufficient funds
        mock_process_tx.side_effect = [
            (True, None),  # First member pays successfully
            (None, "Insufficient funds."),  # Second member fails
        ]

        with pytest.raises(ApplicationError, match="Insufficient funds."):
            join_tournament(tournament=team_tournament, user=captain, team_id=team.id)

        # Verify that the team was not added to the tournament
        assert not team_tournament.teams.filter(id=team.id).exists()
        # Verify that no participants were created
        assert team_tournament.participants.count() == 0
        # Verify that `process_transaction` was called for both members before failing
        assert mock_process_tx.call_count == 2

    def test_join_team_tournament_invalid_team_id(
        self, mock_process_tx, team_tournament, verified_user
    ):
        """
        GIVEN a user
        WHEN they try to join a team tournament with an invalid team ID
        THEN an ApplicationError should be raised.
        """
        with pytest.raises(ApplicationError, match="Invalid team ID."):
            join_tournament(tournament=team_tournament, user=verified_user, team_id=999)

    def test_join_team_tournament_not_captain(
        self, mock_process_tx, team_tournament, user_factory
    ):
        """
        GIVEN a user who is not a team captain
        WHEN they try to join a team tournament
        THEN an ApplicationError should be raised.
        """
        captain = user_factory(username="captain", phone_number="+989123456711")
        member = user_factory(username="member", phone_number="+989123456722")
        Verification.objects.create(user=captain, level=1)
        Verification.objects.create(user=member, level=1)
        team = Team.objects.create(name="The Winners", captain=captain)
        team.members.add(member)

        with pytest.raises(
            ApplicationError, match="Only the team captain can join a tournament."
        ):
            join_tournament(tournament=team_tournament, user=member, team_id=team.id)

    def test_join_team_tournament_wrong_team_size(
        self, mock_process_tx, team_tournament, user_factory
    ):
        """
        GIVEN a team with a size different from the tournament's requirement
        WHEN the captain tries to join
        THEN an ApplicationError should be raised.
        """
        captain = user_factory(username="captain", phone_number="+989123456711")
        Verification.objects.create(user=captain, level=1)
        team = Team.objects.create(name="Solo Team", captain=captain)  # Team size is 1

        with pytest.raises(
            ApplicationError, match="This tournament requires teams of size 2."
        ):
            join_tournament(tournament=team_tournament, user=captain, team_id=team.id)

    def test_join_team_tournament_member_already_joined(
        self, mock_process_tx, team_tournament, user_factory
    ):
        """
        GIVEN a team where one member is already in the tournament
        WHEN the captain tries to join
        THEN an ApplicationError should be raised.
        """
        captain = user_factory(username="captain_test_1", phone_number="+989123456733")
        member = user_factory(username="member_test_1", phone_number="+989123456744")
        Verification.objects.create(user=captain, level=1)
        Verification.objects.create(user=member, level=1)
        team = Team.objects.create(name="The Winners", captain=captain)
        team.members.add(member)

        # Manually add one of the team members as a participant
        Participant.objects.create(user=member, tournament=team_tournament)

        with pytest.raises(
            ApplicationError,
            match="One or more members of your team are already in this tournament.",
        ):
            join_tournament(tournament=team_tournament, user=captain, team_id=team.id)

    @patch("tournaments.services.send_email_notification.delay")
    @patch("tournaments.services.send_sms_notification.delay")
    def test_join_team_tournament_already_joined(
        self, mock_sms, mock_email, mock_process_tx, team_tournament, user_factory
    ):
        """
        GIVEN a team that has already joined a tournament
        WHEN the captain tries to join again
        THEN an ApplicationError should be raised.
        """
        captain = user_factory(username="captain_test_4", phone_number="+989123456799")
        member = user_factory(username="member_test_4", phone_number="+989123456700")
        Verification.objects.create(user=captain, level=1)
        Verification.objects.create(user=member, level=1)
        team = Team.objects.create(name="The Winners Again 2", captain=captain)
        team.members.add(member)

        # First join
        join_tournament(tournament=team_tournament, user=captain, team_id=team.id)

        # Ensure the mock is reset for the second call
        mock_process_tx.reset_mock()

        # Second attempt
        with pytest.raises(
            ApplicationError, match="Your team has already joined this tournament."
        ):
            join_tournament(tournament=team_tournament, user=captain, team_id=team.id)

        # Make sure no new transactions were processed
        mock_process_tx.assert_not_called()
        assert mock_sms.call_count == 2
        assert mock_email.call_count == 2

    @pytest.mark.parametrize(
        "score, level, expected_error",
        [
            (1500, 1, "You must be verified at level 2 to join this tournament."),
            (2500, 2, "You must be verified at level 3 to join this tournament."),
        ],
    )
    def test_join_tournament_high_score_verification(
        self,
        mock_process_tx,
        individual_tournament,
        user_factory,
        score,
        level,
        expected_error,
    ):
        """
        GIVEN a user with a high score but insufficient verification
        WHEN they try to join a tournament
        THEN an ApplicationError should be raised.
        """
        user = user_factory(username=f"high_score_user_{score}", score=score)
        Verification.objects.create(user=user, level=level)

        with pytest.raises(ApplicationError, match=expected_error):
            join_tournament(tournament=individual_tournament, user=user)


@pytest.mark.django_db
class TestMatchProgression:
    @pytest.fixture
    def setup_tournament(self, individual_tournament, user_factory):
        """Creates a tournament with 4 verified participants."""
        users = []
        for i in range(4):
            user = user_factory(
                username=f"player_{i}", phone_number=f"+9891234567{i}"
            )
            Verification.objects.create(user=user, level=1)
            Participant.objects.create(user=user, tournament=individual_tournament)
            users.append(user)
        return individual_tournament, users

    def test_generate_matches_success(self, setup_tournament):
        """
        GIVEN a tournament with participants
        WHEN matches are generated
        THEN the correct number of matches for the first round should be created.
        """
        tournament, _ = setup_tournament
        generate_matches(tournament)
        assert tournament.matches.count() == 2
        assert all(match.round == 1 for match in tournament.matches.all())

    def test_generate_matches_not_enough_participants(self, individual_tournament):
        """
        GIVEN a tournament with less than 2 participants
        WHEN matches are generated
        THEN an ApplicationError should be raised.
        """
        with pytest.raises(ApplicationError, match="Not enough participants"):
            generate_matches(individual_tournament)

    def test_confirm_result_and_advance_round(self, setup_tournament):
        """
        GIVEN a tournament with ongoing matches
        WHEN all matches in a round are confirmed
        THEN the system should automatically advance to the next round.
        """
        tournament, users = setup_tournament
        generate_matches(tournament)

        # Round 1
        round1_matches = list(tournament.matches.filter(round=1))
        assert len(round1_matches) == 2

        # Confirm first match
        confirm_match_result(
            round1_matches[0], winner_id=round1_matches[0].participant1_user.id
        )
        assert tournament.matches.filter(round=2).count() == 0  # Not all confirmed yet

        # Confirm second match
        confirm_match_result(
            round1_matches[1], winner_id=round1_matches[1].participant1_user.id
        )
        assert tournament.matches.filter(round=2).count() == 1  # Next round generated

        # Final Round
        final_match = tournament.matches.get(round=2)
        confirm_match_result(
            final_match, winner_id=final_match.participant1_user.id
        )
        assert tournament.matches.filter(round=3).count() == 0  # Tournament ended

        # Check winner
        winner = get_tournament_winners(tournament)[0]
        assert winner.id == final_match.participant1_user.id
