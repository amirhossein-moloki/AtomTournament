from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Wallet
from .services import update_wallet_balance, pay_entry_fee, distribute_prize
from tournaments.models import Tournament, Game, Match
from users.models import Team
from decimal import Decimal
from datetime import datetime, timedelta

User = get_user_model()

class WalletServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password", phone_number="+12125552368")
        self.wallet = Wallet.objects.create(user=self.user, total_balance=100, withdrawable_balance=50)
        self.game = Game.objects.create(name="Test Game")
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=1),
            is_free=False,
            entry_fee=Decimal('10.00'),
            type='individual'
        )
        self.tournament.participants.add(self.user)

    def test_deposit(self):
        update_wallet_balance(self.user, Decimal('50.00'), 'deposit')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal('150.00'))

    def test_withdrawal(self):
        update_wallet_balance(self.user, Decimal('30.00'), 'withdrawal')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.withdrawable_balance, Decimal('20.00'))
        self.assertEqual(self.wallet.total_balance, Decimal('70.00'))

    def test_insufficient_withdrawable_balance(self):
        with self.assertRaises(ValueError):
            update_wallet_balance(self.user, Decimal('60.00'), 'withdrawal')

    def test_pay_entry_fee(self):
        pay_entry_fee(self.user, self.tournament)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal('90.00'))

    def test_distribute_prize_individual(self):
        user2 = User.objects.create_user(username="user2", password="password", phone_number="+12125552369")
        Wallet.objects.create(user=user2, total_balance=100, withdrawable_balance=50)
        self.tournament.participants.add(user2)

        match = Match.objects.create(
            tournament=self.tournament,
            match_type='individual',
            round=1,
            participant1_user=self.user,
            participant2_user=user2,
            winner_user=self.user,
            is_confirmed=True
        )

        distribute_prize(self.tournament)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal('120.00')) # 100 (initial) + 20 (prize)
        self.assertEqual(self.wallet.withdrawable_balance, Decimal('70.00')) # 50 (initial) + 20 (prize)

    def test_distribute_prize_team(self):
        user2 = User.objects.create_user(username="user2", password="password", phone_number="+12125552369")
        user3 = User.objects.create_user(username="user3", password="password", phone_number="+12125552370")
        user4 = User.objects.create_user(username="user4", password="password", phone_number="+12125552371")

        team1 = Team.objects.create(name="Team 1", captain=self.user)
        team2 = Team.objects.create(name="Team 2", captain=user3)

        team1.members.add(self.user, user2)
        team2.members.add(user3, user4)

        wallet2 = Wallet.objects.create(user=user2, total_balance=100, withdrawable_balance=50)
        Wallet.objects.create(user=user3, total_balance=100, withdrawable_balance=50)
        Wallet.objects.create(user=user4, total_balance=100, withdrawable_balance=50)

        team_tournament = Tournament.objects.create(
            name="Team Tournament",
            game=self.game,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=1),
            is_free=False,
            entry_fee=Decimal('20.00'),
            type='team'
        )
        team_tournament.teams.add(team1, team2)

        match = Match.objects.create(
            tournament=team_tournament,
            match_type='team',
            round=1,
            participant1_team=team1,
            participant2_team=team2,
            winner_team=team1,
            is_confirmed=True
        )

        distribute_prize(team_tournament)
        self.wallet.refresh_from_db()
        wallet2.refresh_from_db()

        # Prize is 40 (20 * 2 teams), distributed among 2 members
        self.assertEqual(self.wallet.total_balance, Decimal('120.00'))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal('70.00'))
        self.assertEqual(wallet2.total_balance, Decimal('120.00'))
        self.assertEqual(wallet2.withdrawable_balance, Decimal('70.00'))
