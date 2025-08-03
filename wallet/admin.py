from django.contrib import admin
from .models import Wallet, Transaction

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('amount', 'transaction_type', 'timestamp', 'description')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_balance', 'withdrawable_balance')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'total_balance', 'withdrawable_balance')
    inlines = [TransactionInline]

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'timestamp')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('wallet__user__username', 'description')
    readonly_fields = ('wallet', 'amount', 'transaction_type', 'timestamp', 'description')
