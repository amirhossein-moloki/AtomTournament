import secrets
import string

from django.core.management.base import BaseCommand
from users.models import User

class Command(BaseCommand):
    help = 'Resets the password for all users and prints the new passwords.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting password reset for all users..."))

        users = User.objects.all()
        if not users.exists():
            self.stdout.write(self.style.NOTICE("No users found in the database."))
            return

        alphabet = string.ascii_letters + string.digits

        for user in users:
            new_password = ''.join(secrets.choice(alphabet) for i in range(12))
            user.set_password(new_password)
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully reset password for user: '{user.username}'. "
                    f"New password: {new_password}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Password reset process completed for all users."))
