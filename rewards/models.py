from django.db import models

from tournaments.models import Rank
from users.models import User
from common.fields import OptimizedImageField
from common.utils.files import get_sanitized_upload_path


class Wheel(models.Model):
    name = models.CharField(max_length=100)
    required_rank = models.ForeignKey(Rank, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Prize(models.Model):
    wheel = models.ForeignKey(Wheel, on_delete=models.CASCADE, related_name="prizes")
    name = models.CharField(max_length=100)
    image = OptimizedImageField(upload_to=get_sanitized_upload_path)
    chance = models.FloatField()

    def __str__(self):
        return self.name


class Spin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wheel = models.ForeignKey(Wheel, on_delete=models.CASCADE)
    prize = models.ForeignKey(Prize, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "wheel")
