from django.urls import path
from . import views

app_name = 'management_dashboard'

# TODO: This URL is for an incomplete feature. Uncomment once seed_data_view is implemented.
urlpatterns = [
    # path('seed/', views.seed_data_view, name='seed_data'),
]
