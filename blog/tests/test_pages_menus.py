from django.urls import reverse
from rest_framework import status

from blog.factories import PageFactory, MenuFactory, MenuItemFactory
from blog.tests.base import BaseAPITestCase


class PageAPITest(BaseAPITestCase):
    def test_create_page(self):
        self._authenticate_as_staff()
        url = reverse('page-list')
        data = {'title': 'New Page', 'slug': 'new-page', 'content': 'Some content.'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_pages(self):
        PageFactory.create_batch(3)
        url = reverse('page-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)


class MenuAPITest(BaseAPITestCase):
    def test_create_menu(self):
        self._authenticate_as_staff()
        url = reverse('menu-list')
        data = {'name': 'Main Menu', 'location': 'header'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_menus(self):
        MenuFactory.create_batch(2)
        url = reverse('menu-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class MenuItemAPITest(BaseAPITestCase):
    def test_create_menu_item(self):
        self._authenticate_as_staff()
        menu = MenuFactory()
        url = reverse('menuitem-list')
        data = {'menu': menu.pk, 'label': 'Home', 'url': '/'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
