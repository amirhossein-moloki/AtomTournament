from django.db import models
from .models import User


class Level2AuthenticationRequest(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    selfie = models.ImageField(upload_to="level2_authentication/")
    id_card = models.ImageField(upload_to="level2_authentication/")
    status = models.CharField(max_length=20, choices=(("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")), default="pending")

    def __str__(self):
        return f"Level 2 Authentication Request for {self.user.username}"


import random
import string


def generate_random_text():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


class Level3AuthenticationRequest(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    video = models.FileField(upload_to="level3_authentication/")
    text_to_read = models.CharField(max_length=10, default=generate_random_text)
    status = models.CharField(max_length=20, choices=(("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")), default="pending")

    def __str__(self):
        return f"Level 3 Authentication Request for {self.user.username}"
