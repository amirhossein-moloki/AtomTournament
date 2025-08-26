from django.db import models

class Report(models.Model):
    """
    Stores the results of generated reports to act as a cache.
    """
    REPORT_TYPE_CHOICES = [
        ("revenue_report", "Revenue Report"),
        ("players_report", "Players Report"),
        ("tournament_report", "Tournament Report"),
        ("finance_report", "Finance Report"),
        ("marketing_roi_report", "Marketing ROI Report"),
    ]

    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES)
    generated_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()
    filters = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Generated Report"
        verbose_name_plural = "Generated Reports"
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=['report_type']),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} generated at {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
