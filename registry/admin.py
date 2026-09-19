from django.contrib import admin
from .models import (
    Registry,
    LifeEvent,
    MarriageDetails,
    DivorceDetails,
)


# ============================================================
# REGISTRY ADMIN
# ============================================================

@admin.register(Registry)
class RegistryAdmin(admin.ModelAdmin):
    list_display = (
        "aut_id",
        "surname",
        "firstname",
        "family_root",
        "gender",
        "marital_status",
        "phone_number",
    )
    list_filter = (
        "family_root",
        "gender",
        "marital_status",
    )
    search_fields = (
        "aut_id",
        "surname",
        "firstname",
        "family_name",
        "family_root",
        "phone_number",
    )
    readonly_fields = (
        "aut_id",
        "aut_reg_date",
    )


# ============================================================
# LIFE EVENT ADMIN
# ============================================================

@admin.register(LifeEvent)
class LifeEventAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "event_type",
        "event_date",
        "event_location",
    )
    list_filter = (
        "event_type",
        "event_date",
    )
    search_fields = (
        "member__surname",
        "member__firstname",
        "member__aut_id",
        "event_location",
    )


# ============================================================
# MARRIAGE DETAILS ADMIN
# ============================================================

@admin.register(MarriageDetails)
class MarriageDetailsAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "spouse_full_name",
        "date_of_marriage",
    )
    search_fields = (
        "member__surname",
        "member__firstname",
        "spouse_full_name",
    )


# ============================================================
# DIVORCE DETAILS ADMIN
# ============================================================

@admin.register(DivorceDetails)
class DivorceDetailsAdmin(admin.ModelAdmin):
    list_display = (
        "marriage",
        "date_of_divorce",
    )
    search_fields = (
        "marriage__member__surname",
        "marriage__member__firstname",
        "marriage__spouse_full_name",
    )