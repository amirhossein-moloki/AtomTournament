from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Tournament, Game
from datetime import datetime, timedelta

class TournamentModelTest(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")

    def test_end_date_after_start_date(self):
        """
        Tests that the end date is after the start date.
        """
        tournament = Tournament(
            name="Test Tournament",
            game=self.game,
            start_date=datetime.now(),
            end_date=datetime.now() - timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            tournament.full_clean()

    def test_entry_fee_for_paid_tournament(self):
        """
        Tests that an entry fee is set for paid tournaments.
        """
        tournament = Tournament(
            name="Test Tournament",
            game=self.game,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=1),
            is_free=False
        )
        with self.assertRaises(ValidationError):
            tournament.full_clean()
