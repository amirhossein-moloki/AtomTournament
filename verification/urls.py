from django.urls import path
from .views import VerificationLevel2View, VerificationLevel3View, AdminVerificationView

urlpatterns = [
    path('level2/', VerificationLevel2View.as_view(), name='verification-level2'),
    path('level3/', VerificationLevel3View.as_view(), name='verification-level3'),
    path('admin/<int:pk>/', AdminVerificationView.as_view(), name='admin-verification'),
]
