from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from faker import Faker
import random

from users.models import User
from tournaments.models import Game, Tournament
from teams.models import Team, TeamMembership
from django.db import transaction

class Command(BaseCommand):
    help = 'Sets up a test tournament with users and teams.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting the test tournament setup...'))
        fake = Faker()

        try:
            with transaction.atomic():
                # 1. Get or create 'amir' user
                amir, created = User.objects.get_or_create(
                    username='amir',
                    defaults={'first_name': 'Amir', 'email': 'amir@example.com'}
                )
                if created:
                    amir.set_password('password123')
                    # Generate a unique phone number
                    while True:
                        phone_number = f"+98912{random.randint(1000000, 9999999)}"
                        if not User.objects.filter(phone_number=phone_number).exists():
                            amir.phone_number = phone_number
                            amir.save()
                            break
                    self.stdout.write(self.style.SUCCESS('User "amir" created.'))
                else:
                    self.stdout.write(self.style.SUCCESS('User "amir" already exists.'))

                # 2. Find an active game
                active_game = Game.objects.filter(status='active').first()
                if not active_game:
                    self.stdout.write(self.style.ERROR('No active game found. Please create one first.'))
                    return
                self.stdout.write(self.style.SUCCESS(f'Using active game: "{active_game.name}"'))

                # 3. Create the tournament
                now = timezone.now()
                tournament = Tournament.objects.create(
                    name='Automated Battle Royale Tournament',
                    creator=amir,
                    game=active_game,
                    type='team',
                    mode='battle_royale',
                    max_participants=100,
                    team_size=2,
                    registration_start_date=now,
                    registration_end_date=now + timedelta(minutes=10),
                    start_date=now + timedelta(minutes=15),
                    end_date=now + timedelta(minutes=20) # Finishes 20 minutes from creation
                )
                self.stdout.write(self.style.SUCCESS(f'Tournament "{tournament.name}" created.'))

                # 4. Create 100 new users
                self.stdout.write('Creating 100 test users...')
                users = []
                for i in range(100):
                    username = fake.user_name() + str(random.randint(100, 999))
                    while User.objects.filter(username=username).exists():
                         username = fake.user_name() + str(random.randint(100, 999))

                    phone_number = f"+98935{random.randint(1000000, 9999999)}"
                    while User.objects.filter(phone_number=phone_number).exists():
                        phone_number = f"+98935{random.randint(1000000, 9999999)}"

                    user = User.objects.create_user(
                        username=username,
                        password='password123',
                        phone_number=phone_number
                    )
                    users.append(user)
                    self.stdout.write(f'  Created user {i + 1}/100: {user.username}')
                self.stdout.write(self.style.SUCCESS('100 test users created.'))

                # 5. Create 50 teams of 2
                self.stdout.write('Creating 50 teams and registering them...')
                user_iter = iter(users)
                for i in range(50):
                    captain = next(user_iter)
                    member = next(user_iter)

                    team = Team.objects.create(
                        name=f'Team {i + 1} - {fake.word().capitalize()}',
                        captain=captain,
                        max_members=2
                    )

                    TeamMembership.objects.create(team=team, user=captain)
                    TeamMembership.objects.create(team=team, user=member)

                    # 6. Register team for the tournament
                    tournament.teams.add(team)
                    self.stdout.write(f'  Created and registered Team {i + 1}/50.')

            self.stdout.write(self.style.SUCCESS('Test tournament setup finished successfully!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))
            self.stdout.write(self.style.ERROR('Transaction rolled back.'))
