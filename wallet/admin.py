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
from .models import Transaction, Wallet

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
    readonly_fields = ("amount", "transaction_type", "timestamp", "description")
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# --- ModelAdmins (Upgraded) ---

@admin.register(Wallet)
class WalletAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = WalletResource
    list_display = ("user", "total_balance", "withdrawable_balance")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
    inlines = [TransactionInline]
    readonly_fields = ("total_balance", "withdrawable_balance")

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

    fieldsets = (
        ("Owner", {"fields": ("user",), "classes": ("tab",)}),
        ("Balance", {"fields": ("total_balance", "withdrawable_balance"), "classes": ("tab",)}),
    )


@admin.register(Transaction)
class TransactionAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = TransactionResource
    list_display = ("wallet", "amount", "transaction_type", "timestamp")
    list_filter = ("transaction_type", "timestamp")
    search_fields = ("wallet__user__username", "description")
    autocomplete_fields = ("wallet",)
    readonly_fields = ("wallet", "amount", "transaction_type", "timestamp", "description")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
