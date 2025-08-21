from django.contrib import messages

# To make this mixin more concrete, we can import models and check conditions.
# Note: This creates a dependency from 'tournaments' to 'support'.
# A more decoupled approach might use signals or a dedicated notifications app.
from support.models import Ticket
from tournaments.models import Match


class AdminAlertsMixin:
    """
    A mixin for the Django admin to show important alerts on the changelist page.

    This mixin checks for specific conditions (e.g., new support tickets)
    and uses the Django messages framework to display them.
    """

    def changelist_view(self, request, extra_context=None):
        # --- Alert Examples ---

        # 1. Alert for open support tickets.
        # This will be shown on any admin page that uses this mixin.
        try:
            # Corrected model name to 'Ticket' and status to 'open'
            open_tickets_count = Ticket.objects.filter(status="open").count()
            if open_tickets_count > 0:
                message = f"هشدار: {open_tickets_count} تیکت پشتیبانی باز منتظر بررسی است."
                messages.add_message(
                    request, messages.WARNING, message, extra_tags="warning"
                )
        except Exception:
            # Fails silently if the Ticket model is not available for some reason
            pass

        # 2. Alert for disputed matches.
        try:
            disputed_matches_count = Match.objects.filter(is_disputed=True).count()
            if disputed_matches_count > 0:
                message = (
                    f"توجه: {disputed_matches_count} مسابقه مورد مناقشه قرار گرفته "
                    f"و نیاز به بررسی دارد."
                )
                messages.add_message(
                    request, messages.INFO, message, extra_tags="info"
                )
        except Exception:
            pass

        # Call the original changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)
