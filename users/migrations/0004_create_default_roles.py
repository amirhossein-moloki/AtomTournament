from django.db import migrations

def create_default_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Role = apps.get_model("users", "Role")
    Permission = apps.get_model("auth", "Permission")

    # Create groups
    admin_group, _ = Group.objects.get_or_create(name="Admin")
    manager_group, _ = Group.objects.get_or_create(name="Tournament Manager")
    support_group, _ = Group.objects.get_or_create(name="Support")
    user_group, _ = Group.objects.get_or_create(name="User")

    # Create roles
    Role.objects.get_or_create(group=admin_group, description="Superuser with all permissions.")
    Role.objects.get_or_create(group=manager_group, description="Can manage tournaments.")
    Role.objects.get_or_create(group=support_group, description="Can handle user support.")
    Role.objects.get_or_create(group=user_group, description="Default user role.", is_default=True)

    # Assign permissions
    # Admin gets all permissions
    admin_group.permissions.set(Permission.objects.all())

    # Tournament Manager permissions
    tournament_permissions = Permission.objects.filter(
        content_type__app_label="tournaments"
    )
    manager_group.permissions.set(tournament_permissions)

    # Support permissions (example: can view users and tournaments)
    support_permissions = Permission.objects.filter(
        content_type__app_label__in=["users", "tournaments"],
        codename__startswith="view_"
    )
    support_group.permissions.set(support_permissions)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_remove_user_role_role"),
    ]

    operations = [
        migrations.RunPython(create_default_roles),
    ]
