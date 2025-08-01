from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Wheel, Prize, Spin
from tournaments.models import Rank

User = get_user_model()

class RewardModelTests(TestCase):
    def test_reward_creation(self):
        user = User.objects.create_user(username="testuser", password="password", phone_number="+123")
        rank = Rank.objects.create(name="Gold", required_score=2000)
        wheel = Wheel.objects.create(name="Gold Wheel", required_rank=rank)
        prize = Prize.objects.create(wheel=wheel, name="Gold Prize", chance=0.1)
        spin = Spin.objects.create(user=user, wheel=wheel, prize=prize)

        self.assertEqual(wheel.prizes.count(), 1)
        self.assertEqual(spin.user, user)
