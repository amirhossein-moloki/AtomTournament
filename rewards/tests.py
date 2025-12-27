from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from tournaments.models import Rank

from .models import Prize, Spin, Wheel

User = get_user_model()


class RewardModelTests(TestCase):
    def test_reward_creation(self):
        user = User.objects.create_user(
            username="testuser", password="password", phone_number="+123"
        )
        rank = Rank.objects.create(name="Gold", required_score=2000)
        wheel = Wheel.objects.create(name="Gold Wheel", required_rank=rank)
        prize = Prize.objects.create(wheel=wheel, name="Gold Prize", chance=0.1)
        spin = Spin.objects.create(user=user, wheel=wheel, prize=prize)

        self.assertEqual(wheel.prizes.count(), 1)
        self.assertEqual(spin.user, user)


class WheelViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.rank1 = Rank.objects.create(name="Bronze", required_score=0)
        self.rank2 = Rank.objects.create(name="Silver", required_score=100)
        self.rank3 = Rank.objects.create(name="Gold", required_score=200)

        self.user_low_rank = User.objects.create_user(
            username="lowrank", password="p", phone_number="+101", score=0, rank=self.rank1
        )
        self.user_mid_rank = User.objects.create_user(
            username="midrank", password="p", phone_number="+103", score=100, rank=self.rank2
        )
        self.user_high_rank = User.objects.create_user(
            username="highrank", password="p", phone_number="+102", score=200, rank=self.rank3
        )

        self.wheel = Wheel.objects.create(name="Test Wheel", required_rank=self.rank2)
        self.prize = Prize.objects.create(
            wheel=self.wheel, name="Test Prize", chance=1.0
        )

        self.spin_url = f"/api/rewards/wheels/{self.wheel.pk}/spin/"

    def tearDown(self):
        User.objects.all().delete()
        Rank.objects.all().delete()
        Wheel.objects.all().delete()
        Prize.objects.all().delete()
        Spin.objects.all().delete()

    def test_spin_unauthenticated(self):
        response = self.client.post(self.spin_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_spin_insufficient_rank(self):
        self.client.force_authenticate(user=self.user_low_rank)
        response = self.client.post(self.spin_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["error"],
            "You do not have the required rank to spin this wheel.",
        )

    def test_spin_success_exact_rank(self):
        self.client.force_authenticate(user=self.user_mid_rank)
        response = self.client.post(self.spin_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Spin.objects.filter(user=self.user_mid_rank, wheel=self.wheel).exists()
        )

    def test_spin_success_higher_rank(self):
        self.client.force_authenticate(user=self.user_high_rank)
        response = self.client.post(self.spin_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Spin.objects.filter(user=self.user_high_rank, wheel=self.wheel).exists()
        )

    def test_spin_already_spun(self):
        # First spin
        Spin.objects.create(
            user=self.user_high_rank, wheel=self.wheel, prize=self.prize
        )

        # Try to spin again
        self.client.force_authenticate(user=self.user_high_rank)
        response = self.client.post(self.spin_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "You have already spun this wheel.")

    def test_list_wheels(self):
        self.client.force_authenticate(user=self.user_low_rank)
        response = self.client.get("/api/rewards/wheels/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], self.wheel.name)
