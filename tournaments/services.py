import random
from decimal import Decimal

from django.db import transaction
from django.db.models import Count
from rest_framework.exceptions import PermissionDenied, ValidationError

from notifications.services import send_notification
from notifications.tasks import send_email_notification, send_sms_notification
from teams.models import Team
from users.models import InGameID, User
from verification.models import Verification
from wallet.services import process_transaction, process_token_transaction

from .exceptions import ApplicationError
from .models import Match, Participant, Report, Tournament, WinnerSubmission


def generate_matches(tournament: Tournament):
    """
    Generates matches for the first round of a tournament.
    """
    if tournament.mode == "battle_royale":
        # For Battle Royale, we don't generate traditional matches.
        # Winner determination will be handled differently, e.g., through winner submissions.
        return

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


def confirm_match_result(match: Match, winner_id: int, user: User, proof_image=None):
    """
    Confirms the result of a match and advances the winner.
    """
    if not match.is_participant(user):
        raise PermissionDenied("You are not a participant in this match.")

    if match.is_confirmed:
        raise ApplicationError("Match result has already been confirmed.")

    try:
        if match.match_type == "individual":
            winner = User.objects.get(id=winner_id)
            match.winner_user = winner
        else:
            winner = Team.objects.get(id=winner_id)
            match.winner_team = winner
    except (User.DoesNotExist, Team.DoesNotExist):
        raise ApplicationError("Invalid winner ID.")

    match.is_confirmed = True
    match.result_proof = proof_image
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
            winner = Tournament.objects.get(id=match.tournament.id).participants.get(
                id=winner_id
            )
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


@transaction.atomic
def join_tournament(
    tournament: Tournament,
    user: User,
    team_id: int = None,
    member_ids: list[int] = None,
):
    """
    Handles the logic for a user or a team to join a tournament,
    including validation, fee deduction, and notification.
    """
    # 0. Capacity Check
    if tournament.type == "individual":
        if tournament.participants.count() >= tournament.max_participants:
            raise ApplicationError("This tournament is full.")
    else:  # team
        if tournament.teams.count() >= tournament.max_participants:
            raise ApplicationError("This tournament is full.")

    # 1. Verification and Score Checks
    try:
        verification = user.verification
    except Verification.DoesNotExist:
        verification = None

    if (
        verification is None
        or verification.level < tournament.required_verification_level
    ):
        raise ApplicationError(
            "You do not have the required verification level to join this tournament."
        )

    if user.score >= 1000 and (verification is None or verification.level < 2):
        raise ApplicationError(
            "You must be verified at level 2 to join this tournament."
        )

    if user.score >= 2000 and (verification is None or verification.level < 3):
        raise ApplicationError(
            "You must be verified at level 3 to join this tournament."
        )

    # 2. Handle Individual vs. Team Tournament
    if tournament.type == "individual":
        if not InGameID.objects.filter(user=user, game=tournament.game).exists():
            raise ApplicationError(
                "You must set your in-game ID for this game before joining the tournament."
            )
        if tournament.participants.filter(id=user.id).exists():
            raise ApplicationError("You have already joined this tournament.")

        # 3. Handle Entry Fee using the safe wallet service
        if not tournament.is_free:
            if tournament.is_token_based:
                _, error = process_token_transaction(
                    user=user,
                    amount=tournament.entry_fee,
                    transaction_type="token_spent",
                    description=f"Token entry fee for tournament: {tournament.name}",
                )
            else:
                _, error = process_transaction(
                    user=user,
                    amount=tournament.entry_fee,
                    transaction_type="entry_fee",
                    description=f"Entry fee for tournament: {tournament.name}",
                )
            if error:
                raise ApplicationError(error)

        participant = Participant.objects.create(user=user, tournament=tournament)
        return participant

    elif tournament.type == "team":
        if not team_id:
            raise ApplicationError("Team ID is required for team tournaments.")

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            raise ApplicationError("Invalid team ID.")

        if user != team.captain:
            raise ApplicationError("Only the team captain can join a tournament.")

        if team.members.count() + 1 != tournament.team_size:
            raise ApplicationError(
                f"This tournament requires teams of size {tournament.team_size}."
            )

        if tournament.teams.filter(id=team.id).exists():
            raise ApplicationError("Your team has already joined this tournament.")

        # Fetch all members including the captain
        members = list(team.members.all()) + [team.captain]

        existing_in_game_ids = set(
            InGameID.objects.filter(user__in=members, game=tournament.game)
            .values_list("user_id", flat=True)
        )
        missing_in_game_ids = [
            member.username
            for member in members
            if member.id not in existing_in_game_ids
        ]

        if missing_in_game_ids:
            raise ApplicationError(
                "The following players need to set their in-game IDs for this game before joining the tournament: "
                + ", ".join(missing_in_game_ids)
            )

        if any(
            tournament.participants.filter(id=member.id).exists() for member in members
        ):
            raise ApplicationError(
                "One or more members of your team are already in this tournament."
            )

        # 3. Handle Entry Fee for Team using the safe wallet service
        if not tournament.is_free:
            for member in members:
                if tournament.is_token_based:
                    _, error = process_token_transaction(
                        user=member,
                        amount=tournament.entry_fee,
                        transaction_type="token_spent",
                        description=f"Token entry fee for tournament: {tournament.name}",
                    )
                else:
                    _, error = process_transaction(
                        user=member,
                        amount=tournament.entry_fee,
                        transaction_type="entry_fee",
                        description=f"Entry fee for tournament: {tournament.name}",
                    )
                if error:
                    # Note: In a real-world scenario, we would need to roll back
                    # the transactions for other team members who were already charged.
                    # The current `process_transaction` is atomic per user, but the
                    # overall team join is not. This is a complex problem.
                    # For now, we raise an error for the first member that fails.
                    raise ApplicationError(
                        f"Failed to process fee for {member.username}: {error}"
                    )

        tournament.teams.add(team)
        for member in members:
            Participant.objects.get_or_create(user=member, tournament=tournament)

        # 4. Send Notifications
        context = {
            "tournament_name": tournament.name,
            "entry_code": "placeholder-entry-code",  # Replace with actual entry code
            "room_id": "placeholder-room-id",  # Replace with actual room ID
        }
        for member in members:
            send_email_notification.delay(
                member.email,
                "Tournament Joined",
                "notifications/email/tournament_joined.html",
                context,
            )
            send_sms_notification.delay(str(member.phone_number), context)

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
    """Return the tournament winners.

    For standard brackets we keep the historical behaviour of returning the top
    five finishers. For head-to-head tournaments (two entrants only) we limit
    the result to the single champion so that only the rightful winner receives
    the prize.
    """
    if tournament.type == "individual":
        entrant_count = tournament.participants.count()
        base_queryset = User.objects.filter(won_matches__tournament=tournament)
    else:
        entrant_count = tournament.teams.count()
        base_queryset = Team.objects.filter(won_matches__tournament=tournament)

    duel_limit = 1 if entrant_count <= 2 else tournament.winner_slots
    limit = max(1, duel_limit)

    winners = (
        base_queryset.annotate(num_wins=Count("won_matches"))
        .order_by("-num_wins", "id")[:limit]
    )
    return winners


def pay_prize(tournament: Tournament, winner):
    """
    Pays the prize to the winner using the safe wallet service.
    """
    # This is a simplified logic. In a real application, you would
    # probably have a more complex prize distribution system.
    if tournament.is_free:
        return

    prize_amount = tournament.prize_pool or 0

    if prize_amount > 0:
        _, error = process_transaction(
            user=winner,
            amount=prize_amount,
            transaction_type="prize",
            description=f"Prize for winning tournament: {tournament.name}",
        )
        if error:
            # In a real app, this should trigger an alert for manual review.
            print(f"ERROR: Failed to pay prize to {winner.username} for tournament {tournament.id}: {error}")


def refund_entry_fees(tournament: Tournament, cheater):
    """
    Refunds entry fees to all participants except the cheater.
    """
    if tournament.is_free or not tournament.entry_fee:
        return

    for participant in tournament.participants.all():
        if participant.user != cheater:
            _, error = process_transaction(
                user=participant.user,
                amount=tournament.entry_fee,
                transaction_type="deposit", # Refund is a type of deposit
                description=f"Refund for tournament: {tournament.name}",
            )
            if error:
                print(f"ERROR: Failed to refund {participant.user.username} for t: {tournament.id}: {error}")


def create_report_service(
    reporter: User,
    reported_user_id: int,
    tournament: Tournament,
    match: Match | None,
    description: str,
    evidence=None,
):
    """
    Creates a report and sends a notification.
    """
    report = Report.objects.create(
        reporter=reporter,
        reported_user_id=reported_user_id,
        tournament=tournament,
        match=match,
        description=description,
        evidence=evidence,
    )
    send_notification(
        user=report.reported_user,
        message=f"You have been reported in tournament {report.tournament}.",
        notification_type="report_new",
    )
    return report


def resolve_report_service(report: Report, ban_user: bool):
    """
    Resolves a report, optionally banning the user, and sends a notification.
    """
    if ban_user:
        reported_user = report.reported_user
        reported_user.is_active = False
        reported_user.save()
        report.status = "resolved"
        report.save()
        send_notification(
            user=report.reporter,
            message=f"Your report against {reported_user.username} has been resolved and the user has been banned.",
            notification_type="report_status_change",
        )
    else:
        report.status = "resolved"
        report.save()
        send_notification(
            user=report.reporter,
            message=f"Your report against {report.reported_user.username} has been resolved.",
            notification_type="report_status_change",
        )
    return report


def reject_report_service(report: Report):
    """
    Rejects a report and sends a notification.
    """
    report.status = "rejected"
    report.save()
    send_notification(
        user=report.reporter,
        message=f"Your report against {report.reported_user.username} has been rejected.",
        notification_type="report_status_change",
    )
    return report


def _is_user_in_winning_teams(user: User, teams):
    """Return True if the user is the captain or a member of any team in ``teams``."""

    for team in teams:
        if team.captain_id == user.id:
            return True
        if team.members.filter(id=user.id).exists():
            return True
    return False


def create_winner_submission_service(user: User, tournament: Tournament, video):
    """
    Creates a winner submission after checking if the user is an eligible winner.
    """
    winners = list(get_tournament_winners(tournament))

    if tournament.type == "team":
        is_winner = _is_user_in_winning_teams(user, winners)
        if not is_winner:
            raise ValidationError("You are not a member of a winning team.")
    else:
        is_winner = user in winners
        if not is_winner:
            raise ValidationError("You are not one of the tournament winners.")

    submission = WinnerSubmission.objects.create(
        winner=user, tournament=tournament, video=video
    )
    send_notification(
        user=user,
        message="Your winner submission has been received.",
        notification_type="winner_submission_status_change",
    )
    return submission


def distribute_scores_for_tournament(tournament: Tournament, score_distribution=None):
    """
    Distributes scores to players or teams at the end of a tournament.

    This function is designed to be more efficient and configurable than the
    original model method. It uses bulk_update for efficiency.

    Args:
        tournament: The Tournament instance that has finished.
        score_distribution (list, optional): A list of scores to be awarded
            to the top places. E.g., [10, 5, 3] for 1st, 2nd, 3rd.
            If None, a default scoring system is used.
    """
    if score_distribution is None:
        # Default scoring: 5 points for 1st, 4 for 2nd, 3 for 3rd, etc.
        score_distribution = [5, 4, 3, 2, 1]

    users_to_update = []
    if tournament.type == "individual":
        # Get the top players from the tournament's m2m field
        top_placements = tournament.top_players.all()
        for i, player in enumerate(top_placements):
            if i < len(score_distribution):
                player.score += score_distribution[i]
                users_to_update.append(player)
    else:  # 'team'
        # Get the top teams from the tournament's m2m field
        top_placements = tournament.top_teams.all()
        for i, team in enumerate(top_placements):
            if i < len(score_distribution):
                # Award points to every member of the team, including the captain
                all_members = list(team.members.all()) + [team.captain]
                for member in all_members:
                    # It's important to fetch the user again to avoid stale data
                    user = User.objects.get(id=member.id)
                    user.score += score_distribution[i]
                    users_to_update.append(user)

    # Use a transaction to ensure all score updates are atomic and efficient
    with transaction.atomic():
        User.objects.bulk_update(users_to_update, ["score"])

    # After scores are updated, ranks might change.
    # This part still involves individual saves, but rank updates are
    # complex and might need to run one by one.
    for user in users_to_update:
        user.update_rank()


def approve_winner_submission_service(submission: WinnerSubmission):
    """
    Approves a winner submission, pays the prize, and sends a notification.
    """
    submission.status = "approved"
    submission.save()
    pay_prize(submission.tournament, submission.winner)
    send_notification(
        user=submission.winner,
        message=f"Your submission for {submission.tournament.name} has been approved.",
        notification_type="winner_submission_status_change",
    )
    return submission


def reject_winner_submission_service(submission: WinnerSubmission):
    """
    Rejects a winner submission, refunds entry fees, and sends a notification.
    """
    submission.status = "rejected"
    submission.save()
    refund_entry_fees(submission.tournament, submission.winner)
    send_notification(
        user=submission.winner,
        message=f"Your submission for {submission.tournament.name} has been rejected.",
        notification_type="winner_submission_status_change",
    )
    return submission
