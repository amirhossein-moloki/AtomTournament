from django.urls import path
from .views import BotSettingsAPIView

app_name = 'atomgamebot'

urlpatterns = [
    path('status/', BotSettingsAPIView.as_view(), name='bot-settings-status'),
]
