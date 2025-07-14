from .models import Tournament, Match
import random
from api.exceptions import ApplicationError

def generate_matches(tournament: Tournament):
    """
    Generates matches for the first round of a tournament.
    """
    if tournament.matches.exists():
        raise ApplicationError("Matches have already been generated for this tournament.")

    if tournament.type == 'individual':
        participants = list(tournament.participants.all())
        if len(participants) < 2:
            raise ApplicationError("Not enough participants to generate matches.")

        random.shuffle(participants)
        for i in range(0, len(participants) - 1, 2):
            Match.objects.create(
                tournament=tournament,
                match_type='individual',
                round=1,
                participant1_user=participants[i],
                participant2_user=participants[i+1]
            )
    elif tournament.type == 'team':
        teams = list(tournament.teams.all())
        if len(teams) < 2:
            raise ApplicationError("Not enough teams to generate matches.")

        random.shuffle(teams)
        for i in range(0, len(teams) - 1, 2):
            Match.objects.create(
                tournament=tournament,
                match_type='team',
                round=1,
                participant1_team=teams[i],
                participant2_team=teams[i+1]
            )

def confirm_match_result(match: Match, winner, proof_image=None):
    """
    Confirms the result of a match and advances the winner.
    """
    if match.is_confirmed:
        raise ApplicationError("Match result has already been confirmed.")

    match.is_confirmed = True
    match.result_proof = proof_image

    if match.match_type == 'individual':
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
    if tournament.type == 'individual':
        winners = [m.winner_user for m in tournament.matches.filter(round=current_round)]
        if len(winners) < 2:
            # Tournament is over
            return

        random.shuffle(winners)
        for i in range(0, len(winners) - 1, 2):
            Match.objects.create(
                tournament=tournament,
                match_type='individual',
                round=current_round + 1,
                participant1_user=winners[i],
                participant2_user=winners[i+1]
            )
    elif tournament.type == 'team':
        winners = [m.winner_team for m in tournament.matches.filter(round=current_round)]
        if len(winners) < 2:
            # Tournament is over
            return

        random.shuffle(winners)
        for i in range(0, len(winners) - 1, 2):
            Match.objects.create(
                tournament=tournament,
                match_type='team',
                round=current_round + 1,
                participant1_team=winners[i],
                participant2_team=winners[i+1]
            )
