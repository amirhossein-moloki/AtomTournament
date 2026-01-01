from django.db import migrations
from django.db.models import Count


def handle_duplicate_emails(apps, schema_editor):
    User = apps.get_model('users', 'User')
    duplicate_emails = (
        User.objects.values('email')
        .annotate(email_count=Count('email'))
        .filter(email_count__gt=1)
    )

    for item in duplicate_emails:
        email = item['email']
        if not email:
            continue

        users_with_duplicate_email = User.objects.filter(email=email).order_by('id')

        # Keep the first user
        users_with_duplicate_email.first()

        # For the rest of the users, update their email to a unique value
        for i, user_to_update in enumerate(users_with_duplicate_email[1:]):
            user_to_update.email = f"duplicate_{user_to_update.id}_{i}_{email}"
            user_to_update.save(update_fields=['email'])


def reverse_handle_duplicate_emails(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_profile_picture'),
    ]

    operations = [
        migrations.RunPython(handle_duplicate_emails, reverse_handle_duplicate_emails),
    ]
