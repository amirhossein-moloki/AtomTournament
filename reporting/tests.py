from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
import datetime

from users.models import User, Referral
from tournaments.models import Game, Tournament, Participant
from wallet.models import Wallet, Transaction
from .services import (
    generate_revenue_report,
    generate_players_report,
    generate_financial_report,
    generate_tournament_report,
    generate_marketing_report,
)
from rest_framework.test import APIClient

class ReportingServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole test class."""
        cls.game = Game.objects.create(name="Test Game")
        cls.admin_user = User.objects.create_superuser(username="admin", password="password", email="admin@test.com", phone_number="+989000000000")
        cls.user1 = User.objects.create_user(username="user1", password="password", phone_number="+989123456789")
        cls.user2 = User.objects.create_user(username="user2", password="password", phone_number="+989123456780")

        Referral.objects.create(referrer=cls.user1, referred=cls.user2)

        cls.wallet1 = Wallet.objects.get(user=cls.user1)
        cls.wallet2 = Wallet.objects.get(user=cls.user2)

        cls.tournament1 = Tournament.objects.create(
            name="Test Tournament 1",
            game=cls.game,
            start_date=timezone.now() - datetime.timedelta(days=10),
            end_date=timezone.now() - datetime.timedelta(days=9),
            is_free=False,
            entry_fee=10000,
            max_participants=10,
        )
        Participant.objects.create(user=cls.user1, tournament=cls.tournament1)
        Participant.objects.create(user=cls.user2, tournament=cls.tournament1)

        cls.tournament2 = Tournament.objects.create(
            name="Test Tournament 2",
            game=cls.game,
            start_date=timezone.now() - datetime.timedelta(days=5),
            end_date=timezone.now() - datetime.timedelta(days=4),
            is_free=False,
            entry_fee=20000
        )
        Participant.objects.create(user=cls.user1, tournament=cls.tournament2)

        Transaction.objects.create(wallet=cls.wallet1, amount=Decimal('10000'), transaction_type='entry_fee', description=f"Entry fee for tournament: {cls.tournament1.name}")
        Transaction.objects.create(wallet=cls.wallet2, amount=Decimal('10000'), transaction_type='entry_fee', description=f"Entry fee for tournament: {cls.tournament1.name}")
        Transaction.objects.create(wallet=cls.wallet1, amount=Decimal('20000'), transaction_type='entry_fee', description=f"Entry fee for tournament: {cls.tournament2.name}")
        Transaction.objects.create(wallet=cls.wallet1, amount=Decimal('5000'), transaction_type='prize', description="Prize for something")
        Transaction.objects.create(wallet=cls.wallet2, amount=Decimal('1000'), transaction_type='withdrawal')

    def test_generate_revenue_report(self):
        report = generate_revenue_report()
        self.assertEqual(report['summary']['total_revenue'], Decimal('40000.00'))
        self.assertEqual(report['summary']['platform_share'], Decimal('12000.00'))

    def test_generate_players_report(self):
        report = generate_players_report()
        self.assertEqual(report['summary']['total_users'], 3) # admin, user1, user2
        self.assertEqual(report['summary']['active_players'], 2)

    def test_generate_financial_report(self):
        report = generate_financial_report()
        self.assertEqual(report['summary']['total_revenue'], Decimal('40000.00'))
        self.assertEqual(report['summary']['total_prize_paid'], Decimal('5000.00'))
        self.assertEqual(report['summary']['net_profit'], Decimal('12000.00'))
        self.assertEqual(report['cash_flow'][0]['expenses'], Decimal('6000.00')) # prize + withdrawal

    def test_generate_tournament_report(self):
        report = generate_tournament_report()
        self.assertEqual(len(report['all_tournaments']), 2)
        t1_data = next(t for t in report['all_tournaments'] if t['name'] == 'Test Tournament 1')
        self.assertEqual(t1_data['participant_count'], 2)
        self.assertEqual(t1_data['fill_rate'], 20.0)

    def test_generate_marketing_report(self):
        report = generate_marketing_report()
        self.assertEqual(report['summary']['total_referred_users'], 1)
        self.assertEqual(report['by_referrer'][0]['referrer__username'], 'user1')
        self.assertEqual(report['by_referrer'][0]['new_users'], 1)
        # user2 was referred and paid 10000 entry fee
        self.assertEqual(report['summary']['revenue_from_referred_users'], Decimal('10000.00'))


class ReportingAPITests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username="admin", password="password", email="admin@test.com", phone_number="+989000000000")
        self.normal_user = User.objects.create_user(username="user", password="password", phone_number="+989123456789")
        self.client = APIClient()

    def test_api_permissions(self):
        """Test that only admin users can access the reporting API."""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get('/api/reporting/revenue/')
        self.assertEqual(response.status_code, 403) # Forbidden

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/reporting/revenue/')
        self.assertEqual(response.status_code, 200)

    def test_csv_export(self):
        """Test that CSV export works."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/reporting/revenue/?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        content = response.content.decode('utf-8')
        self.assertIn('Revenue Report Summary', content)
        self.assertIn('Total Revenue', content)
