from django.contrib import admin

from .models import Transaction, Wallet


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 1
    readonly_fields = ("amount", "transaction_type", "timestamp", "description")
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "total_balance", "withdrawable_balance")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
    inlines = [TransactionInline]
    readonly_fields = ("total_balance", "withdrawable_balance")

    fieldsets = (
        ("Owner", {"fields": ("user",)}),
        ("Balance", {"fields": ("total_balance", "withdrawable_balance")}),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "amount", "transaction_type", "timestamp")
    list_filter = ("transaction_type", "timestamp")
    search_fields = ("wallet__user__username", "description")
    autocomplete_fields = ("wallet",)
    readonly_fields = ("wallet", "amount", "transaction_type", "timestamp")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
