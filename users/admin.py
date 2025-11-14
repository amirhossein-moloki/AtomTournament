# Django Imports
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models

# 3rd-party Imports
from unfold.admin import ModelAdmin, TabularInline
from simple_history.admin import SimpleHistoryAdmin
from django_select2.forms import Select2Widget

# Local Imports
from .models import (
    InGameID,
    OTP,
    Role,
    User,
)

# --- Inlines (using Unfold's TabularInline) ---

class InGameIDInline(TabularInline):
    model = InGameID
    extra = 1
    autocomplete_fields = ("game",)
    classes = ["collapse"]


# --- ModelAdmins (Upgraded with Unfold and other features) ---

@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin, ModelAdmin):
    list_display = ("username", "email", "phone_number", "score", "rank", "is_staff", "is_phone_verified")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "rank", "is_phone_verified")
    autocomplete_fields = ("rank", "groups")
    inlines = [InGameIDInline]  # TeamMembershipInline is on TeamAdmin
    readonly_fields = ("score", "rank", "last_login", "date_joined")

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "phone_number"), "classes": ("tab",)}),
        ("Game Profile", {"fields": ("score", "rank", "profile_picture"), "classes": ("tab",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "is_phone_verified", "groups", "user_permissions"), "classes": ("tab",)}),
        ("Important dates", {"fields": ("last_login", "date_joined"), "classes": ("tab",)}),
    )

    actions = ["reset_score"]

    def reset_score(self, request, queryset):
        updated_count = queryset.update(score=0)
        self.message_user(request, f"{updated_count} users had their score reset.", "success")
    reset_score.short_description = "Reset score of selected users"


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ("group", "is_default")
    search_fields = ("group__name",)
    list_filter = ("is_default",)
    autocomplete_fields = ("group",)


@admin.register(InGameID)
class InGameIDAdmin(ModelAdmin):
    list_display = ("user", "game", "player_id")
    search_fields = ("user__username", "game__name", "player_id")
    autocomplete_fields = ("user", "game")


@admin.register(OTP)
class OTPAdmin(ModelAdmin):
    list_display = ("user", "code", "created_at", "is_active")
    search_fields = ("user__username",)
    list_filter = ("is_active",)
    autocomplete_fields = ("user",)
