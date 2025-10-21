from django.contrib.auth import get_user_model

User = get_user_model()


def should_never_lockout_staff(request):
    """
    A callable for django-axes that returns True if the user is a staff member,
    preventing them from being locked out.
    """
    username = request.POST.get("username")
    if not username:
        return False

    try:
        user = User.objects.get(username=username)
        return user.is_staff
    except User.DoesNotExist:
        return False
