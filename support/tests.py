from django.urls import reverse
from rest_framework import status
from blog.tests.base import BaseAPITestCase
from .models import Ticket, TicketMessage
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO

class SupportTicketAPITest(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.ticket = Ticket.objects.create(user=self.user, title="Test Ticket")

    def test_create_ticket_with_attachment(self):
        self._authenticate()
        url = reverse('ticket-list')
        # Create a dummy image file
        file = SimpleUploadedFile("file.png", b"file_content", content_type="image/png")
        data = {
            'title': 'New Ticket with Attachment',
            'content': 'Please see attached file.',
            'attachment': file
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Ticket.objects.filter(title='New Ticket with Attachment').exists())
        new_ticket = Ticket.objects.get(title='New Ticket with Attachment')
        self.assertEqual(new_ticket.messages.count(), 1)
        self.assertEqual(new_ticket.messages.first().attachments.count(), 1)

    def test_user_can_update_own_ticket(self):
        self._authenticate()
        url = reverse('ticket-detail', kwargs={'pk': self.ticket.pk})
        data = {'title': 'Updated Title'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, 'Updated Title')

    def test_admin_can_update_other_ticket(self):
        self._authenticate_as_staff()
        url = reverse('ticket-detail', kwargs={'pk': self.ticket.pk})
        data = {'status': 'closed'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'closed')

    def test_user_cannot_update_other_ticket(self):
        other_ticket = Ticket.objects.create(user=self.staff_user, title="Other's Ticket")
        self._authenticate() # as normal user
        url = reverse('ticket-detail', kwargs={'pk': other_ticket.pk})
        data = {'title': 'Should Not Work'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
