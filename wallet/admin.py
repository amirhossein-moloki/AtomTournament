# Django Imports
from django.contrib import admin
from django.db import models

# 3rd-party Imports
from unfold.admin import ModelAdmin, TabularInline
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django_select2.forms import Select2Widget

# Local Imports
from .models import Transaction, Wallet, WithdrawalRequest

# --- Resources for django-import-export ---

class WalletResource(resources.ModelResource):
    class Meta:
        model = Wallet

class TransactionResource(resources.ModelResource):
    class Meta:
        model = Transaction


# --- Inlines (Upgraded) ---

class TransactionInline(TabularInline):
    model = Transaction
    extra = 0
    show_change_link = True


# --- ModelAdmins (Upgraded) ---

@admin.register(Wallet)
class WalletAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = WalletResource
    list_display = ("user", "total_balance", "withdrawable_balance", "token_balance")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
    inlines = [TransactionInline]

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

    fieldsets = (
        ("Owner", {"fields": ("user",), "classes": ("tab",)}),
        (
            "Balance",
            {
                "fields": ("total_balance", "withdrawable_balance", "token_balance"),
                "classes": ("tab",),
            },
        ),
    )


@admin.register(Transaction)
class TransactionAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = TransactionResource
    list_display = ("wallet", "amount", "transaction_type", "timestamp", "status")
    list_filter = ("transaction_type", "timestamp", "status")
    search_fields = ("wallet__user__username", "description")
    autocomplete_fields = ("wallet",)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    list_display = (
        "user",
        "amount",
        "card_number",
        "sheba_number",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("user__username",)
    list_editable = ("status",)
    autocomplete_fields = ("user",)

    @admin.display(description="شماره کارت")
    def card_number(self, obj):
        return getattr(obj.user.wallet, "card_number", None)

    @admin.display(description="شماره شبا")
    def sheba_number(self, obj):
        return getattr(obj.user.wallet, "sheba_number", None)
