from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from blog.tests.base import BaseAPITestCase  # Reusing the base test case for convenience
from wallet.models import Transaction, Wallet
from tournaments.models import Game
from .models import User

class UserViewSetAPITest(BaseAPITestCase):

    def test_user_can_update_own_profile(self):
        """
        Ensures a regular user can update their own profile.
        """
        self._authenticate()
        url = reverse('user-detail', kwargs={'pk': self.user.pk})
        data = {'username': 'new_username'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'new_username')

    def test_user_cannot_update_other_profile(self):
        """
        Ensures a regular user cannot update another user's profile.
        """
        self._authenticate()
        other_user = self.staff_user # Another user
        url = reverse('user-detail', kwargs={'pk': other_user.pk})
        data = {'username': 'should_not_work'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_update_other_profile(self):
        """
        Ensures an admin can update another user's profile.
        """
        self._authenticate_as_staff()
        other_user = self.user # The regular user
        url = reverse('user-detail', kwargs={'pk': other_user.pk})
        data = {'username': 'admin_was_here'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other_user.refresh_from_db()
        self.assertEqual(other_user.username, 'admin_was_here')

    def test_admin_can_delete_user(self):
        """
        Ensures an admin can delete a user.
        """
        self._authenticate_as_staff()
        user_to_delete = self.user
        url = reverse('user-detail', kwargs={'pk': user_to_delete.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=user_to_delete.pk).exists())

    def test_setting_in_game_id_ignores_existing_profile_picture_url(self):
        """
        Ensure users with an existing profile picture can still update their in-game IDs
        when the client sends back the current profile picture URL. Previously the
        ImageField validator raised "Upload a valid image" for the URL string and the
        request failed with 400, so the in-game ID never got saved.
        """
        self._authenticate()

        # Create a stored profile picture for the user
        self.user.profile_picture = SimpleUploadedFile(
            "avatar.png",
            (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\x0cIDATx\x9cc````\x00\x00\x00\x04\x00\x01"
                b"\x0b\xe7\x02\x9a\x00\x00\x00\x00IEND\xaeB`\x82"
            ),
            content_type="image/png",
        )
        self.user.save()

        game = Game.objects.create(name="Test Game", description="desc")

        url = reverse('user-detail', kwargs={'pk': self.user.pk})
        data = {
            'profile_picture': self.user.profile_picture.url,
            'in_game_ids': [
                {
                    'game': game.id,
                    'player_id': 'player-123',
                }
            ],
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.in_game_ids.count(), 1)
        self.assertEqual(self.user.in_game_ids.first().player_id, 'player-123')
        self.assertTrue(self.user.profile_picture)

    def test_setting_in_game_id_with_formdata_profile_picture_url(self):
        """
        The same scenario as above, but with multipart/form-data payloads that include
        the stored profile_picture URL as a string. The serializer should drop the
        non-file value so the in-game ID update succeeds.
        """
        self._authenticate()

        # Create a stored profile picture for the user
        self.user.profile_picture = SimpleUploadedFile(
            "avatar.png",
            (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\x0cIDATx\x9cc````\x00\x00\x00\x04\x00\x01"
                b"\x0b\xe7\x02\x9a\x00\x00\x00\x00IEND\xaeB`\x82"
            ),
            content_type="image/png",
        )
        self.user.save()

        game = Game.objects.create(name="Test Game", description="desc")

        url = reverse('user-detail', kwargs={'pk': self.user.pk})
        data = {
            'profile_picture': self.user.profile_picture.url,
            'in_game_ids': """
                [
                    {
                        "game": %d,
                        "player_id": "player-456"
                    }
                ]
            """
            % game.id,
        }

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
        self.user.profile_picture = SimpleUploadedFile(
            "avatar.png",
            (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\x0cIDATx\x9cc````\x00\x00\x00\x04\x00\x01"
                b"\x0b\xe7\x02\x9a\x00\x00\x00\x00IEND\xaeB`\x82"
            ),
            content_type="image/png",
        )
        self.user.save()

        wallet, _ = Wallet.objects.get_or_create(user=self.user)
        Transaction.objects.create(
            wallet=wallet,
            amount=prize_amount,
            transaction_type=Transaction.TransactionType.PRIZE,
        )

        response = self.client.get(reverse("top-players-by-rank"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        top_player = response.data[0]

        self.assertEqual(top_player["id"], self.user.id)
        self.assertEqual(top_player["total_winnings"], str(prize_amount))
        self.assertIsNotNone(top_player.get("profile_picture"))
