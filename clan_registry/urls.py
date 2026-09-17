from django.contrib import admin
from django.urls import path

from registry.views import (
    dashboard,
    new_registry,
    global_sheet,
    view_registry,
    life_events,
    new_life_event,
    view_life_event,
    historian_chat,
    ancestry_map,
)


urlpatterns = [

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "",
        dashboard,
        name="dashboard"
    ),

    path(
        "new-registry/",
        new_registry,
        name="new_registry"
    ),

    path(
        "global-sheet/",
        global_sheet,
        name="global_sheet"
    ),

    path(
        "registry/<int:pk>/",
        view_registry,
        name="view_registry"
    ),

    path(
        "life-events/",
        life_events,
        name="life_events"
    ),

    path(
        "life-events/new/",
        new_life_event,
        name="new_life_event"
    ),

    path(
        "life-events/<int:pk>/",
        view_life_event,
        name="view_life_event"
    ),

    path(
        "historian-chat/",
        historian_chat,
        name="historian_chat"
    ),

    path(
        "ancestry-map/",
        ancestry_map,
        name="ancestry_map"
    ),

]