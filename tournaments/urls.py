from django.urls import include, path

from .routers import router
from .views import AdminReportListView, AdminWinnerSubmissionListView

urlpatterns = [
    path("", include(router.urls)),
    path("admin/reports/", AdminReportListView.as_view(), name="admin-reports"),
    path(
        "admin/winner-submissions/",
        AdminWinnerSubmissionListView.as_view(),
        name="admin-winner-submissions",
    ),
]
