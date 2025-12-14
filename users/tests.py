from django.urls import reverse
from rest_framework import status
from blog.tests.base import BaseAPITestCase  # Reusing the base test case for convenience
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
