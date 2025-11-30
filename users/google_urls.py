from django.urls import path
from . import google_views

urlpatterns = [
    path('login/', google_views.GoogleLoginRedirect.as_view(), name='google-login'),
    path('callback/', google_views.GoogleCallback.as_view(), name='google-callback'),
]
