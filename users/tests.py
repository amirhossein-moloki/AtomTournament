from decimal import Decimal
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from blog.tests.base import BaseAPITestCase
from wallet.models import Transaction, Wallet
from tournaments.models import Game
from .models import User, OTP
from .services import verify_otp_service

class UserViewSetAPITest(BaseAPITestCase):

    def test_user_can_update_own_profile(self):
        self._authenticate()
        url = reverse('user-detail', kwargs={'pk': self.user.pk})
        data = {'username': 'new_username'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'new_username')

    def test_user_cannot_update_other_profile(self):
        self._authenticate()
        other_user = self.staff_user
        url = reverse('user-detail', kwargs={'pk': other_user.pk})
        data = {'username': 'should_not_work'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_update_other_profile(self):
        self._authenticate_as_staff()
        other_user = self.user
        url = reverse('user-detail', kwargs={'pk': other_user.pk})
        data = {'username': 'admin_was_here'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other_user.refresh_from_db()
        self.assertEqual(other_user.username, 'admin_was_here')

    def test_admin_can_delete_user(self):
        self._authenticate_as_staff()
        user_to_delete = self.user
        url = reverse('user-detail', kwargs={'pk': user_to_delete.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=user_to_delete.pk).exists())

    def test_setting_in_game_id_ignores_existing_profile_picture_url(self):
        self._authenticate()
        self.user.profile_picture = SimpleUploadedFile("avatar.png", b"file_content", content_type="image/png")
        self.user.save()
        game = Game.objects.create(name="Test Game", description="desc")
        url = reverse('user-detail', kwargs={'pk': self.user.pk})
        data = {'profile_picture': self.user.profile_picture.url, 'in_game_ids': [{'game': game.id, 'player_id': 'player-123'}]}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.in_game_ids.count(), 1)
        self.assertEqual(self.user.in_game_ids.first().player_id, 'player-123')
        self.assertTrue(self.user.profile_picture)

    def test_setting_in_game_id_with_formdata_profile_picture_url(self):
        self._authenticate()
        self.user.profile_picture = SimpleUploadedFile("avatar.png", b"file_content", content_type="image/png")
        self.user.save()
        game = Game.objects.create(name="Test Game", description="desc")
        url = reverse('user-detail', kwargs={'pk': self.user.pk})
        data = {'profile_picture': self.user.profile_picture.url, 'in_game_ids': f'[{{"game": {game.id}, "player_id": "player-456"}}]'}
        response = self.client.patch(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.in_game_ids.count(), 1)
        self.assertEqual(self.user.in_game_ids.first().player_id, 'player-456')
        self.assertTrue(self.user.profile_picture)

class TopPlayersByRankAPITest(BaseAPITestCase):
    def test_top_players_by_rank_includes_winnings_and_avatar(self):
        prize_amount = Decimal("150.00")
        self.user.score = 10
        self.user.profile_picture = SimpleUploadedFile("avatar.png", b"file_content", content_type="image/png")
        self.user.save()
        wallet, _ = Wallet.objects.get_or_create(user=self.user)
        Transaction.objects.create(wallet=wallet, amount=prize_amount, transaction_type=Transaction.TransactionType.PRIZE)
        response = self.client.get(reverse("top-players-by-rank"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        top_player = response.data[0]
        self.assertEqual(top_player["id"], self.user.id)
        self.assertEqual(top_player["total_winnings"], str(prize_amount))
        self.assertIsNotNone(top_player.get("profile_picture"))

class OTPServiceTest(BaseAPITestCase):
    def test_verify_otp_handles_existing_duplicate_case_insensitive_emails(self):
        email1 = "DuplicateCase@Example.com"
        email2 = "duplicatecase@example.com"
        user1 = User.objects.create(username=email1, email=email1, phone_number="+989999999991")
        user2 = User.objects.create(username=email2, email=email2, phone_number="+989999999992")
        initial_user_count = User.objects.count()
        otp_code = "123456"
        OTP.objects.create(identifier=email1, code=otp_code)
        verified_user = verify_otp_service(identifier=email1, code=otp_code)
        self.assertIsNotNone(verified_user)
        self.assertIn(verified_user.pk, [user1.pk, user2.pk])
        self.assertEqual(User.objects.count(), initial_user_count)

class UserSignalTests(TestCase):
    def test_new_user_creation_signal(self):
        user = User.objects.create_user(username='newusertest', phone_number='+989123456789', password='testpassword')
        user.refresh_from_db()
        self.assertTrue(hasattr(user, 'wallet'))
        self.assertEqual(user.wallet.token_balance, 1000)
        self.assertIsNotNone(user.referral_code)
        self.assertTrue(len(user.referral_code) > 0)
