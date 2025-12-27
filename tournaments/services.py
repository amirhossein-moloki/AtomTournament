import logging
import random
from decimal import Decimal

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from notifications.services import send_notification
from notifications.tasks import send_email_notification, send_sms_notification
from teams.models import Team
from users.models import InGameID, User
from verification.models import Verification
from wallet.services import WalletService
from wallet.models import Transaction # For TransactionType enum

from .exceptions import ApplicationError
from .models import Match, Participant, Report, Tournament, WinnerSubmission

logger = logging.getLogger(__name__)


def generate_matches(tournament: Tournament):
    """
    Generates matches for the first round of a tournament.
    """
    if tournament.mode == "battle_royale":
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
    now = timezone.now()
    if (
        tournament.registration_start_date
        and now < tournament.registration_start_date
    ):
        raise ApplicationError(_("Registration has not started yet."))
    if tournament.registration_end_date and now > tournament.registration_end_date:
        raise ApplicationError(_("Registration has already ended."))

    if tournament.type == "individual":
        if tournament.participants.count() >= tournament.max_participants:
            raise ApplicationError("This tournament is full.")
    else:
        if tournament.teams.count() >= tournament.max_participants:
            raise ApplicationError("This tournament is full.")

    try:
        verification = user.verification
        if verification.level < tournament.required_verification_level:
            raise ApplicationError("You do not have the required verification level.")
    except Verification.DoesNotExist:
        raise ApplicationError("You are not verified.")

    if tournament.type == "individual":
        if not InGameID.objects.filter(user=user, game=tournament.game).exists():
            raise ApplicationError("You must set your in-game ID for this game.")
        if tournament.participants.filter(id=user.id).exists():
            raise ApplicationError("You have already joined this tournament.")

        if not tournament.is_free:
            transaction_type = (
                Transaction.TransactionType.TOKEN_SPENT
                if tournament.is_token_based
                else Transaction.TransactionType.ENTRY_FEE
            )
            WalletService.process_transaction(
                user=user,
                amount=tournament.entry_fee,
                transaction_type=transaction_type,
                description=f"Entry fee for tournament: {tournament.name}",
            )

        return Participant.objects.create(user=user, tournament=tournament)

    elif tournament.type == "team":
        team = Team.objects.get(id=team_id)
        if user != team.captain:
            raise ApplicationError("Only the team captain can join a tournament.")
        if tournament.teams.filter(id=team.id).exists():
            raise ApplicationError("Your team has already joined this tournament.")

        members = list(team.members.all()) + [team.captain]
        if len(members) < tournament.team_size:
            raise ApplicationError("Your team does not have enough members.")

        for member in members:
            if not InGameID.objects.filter(user=member, game=tournament.game).exists():
                raise ApplicationError(
                    f"User {member.username} must set their in-game ID for this game."
                )

        if not tournament.is_free:
            transaction_type = (
                Transaction.TransactionType.TOKEN_SPENT
                if tournament.is_token_based
                else Transaction.TransactionType.ENTRY_FEE
            )
            for member in members:
                try:
                    WalletService.process_transaction(
                        user=member,
                        amount=tournament.entry_fee,
                        transaction_type=transaction_type,
                        description=f"Entry fee for team {team.name} in tournament: {tournament.name}",
                    )
                except ValidationError as e:
                    raise ApplicationError(
                        f"Failed to process fee for {member.username}: {e.detail[0]}"
                    )

        tournament.teams.add(team)
        for member in members:
            Participant.objects.get_or_create(user=member, tournament=tournament)

        return team

def pay_prize(tournament: Tournament, winner):
    """
    Pays the prize to the winner using the safe wallet service.
    """
    if tournament.is_free or not tournament.prize_pool or tournament.prize_pool <= 0:
        return

    try:
        WalletService.process_transaction(
            user=winner,
            amount=tournament.prize_pool,
            transaction_type=Transaction.TransactionType.PRIZE,
            description=f"Prize for winning tournament: {tournament.name}",
        )
    except ValidationError as e:
        logger.error(f"Failed to pay prize to {winner.username} for tournament {tournament.id}: {e.detail[0]}")


def refund_entry_fees(tournament: Tournament, cheater):
    """
    Refunds entry fees to all participants except the cheater.
    """
    if tournament.is_free or not tournament.entry_fee:
        return

    for participant in tournament.participants.all():
        if participant.user != cheater:
            try:
                WalletService.process_transaction(
                    user=participant.user,
                    amount=tournament.entry_fee,
                    transaction_type=Transaction.TransactionType.DEPOSIT,
                    description=f"Refund for tournament: {tournament.name}",
                )
            except ValidationError as e:
                logger.error(f"Failed to refund {participant.user.username} for t: {tournament.id}: {e.detail[0]}")

# ... (other functions remain the same)
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
    """Return the tournament winners."""
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
        message=_("You have been reported in tournament %(tournament_name)s.")
        % {"tournament_name": report.tournament},
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
            message=_(
                "Your report against %(reported_user)s has been resolved and the user has been banned."
            )
            % {"reported_user": reported_user.username},
            notification_type="report_status_change",
        )
    else:
        report.status = "resolved"
        report.save()
        send_notification(
            user=report.reporter,
            message=_("Your report against %(reported_user)s has been resolved.")
            % {"reported_user": report.reported_user.username},
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
        message=_("Your report against %(reported_user)s has been rejected.")
        % {"reported_user": report.reported_user.username},
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


def create_winner_submission_service(user: User, tournament: Tournament, image):
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
        winner=user, tournament=tournament, image=image
    )
    send_notification(
        user=user,
        message=_("Your winner submission has been received."),
        notification_type="winner_submission_status_change",
    )
    return submission


def distribute_scores_for_tournament(tournament: Tournament, score_distribution=None):
    if score_distribution is None:
        score_distribution = [5, 4, 3, 2, 1]

    users_to_update = []
    if tournament.type == "individual":
        top_placements = tournament.top_players.all()
        for i, player in enumerate(top_placements):
            if i < len(score_distribution):
                player.score += score_distribution[i]
                users_to_update.append(player)
    else:  # 'team'
        top_placements = tournament.top_teams.all()
        for i, team in enumerate(top_placements):
            if i < len(score_distribution):
                all_members = list(team.members.all()) + [team.captain]
                for member in all_members:
                    user = User.objects.get(id=member.id)
                    user.score += score_distribution[i]
                    users_to_update.append(user)
    with transaction.atomic():
        User.objects.bulk_update(users_to_update, ["score"])

    for user in users_to_update:
        user.update_rank()


def approve_winner_submission_service(submission: WinnerSubmission):
    submission.status = "approved"
    submission.save()
    pay_prize(submission.tournament, submission.winner)
    send_notification(
        user=submission.winner,
        message=_("Your submission for %(tournament_name)s has been approved.")
        % {"tournament_name": submission.tournament.name},
        notification_type="winner_submission_status_change",
    )
    return submission


def reject_winner_submission_service(submission: WinnerSubmission):
    submission.status = "rejected"
    submission.save()
    refund_entry_fees(submission.tournament, submission.winner)
    send_notification(
        user=submission.winner,
        message=_("Your submission for %(tournament_name)s has been rejected.")
        % {"tournament_name": submission.tournament.name},
        notification_type="winner_submission_status_change",
    )
    return submission
