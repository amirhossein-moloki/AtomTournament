import random

from django.db import models
from users.models import Team, User
from .exceptions import ApplicationError
from .models import Match, Participant, Tournament


def generate_matches(tournament: Tournament):
    """
    Generates matches for the first round of a tournament.
    """
    if tournament.matches.exists():
        raise ApplicationError(
            "Matches have already been generated for this tournament."
        )

    if tournament.type == "individual":
        participants = list(tournament.participants.all())
        if len(participants) < 2:
            raise ApplicationError("Not enough participants to generate matches.")

        random.shuffle(participants)
        for i in range(0, len(participants) - 1, 2):
            Match.objects.create(
                tournament=tournament,
                match_type="individual",
                round=1,
                participant1_user=participants[i],
                participant2_user=participants[i + 1],
            )
    elif tournament.type == "team":
        teams = list(tournament.teams.all())
        if len(teams) < 2:
            raise ApplicationError("Not enough teams to generate matches.")

        random.shuffle(teams)
        for i in range(0, len(teams) - 1, 2):
            Match.objects.create(
                tournament=tournament,
                match_type="team",
                round=1,
                participant1_team=teams[i],
                participant2_team=teams[i + 1],
            )


def confirm_match_result(match: Match, winner, proof_image=None):
    """
    Confirms the result of a match and advances the winner.
    """
    if match.is_confirmed:
        raise ApplicationError("Match result has already been confirmed.")

    match.is_confirmed = True
    match.result_proof = proof_image

    if match.match_type == "individual":
        match.winner_user = winner
    else:
        match.winner_team = winner

    match.save()

    # Check if all matches in the round are confirmed
    tournament = match.tournament
    round_matches = tournament.matches.filter(round=match.round)
    if all(m.is_confirmed for m in round_matches):
        advance_to_next_round(tournament, match.round)


def advance_to_next_round(tournament: Tournament, current_round: int):
    """
    Advances the winners of the current round to the next round.
    """
    if tournament.type == "individual":
        winners = [
            m.winner_user for m in tournament.matches.filter(round=current_round)
        ]
        if len(winners) < 2:
            # Tournament is over
            return

        random.shuffle(winners)
        for i in range(0, len(winners) - 1, 2):
            Match.objects.create(
                tournament=tournament,
                match_type="individual",
                round=current_round + 1,
                participant1_user=winners[i],
                participant2_user=winners[i + 1],
            )
    elif tournament.type == "team":
        winners = [
            m.winner_team for m in tournament.matches.filter(round=current_round)
        ]
        if len(winners) < 2:
            # Tournament is over
            return

        random.shuffle(winners)
        for i in range(0, len(winners) - 1, 2):
            Match.objects.create(
                tournament=tournament,
                match_type="team",
                round=current_round + 1,
                participant1_team=winners[i],
                participant2_team=winners[i + 1],
            )


def record_match_result(match: Match, winner_id, proof_image=None):
    """
    Finds the winner object and confirms the match result.
    """
    try:
        if match.match_type == "individual":
            winner = Tournament.objects.get(
                id=match.tournament.id
            ).participants.get(id=winner_id)
        else:
            winner = Tournament.objects.get(id=match.tournament.id).teams.get(
                id=winner_id
            )
    except (
        Tournament.participants.model.DoesNotExist,
        Tournament.teams.model.DoesNotExist,
    ):
        raise ValueError("Invalid winner ID.")

    confirm_match_result(match, winner, proof_image)


from wallet.models import Wallet


def join_tournament(tournament: Tournament, user, team, members):
    """
    Adds a user or a team to a tournament.
    """
    if tournament.type == "individual":
        if tournament.participants.filter(id=user.id).exists():
            raise ApplicationError("You have already joined this tournament.")

        # Tier-based restrictions
        if tournament.tier == "silver" and user.points < 1000:
            raise ApplicationError("You need at least 1000 points to join a silver tournament.")
        if tournament.tier == "gold" and user.points < 2000:
            raise ApplicationError("You need at least 2000 points to join a gold tournament.")
        if tournament.tier == "diamond" and user.points < 3000:
            raise ApplicationError("You need at least 3000 points to join a diamond tournament.")

        # Authentication level restrictions
        if tournament.tier == "silver" and user.authentication_level < 2:
            raise ApplicationError("You need authentication level 2 to join a silver tournament.")
        if tournament.tier == "gold" and user.authentication_level < 3:
            raise ApplicationError("You need authentication level 3 to join a gold tournament.")
        if tournament.tier == "diamond" and user.authentication_level < 3:
            raise ApplicationError("You need authentication level 3 to join a diamond tournament.")

        # Tournaments played restrictions
        if tournament.tournaments_played_min is not None and user.tournaments_played < tournament.tournaments_played_min:
            raise ApplicationError(f"You need to have played at least {tournament.tournaments_played_min} tournaments to join.")
        if tournament.tournaments_played_max is not None and user.tournaments_played > tournament.tournaments_played_max:
            raise ApplicationError(f"You cannot have played more than {tournament.tournaments_played_max} tournaments to join.")

        # Check wallet balance
        if not tournament.is_free:
            wallet = Wallet.objects.get(user=user)
            if wallet.withdrawable_balance < tournament.entry_fee:
                raise ApplicationError("Insufficient funds to join the tournament.")
            wallet.withdrawable_balance -= tournament.entry_fee
            wallet.save()

        user.tournaments_played += 1
        user.save()

        participant = Participant.objects.create(user=user, tournament=tournament)
        return participant
    elif tournament.type == "team":
        if tournament.teams.filter(id=team.id).exists():
            raise ApplicationError("Your team has already joined this tournament.")
        if any(
            tournament.participants.filter(id=member.id).exists() for member in members
        ):
            raise ApplicationError(
                "One or more members of your team are already in this tournament."
            )
        # Check wallet balance for all members
        if not tournament.is_free:
            for member in members:
                wallet = Wallet.objects.get(user=member)
                if wallet.withdrawable_balance < tournament.entry_fee:
                    raise ApplicationError(
                        f"Insufficient funds for member {member.username}."
                    )
        # Deduct entry fee from all members
        if not tournament.is_free:
            for member in members:
                wallet = Wallet.objects.get(user=member)
                wallet.withdrawable_balance -= tournament.entry_fee
                wallet.save()
        tournament.teams.add(team)
        # Create participant entries for all team members
        for member in members:
            Participant.objects.get_or_create(user=member, tournament=tournament)
        return team


def dispute_match_result(match: Match, user, reason: str):
    """
    Marks a match as disputed.
    """
    if not match.is_participant(user):
        raise PermissionDenied("You are not a participant in this match.")
    if not reason:
        raise ApplicationError("A reason for the dispute must be provided.")

    match.is_disputed = True
    match.dispute_reason = reason
    match.save()


def get_tournament_winners(tournament: Tournament):
    """
    Returns the top 5 winners of a tournament.
    """
    if tournament.type == "individual":
        winners = (
            User.objects.filter(won_matches__tournament=tournament)
            .annotate(num_wins=models.Count("won_matches"))
            .order_by("-num_wins")[:5]
        )
    else:
        winners = (
            Team.objects.filter(won_matches__tournament=tournament)
            .annotate(num_wins=models.Count("won_matches"))
            .order_by("-num_wins")[:5]
        )
    return winners


def pay_prize(tournament: Tournament, winner):
    """
    Pays the prize to the winner.
    """
    # This is a simplified logic. In a real application, you would
    # probably have a more complex prize distribution system.
    prize_amount = tournament.entry_fee * tournament.participants.count() * 0.8  # 80% of the pot
    wallet = Wallet.objects.get(user=winner)
    wallet.withdrawable_balance += prize_amount
    wallet.save()

    # Award points
    winner.points += 100

    # Check for authentication level upgrade
    if winner.points >= 2000 and winner.authentication_level < 3:
        winner.authentication_level = 3
    elif winner.points >= 1000 and winner.authentication_level < 2:
        winner.authentication_level = 2

    winner.save()


def refund_entry_fees(tournament: Tournament, cheater):
    """
    Refunds entry fees to all participants except the cheater.
    """
    for participant in tournament.participants.all():
        if participant.user != cheater:
            wallet = Wallet.objects.get(user=participant.user)
            wallet.withdrawable_balance += tournament.entry_fee
            wallet.save()
