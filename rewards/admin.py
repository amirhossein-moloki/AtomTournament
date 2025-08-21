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
from .models import Prize, Spin, Wheel


# --- Resources for django-import-export ---

class WheelResource(resources.ModelResource):
    class Meta:
        model = Wheel

class PrizeResource(resources.ModelResource):
    class Meta:
        model = Prize

class SpinResource(resources.ModelResource):
    class Meta:
        model = Spin


# --- Inlines (Upgraded) ---

class PrizeInline(TabularInline):
    model = Prize
    extra = 1
    classes = ["collapse"]


# --- ModelAdmins (Upgraded) ---

@admin.register(Wheel)
class WheelAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = WheelResource
    list_display = ("name", "required_rank")
    search_fields = ("name",)
    autocomplete_fields = ("required_rank",)
    inlines = [PrizeInline]
    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }


@admin.register(Prize)
class PrizeAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = PrizeResource
    list_display = ("name", "wheel", "chance")
    search_fields = ("name",)
    autocomplete_fields = ("wheel",)
    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }


@admin.register(Spin)
class SpinAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = SpinResource
    list_display = ("user", "wheel", "prize", "timestamp")
    search_fields = ("user__username", "wheel__name", "prize__name")
    autocomplete_fields = ("user", "wheel", "prize")
    readonly_fields = ("user", "wheel", "prize", "timestamp")
    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }
