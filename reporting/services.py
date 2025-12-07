from django.db.models import Sum, F, Count, ExpressionWrapper, FloatField, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import re

from wallet.models import Transaction
from tournaments.models import Tournament, Game, Participant
from users.models import User, Referral


BOT_USERNAME = "AtomGameBot"
BOT_EMAIL = "atomgamebot@example.com"
BOT_PHONE_NUMBER = "+989000000001"


def ensure_bot_user():
    """Ensure the AtomGameBot user exists and is active for reporting metrics."""
    bot_user, created = User.objects.get_or_create(
        username=BOT_USERNAME,
        defaults={
            "email": BOT_EMAIL,
            "phone_number": BOT_PHONE_NUMBER,
            "is_active": True,
        },
    )

    updates = []
    if created:
        bot_user.set_unusable_password()
        updates.append("password")

    if not bot_user.is_active:
        bot_user.is_active = True
        updates.append("is_active")

    if not bot_user.phone_number:
        bot_user.phone_number = BOT_PHONE_NUMBER
        updates.append("phone_number")

    if updates:
        bot_user.save(update_fields=updates)

    return bot_user


def generate_revenue_report(filters=None):
    """
    Generates a comprehensive revenue report based on provided filters.
    """
    if filters is None:
        filters = {}

    revenue_transactions = Transaction.objects.filter(transaction_type='entry_fee')
    end_date = filters.get('end_date', timezone.now())
    start_date = filters.get('start_date', end_date - timedelta(days=30))
    revenue_transactions = revenue_transactions.filter(timestamp__range=[start_date, end_date])

    total_revenue = revenue_transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    platform_share = total_revenue * Decimal('0.30')
    players_share = total_revenue * Decimal('0.70')

    revenue_by_tournament_raw = revenue_transactions.values('description').annotate(total=Sum('amount')).order_by('-total')
    revenue_by_tournament = []
    tournament_revenue_map = {}
    for item in revenue_by_tournament_raw:
        match = re.search(r'Entry fee for tournament: (.+)', item['description'])
        if match:
            tournament_name = match.group(1)
            revenue_by_tournament.append({
                "tournament_name": tournament_name,
                "total_revenue": item['total'],
            })
            tournament_revenue_map[tournament_name] = item['total']

    tournaments = Tournament.objects.filter(name__in=tournament_revenue_map.keys()).select_related('game')
    revenue_by_game_map = {}
    for t in tournaments:
        game_name = t.game.name
        revenue = tournament_revenue_map.get(t.name, Decimal('0'))
        revenue_by_game_map[game_name] = revenue_by_game_map.get(game_name, Decimal('0')) + revenue

    revenue_by_game = [{"game_name": name, "total_revenue": total} for name, total in revenue_by_game_map.items()]

    timeline_data = (
        revenue_transactions.annotate(day=TruncDay('timestamp'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )

    return {
        "summary": {
            "total_revenue": total_revenue,
            "platform_share": platform_share,
            "players_share": players_share,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "by_game": revenue_by_game,
        "by_tournament": revenue_by_tournament,
        "timeline": [{"date": item['day'].isoformat(), "revenue": item['total']} for item in timeline_data],
    }


def generate_players_report(filters=None):
    """
    Generates a comprehensive players report based on provided filters.
    """
    if filters is None:
        filters = {}

    ensure_bot_user()

    end_date = filters.get('end_date', timezone.now())
    start_date = filters.get('start_date', end_date - timedelta(days=30))

    total_users = User.objects.count()
    active_player_ids = Participant.objects.filter(
        tournament__start_date__range=[start_date, end_date]
    ).values_list('user_id', flat=True).distinct()
    active_players_count = len(active_player_ids)

    total_participations = Participant.objects.filter(
        tournament__start_date__range=[start_date, end_date]
    ).count()
    avg_participation = total_participations / active_players_count if active_players_count > 0 else 0

    participants_by_game = (
        Participant.objects.filter(tournament__start_date__range=[start_date, end_date])
        .values('tournament__game__name')
        .annotate(player_count=Count('user', distinct=True))
        .order_by('-player_count')
    )

    distribution_by_game = [
        {
            "game_name": item['tournament__game__name'],
            "player_count": item['player_count'],
            "percentage": (item['player_count'] / active_players_count) * 100 if active_players_count > 0 else 0,
        }
        for item in participants_by_game
    ]

    return {
        "summary": {
            "total_users": total_users,
            "active_players": active_players_count,
            "avg_participation_per_player": avg_participation,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "distribution_by_game": distribution_by_game,
    }

def generate_financial_report(filters=None):
    """
    Generates a detailed financial report.
    """
    if filters is None:
        filters = {}

    end_date = filters.get('end_date', timezone.now())
    start_date = filters.get('start_date', end_date - timedelta(days=365)) # Default to one year

    transactions = Transaction.objects.filter(timestamp__range=[start_date, end_date])

    total_prize_paid = transactions.filter(transaction_type='prize').aggregate(total=Sum('amount'))['total'] or Decimal('0')

    total_revenue = transactions.filter(transaction_type='entry_fee').aggregate(total=Sum('amount'))['total'] or Decimal('0')

    net_profit = total_revenue * Decimal('0.30')

    cash_flow = (
        transactions.annotate(month=TruncMonth('timestamp'))
        .values('month')
        .annotate(
            income=Sum('amount', filter=Q(transaction_type='entry_fee')),
            expenses=Sum('amount', filter=Q(transaction_type__in=['prize', 'withdrawal']))
        )
        .order_by('month')
    )

    return {
        "summary": {
            "total_revenue": total_revenue,
            "total_prize_paid": total_prize_paid,
            "net_profit": net_profit,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "cash_flow": [
            {
                "month": item['month'].strftime('%Y-%m'),
                "income": item['income'] or Decimal('0'),
                "expenses": item['expenses'] or Decimal('0'),
                "net_flow": (item['income'] or Decimal('0')) - (item['expenses'] or Decimal('0')),
            }
            for item in cash_flow
        ]
    }


def generate_marketing_report(filters=None):
    """
    Generates a marketing and referral report.
    """
    if filters is None:
        filters = {}

    end_date = filters.get('end_date', timezone.now())
    start_date = filters.get('start_date', end_date - timedelta(days=90))

    referrals_by_user = (
        Referral.objects
        .filter(created_at__range=[start_date, end_date])
        .values('referrer__username')
        .annotate(new_users=Count('referred'))
        .order_by('-new_users')
    )

    referred_user_ids = Referral.objects.filter(
        created_at__range=[start_date, end_date]
    ).values_list('referred_id', flat=True)

    revenue_from_referred = Transaction.objects.filter(
        wallet__user_id__in=referred_user_ids,
        transaction_type='entry_fee'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    return {
        "summary": {
            "total_referred_users": len(referred_user_ids),
            "revenue_from_referred_users": revenue_from_referred,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "by_referrer": list(referrals_by_user)
    }


def generate_tournament_report(filters=None):
    """
    Generates a comprehensive tournament report.
    """
    if filters is None:
        filters = {}

    tournaments = Tournament.objects.all().annotate(
        participant_count=Count('participants', distinct=True)
    ).order_by('-start_date')

    if 'game_id' in filters:
        tournaments = tournaments.filter(game_id=filters['game_id'])

    most_popular_tournaments = sorted(
        list(tournaments),
        key=lambda t: t.participant_count,
        reverse=True
    )[:10]

    revenue_data = generate_revenue_report(filters)
    profitable_map = {t['tournament_name']: t['total_revenue'] for t in revenue_data['by_tournament']}

    for t in tournaments:
        t.revenue = profitable_map.get(t.name, Decimal('0'))

    most_profitable_tournaments = sorted(
        list(tournaments),
        key=lambda t: t.revenue,
        reverse=True
    )[:10]

    for t in tournaments:
        if t.max_participants > 0:
            t.fill_rate = (t.participant_count / t.max_participants) * 100
        else:
            t.fill_rate = 0

    return {
        "all_tournaments": [
            {
                "name": t.name,
                "game": t.game.name,
                "start_date": t.start_date,
                "participant_count": t.participant_count,
                "capacity": t.max_participants,
                "fill_rate": t.fill_rate,
                "revenue": t.revenue,
            }
            for t in tournaments
        ],
        "most_popular": [
            {
                "name": t.name,
                "participant_count": t.participant_count,
            } for t in most_popular_tournaments
        ],
        "most_profitable": [
            {
                "name": t.name,
                "revenue": t.revenue,
            } for t in most_profitable_tournaments
        ]
    }
