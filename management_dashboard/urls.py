from django.urls import path
from . import views

app_name = 'management_dashboard'

urlpatterns = [
    path('seed/', views.seed_data_view, name='seed_data'),
]
