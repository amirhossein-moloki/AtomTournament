from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, InGameID, Team, TeamMembership, TeamInvitation, OTP

class InGameIDInline(admin.TabularInline):
    model = InGameID
    extra = 1

class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    readonly_fields = ('user', 'team', 'date_joined')

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('phone_number', 'profile_picture', 'score', 'rank')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('phone_number', 'profile_picture', 'score', 'rank')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'score', 'rank')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'rank')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
    inlines = [InGameIDInline, TeamMembershipInline]

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('group', 'description', 'is_default')
    list_filter = ('is_default',)
    search_fields = ('group__name', 'description')

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'captain')
    search_fields = ('name', 'captain__username')
    inlines = [TeamMembershipInline]

@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'team', 'status', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('from_user__username', 'to_user__username', 'team__name')

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'code', 'created_at')

# TeamMembership is managed through inlines, but it's good to register it too.
@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'date_joined')
    search_fields = ('user__username', 'team__name')
    readonly_fields = ('user', 'team', 'date_joined')

# InGameID is managed through inlines, but it's good to register it too.
@admin.register(InGameID)
class InGameIDAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'player_id')
    search_fields = ('user__username', 'game__name', 'player_id')
