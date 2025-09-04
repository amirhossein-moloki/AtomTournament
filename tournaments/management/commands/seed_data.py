import random
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, models
from tournaments.models import Tournament, Game, Match
from users.models import User, Team, TeamMembership
from wallet.services import process_transaction
from wallet.models import Transaction
from chat.models import Conversation, Message

# Constants for test data
FIRST_NAMES = ["علی", "رضا", "محمد", "حسین", "مهدی", "سارا", "مریم", "فاطمه", "زهرا", "نیما"]
LAST_NAMES = ["احمدی", "محمدی", "رضایی", "حسینی", "کریمی", "صادقی", "جعفری", "کاظمی", "قاسمی", "موسوی"]
TEAM_ADJECTIVES = ["شجاع", "سریع", "خشمگین", "افسانه‌ای", "طلایی", "نقره‌ای", "برنزی"]
TEAM_NOUNS = ["عقاب‌ها", "شیرها", "ببرها", "گرگ‌ها", "مارها", "جنگجویان", "قهرمانان"]
CHAT_MESSAGES = ["سلام، چطوری؟", "آماده‌ای برای مسابقه؟", "من برنده میشم!", "چه بازی خوبی بود!", "موفق باشی"]

class Command(BaseCommand):
    help = 'Seeds the database with realistic test data for various models.'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=0, help='The number of users to create.')
        parser.add_argument('--teams', type=int, default=0, help='The number of teams to create.')
        parser.add_argument('--tournaments', type=int, default=0, help='The number of tournaments to create.')
        parser.add_argument('--matches', type=int, default=0, help='The number of matches to create.')
        parser.add_argument('--transactions', type=int, default=0, help='The number of transactions to create.')
        parser.add_argument('--chats', type=int, default=0, help='The number of chat messages to create.')
        parser.add_argument('--clean', action='store_true', help='Delete existing data before seeding.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clean']:
            self.stdout.write(self.style.WARNING('Deleting all existing data...'))
            Message.objects.all().delete()
            Conversation.objects.all().delete()
            Transaction.objects.all().delete()
            Match.objects.all().delete()
            Tournament.objects.all().delete()
            Team.objects.all().delete()
            User.objects.filter(is_staff=False, is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Successfully deleted existing data.'))

        if options['users'] > 0: self.seed_users(options['users'])
        if options['teams'] > 0: self.seed_teams(options['teams'])
        if options['tournaments'] > 0: self.seed_tournaments(options['tournaments'])
        if options['matches'] > 0: self.seed_matches(options['matches'])
        if options['transactions'] > 0: self.seed_transactions(options['transactions'])
        if options['chats'] > 0: self.seed_chats(options['chats'])

        self.stdout.write(self.style.SUCCESS('Database seeding complete.'))

    def seed_users(self, count):
        self.stdout.write(f'Creating {count} new users...')
        # ... (logic is unchanged)
        users = []
        for i in range(count):
            username = f'user_{random.choice(FIRST_NAMES)}_{i}'
            phone_number = f'+98999{str(i).zfill(8)}'
            if User.objects.filter(username=username).exists() or User.objects.filter(phone_number=phone_number).exists(): continue
            user = User.objects.create_user(username=username, password='password123', email=f'{username}@example.com', phone_number=phone_number, first_name=random.choice(FIRST_NAMES), last_name=random.choice(LAST_NAMES))
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(users)} users.'))

    def seed_teams(self, count):
        self.stdout.write(f'Creating {count} new teams...')
        # ... (logic is unchanged)
        users = list(User.objects.filter(is_staff=False, is_superuser=False))
        if len(users) < 2: self.stdout.write(self.style.ERROR('Cannot create teams. Need at least 2 users.')); return
        teams_created = 0
        for i in range(count):
            team_name = f'{random.choice(TEAM_ADJECTIVES)} {random.choice(TEAM_NOUNS)}'
            if Team.objects.filter(name=team_name).exists(): continue
            captain = random.choice(users)
            team = Team.objects.create(name=team_name, captain=captain)
            TeamMembership.objects.create(user=captain, team=team)
            member_count = random.randint(0, team.max_members - 1)
            potential_members = [u for u in users if u != captain]
            members_to_add = random.sample(potential_members, min(len(potential_members), member_count))
            for member in members_to_add:
                if member.teams.count() < 10 and team.members.count() < team.max_members:
                    TeamMembership.objects.get_or_create(user=member, team=team)
            teams_created += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully created {teams_created} teams.'))

    def seed_tournaments(self, count):
        self.stdout.write(f'Creating {count} new tournaments...')
        # ... (logic is unchanged)
        game, _ = Game.objects.get_or_create(name="Default Game")
        now = timezone.now()
        for i in range(count):
            Tournament.objects.create(name=f'Tournament #{i}', game=game, type=random.choice(['individual', 'team']), start_date=now + datetime.timedelta(days=random.randint(1, 60)), end_date=now + datetime.timedelta(days=random.randint(61, 120)))
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} tournaments.'))

    def seed_matches(self, count):
        self.stdout.write(f'Creating {count} new matches...')
        # ... (logic is unchanged)
        tournaments, users, teams = list(Tournament.objects.all()), list(User.objects.filter(is_staff=False)), list(Team.objects.all())
        if not tournaments: self.stdout.write(self.style.ERROR('Cannot create matches. No tournaments found.')); return
        if len(users) < 2: self.stdout.write(self.style.ERROR('Cannot create individual matches. Need at least 2 users.'))
        if len(teams) < 2: self.stdout.write(self.style.ERROR('Cannot create team matches. Need at least 2 teams.'))
        matches_created = 0
        for i in range(count):
            tournament = random.choice(tournaments)
            try:
                if tournament.type == 'individual':
                    if len(users) < 2: continue
                    p1, p2 = random.sample(users, 2)
                    Match.objects.create(tournament=tournament, match_type='individual', round=random.randint(1, 5), participant1_user=p1, participant2_user=p2)
                elif tournament.type == 'team':
                    if len(teams) < 2: continue
                    t1, t2 = random.sample(teams, 2)
                    Match.objects.create(tournament=tournament, match_type='team', round=random.randint(1, 3), participant1_team=t1, participant2_team=t2)
                matches_created += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Could not create match: {e}"))
        self.stdout.write(self.style.SUCCESS(f'Successfully created {matches_created} matches.'))

    def seed_transactions(self, count):
        self.stdout.write(f'Creating {count} new transactions...')
        # ... (logic is unchanged)
        users = list(User.objects.filter(is_staff=False))
        if not users: self.stdout.write(self.style.ERROR('Cannot create transactions. No users found.')); return
        transaction_types = [t[0] for t in Transaction.TRANSACTION_TYPE_CHOICES]
        transactions_created = 0
        for i in range(count):
            user = random.choice(users)
            transaction_type = random.choice(transaction_types)
            amount = Decimal(random.randrange(10000, 500000))
            if transaction_type in ['withdrawal', 'entry_fee']:
                process_transaction(user, amount * 2, 'deposit', 'Initial seeding deposit')
            _, error = process_transaction(user=user, amount=amount, transaction_type=transaction_type, description=f'تراکنش تستی {transaction_type}')
            if error: self.stdout.write(self.style.ERROR(f"Could not create transaction for {user.username}: {error}"))
            else: transactions_created += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully created {transactions_created} transactions.'))

    def seed_chats(self, count):
        self.stdout.write(f'Creating {count} new chat messages...')
        users = list(User.objects.filter(is_staff=False))
        if len(users) < 2:
            self.stdout.write(self.style.ERROR('Cannot create chats. Need at least 2 users.'))
            return

        # Create a few conversations to populate
        num_conversations = max(1, count // 5) # Create 1 conversation for every 5 messages
        conversations = []
        for _ in range(num_conversations):
            participants = random.sample(users, 2)
            # Use get_or_create to avoid duplicate conversations
            # Note: This simple get_or_create doesn't handle M2M well. A more robust way is needed for production.
            # For seeding, we'll just create new ones.
            convo = Conversation.objects.create()
            convo.participants.set(participants)
            conversations.append(convo)

        if not conversations:
            self.stdout.write(self.style.ERROR('Could not create any conversations.'))
            return

        messages_created = 0
        for i in range(count):
            try:
                conversation = random.choice(conversations)
                sender = random.choice(list(conversation.participants.all()))
                Message.objects.create(
                    conversation=conversation,
                    sender=sender,
                    content=random.choice(CHAT_MESSAGES)
                )
                messages_created += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Could not create message: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully created {messages_created} messages.'))
