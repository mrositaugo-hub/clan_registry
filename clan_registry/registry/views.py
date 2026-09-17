from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    RegistryForm,
    LifeEventForm,
    MarriageDetailsForm,
    DivorceDetailsForm,
)
from .models import (
    Registry,
    LifeEvent,
    MarriageDetails,
    DivorceDetails,
)
from .historian import (
    process_historian_question,
    clear_historian_context,
)


# ============================================================
# DASHBOARD
# ============================================================

def dashboard(request):
    total_members = Registry.objects.count()

    male_members = Registry.objects.filter(
        gender="MALE"
    ).count()

    female_members = Registry.objects.filter(
        gender="FEMALE"
    ).count()

    married_members = Registry.objects.filter(
        marital_status="MARRIED"
    ).count()

    single_members = Registry.objects.filter(
        marital_status="SINGLE"
    ).count()

    divorced_members = Registry.objects.filter(
        marital_status="DIVORCED"
    ).count()

    total_life_events = LifeEvent.objects.count()

    recent_members = Registry.objects.all()[:5]

    recent_life_events = (
        LifeEvent.objects
        .select_related("member")
        .order_by("-event_date")[:5]
    )

    context = {
        "total_members": total_members,
        "male_members": male_members,
        "female_members": female_members,
        "married_members": married_members,
        "single_members": single_members,
        "divorced_members": divorced_members,
        "total_life_events": total_life_events,
        "recent_members": recent_members,
        "recent_life_events": recent_life_events,
    }

    return render(
        request,
        "registry/dashboard.html",
        context,
    )


# ============================================================
# NEW REGISTRY
# ============================================================

def new_registry(request):
    if request.method == "POST":
        form = RegistryForm(request.POST)

        if form.is_valid():
            member = form.save()

            messages.success(
                request,
                (
                    f"Registry record for "
                    f"{member.surname} {member.firstname} "
                    f"saved successfully as {member.aut_id}."
                ),
            )

            return redirect(
                "view_registry",
                pk=member.pk,
            )

    else:
        form = RegistryForm()

    return render(
        request,
        "registry/new_registry.html",
        {
            "form": form,
        },
    )


# ============================================================
# GLOBAL SHEET
# ============================================================

def global_sheet(request):
    query = request.GET.get(
        "q",
        "",
    ).strip()

    members = Registry.objects.all()

    if query:
        members = members.filter(
            Q(aut_id__icontains=query)
            | Q(surname__icontains=query)
            | Q(firstname__icontains=query)
            | Q(middlename__icontains=query)
            | Q(nickname__icontains=query)
            | Q(family_name__icontains=query)
            | Q(family_lineage__icontains=query)
            | Q(immediate_fathers_name__icontains=query)
            | Q(mother_name__icontains=query)
        )

    context = {
        "members": members,
        "query": query,
    }

    return render(
        request,
        "registry/global_sheet.html",
        context,
    )


# ============================================================
# VIEW REGISTRY
# ============================================================

def view_registry(request, pk):
    member = get_object_or_404(
        Registry,
        pk=pk,
    )

    life_events = (
        LifeEvent.objects
        .filter(member=member)
        .order_by("-event_date")
    )

    context = {
        "member": member,
        "life_events": life_events,
    }

    return render(
        request,
        "registry/view_registry.html",
        context,
    )


# ============================================================
# LIFE EVENTS
# ============================================================

def life_events(request):
    query = request.GET.get(
        "q",
        "",
    ).strip()

    events = (
        LifeEvent.objects
        .select_related("member")
        .order_by("-event_date")
    )

    if query:
        events = events.filter(
            Q(member__aut_id__icontains=query)
            | Q(member__surname__icontains=query)
            | Q(member__firstname__icontains=query)
            | Q(member__middlename__icontains=query)
            | Q(event_location__icontains=query)
        )

    context = {
        "events": events,
        "query": query,
    }

    return render(
        request,
        "registry/life_events.html",
        context,
    )


# ============================================================
# NEW LIFE EVENT
# ============================================================

def new_life_event(request):
    members = Registry.objects.all().order_by(
        "surname",
        "firstname",
        "middlename",
    )

    selected_member = None
    details_form = None
    selected_event_type = ""

    member_id = request.GET.get(
        "member",
        "",
    )

    event_type = request.GET.get(
        "event_type",
        "",
    ).upper()

    if member_id:
        try:
            selected_member = Registry.objects.get(
                pk=member_id
            )
        except Registry.DoesNotExist:
            selected_member = None

    if request.method == "POST":
        member_id = request.POST.get(
            "member",
            ""
        )

        selected_event_type = request.POST.get(
            "event_type",
            ""
        ).upper()

        if member_id:
            selected_member = get_object_or_404(
                Registry,
                pk=member_id,
            )

        life_event_form = LifeEventForm(
            request.POST
        )

        if selected_event_type == "MARRIAGE":
            details_form = MarriageDetailsForm(
                request.POST
            )

        elif selected_event_type == "DIVORCE":
            details_form = DivorceDetailsForm(
                request.POST
            )

        else:
            details_form = None

        life_event_valid = life_event_form.is_valid()

        details_valid = True

        if details_form is not None:
            details_valid = details_form.is_valid()

        if (
            selected_member
            and life_event_valid
            and details_valid
        ):
            life_event = life_event_form.save(
                commit=False
            )

            life_event.member = selected_member
            life_event.event_type = selected_event_type

            life_event.save()

            if selected_event_type == "MARRIAGE":
                details = details_form.save(
                    commit=False
                )

                details.life_event = life_event
                details.save()

            elif selected_event_type == "DIVORCE":
                details = details_form.save(
                    commit=False
                )

                details.life_event = life_event
                details.save()

            messages.success(
                request,
                (
                    f"{life_event.get_event_type_display()} "
                    f"recorded successfully for "
                    f"{selected_member.surname} "
                    f"{selected_member.firstname}."
                ),
            )

            return redirect(
                "view_life_event",
                pk=life_event.pk,
            )

    else:
        life_event_form = LifeEventForm()

        if event_type == "MARRIAGE":
            selected_event_type = "MARRIAGE"

            details_form = MarriageDetailsForm()

        elif event_type == "DIVORCE":
            selected_event_type = "DIVORCE"

            details_form = DivorceDetailsForm()

    context = {
        "members": members,
        "selected_member": selected_member,
        "selected_event_type": selected_event_type,
        "life_event_form": life_event_form,
        "details_form": details_form,
    }

    return render(
        request,
        "registry/new_life_event.html",
        context,
    )


# ============================================================
# VIEW LIFE EVENT
# ============================================================

def view_life_event(request, pk):
    event = get_object_or_404(
        LifeEvent.objects.select_related("member"),
        pk=pk,
    )

    marriage_details = None
    divorce_details = None

    if event.event_type == "MARRIAGE":
        marriage_details = getattr(
            event,
            "marriage_details",
            None,
        )

    elif event.event_type == "DIVORCE":
        divorce_details = getattr(
            event,
            "divorce_details",
            None,
        )

    context = {
        "event": event,
        "marriage_details": marriage_details,
        "divorce_details": divorce_details,
    }

    return render(
        request,
        "registry/view_life_event.html",
        context,
    )


# ============================================================
# HISTORIAN CHAT
# ============================================================

def historian_chat(request):
    if request.GET.get("clear") == "1":
        request.session["historian_chat_history"] = []

        clear_historian_context(
            request
        )

        return redirect(
            "historian_chat"
        )

    history = request.session.get(
        "historian_chat_history",
        [],
    )

    if request.method == "POST":
        question = request.POST.get(
            "question",
            "",
        ).strip()

        if question:
            answer, result_members = (
                process_historian_question(
                    request,
                    question,
                )
            )

            result_cards = [
                {
                    "id": member.id,
                    "aut_id": member.aut_id,
                    "name": (
                        f"{member.surname} "
                        f"{member.firstname}"
                    ).strip(),
                }
                for member in result_members
            ]

            history.append(
                {
                    "question": question,
                    "answer": answer,
                    "results": result_cards,
                }
            )

            # Keep the conversation manageable.
            # The active member itself is stored separately
            # in the Django session.
            request.session[
                "historian_chat_history"
            ] = history[-50:]

    return render(
        request,
        "registry/historian_chat.html",
        {
            "history": request.session.get(
                "historian_chat_history",
                [],
            )
        },
    )
    # ============================================================
# ANCESTRY MAP
# ============================================================

def ancestry_map(request):
    family_roots = []

    for root_code, root_name in Registry.ROOT_FAMILY_CHOICES:
        root_members = (
            Registry.objects
            .filter(family_root=root_code)
            .order_by(
                "family_lineage",
                "family_name",
                "surname",
                "firstname",
                "middlename",
            )
        )

        lineages = {}

        for member in root_members:
            lineage = (
                member.family_lineage.strip()
                if member.family_lineage
                else "Unspecified Lineage"
            )

            family_name = (
                member.family_name.strip()
                if member.family_name
                else "Unspecified Family"
            )

            if lineage not in lineages:
                lineages[lineage] = {}

            if family_name not in lineages[lineage]:
                lineages[lineage][family_name] = []

            lineages[lineage][family_name].append(member)

        family_roots.append(
            {
                "code": root_code,
                "name": root_name,
                "lineages": lineages,
                "member_count": root_members.count(),
            }
        )

    context = {
        "foundation_name": "UMUOTUTO",
        "family_roots": family_roots,
    }

    return render(
        request,
        "registry/ancestry_map.html",
        context,
    )
    # ============================================================
# ANCESTRY MAP
# ============================================================

def ancestry_map(request):
    family_roots = []

    for root_code, root_name in Registry.ROOT_FAMILY_CHOICES:
        root_members = (
            Registry.objects
            .filter(family_root=root_code)
            .order_by(
                "family_lineage",
                "family_name",
                "surname",
                "firstname",
                "middlename",
            )
        )

        lineages = {}

        for member in root_members:
            lineage = (
                member.family_lineage.strip()
                if member.family_lineage
                else "Unspecified Lineage"
            )

            family_name = (
                member.family_name.strip()
                if member.family_name
                else "Unspecified Family"
            )

            if lineage not in lineages:
                lineages[lineage] = {}

            if family_name not in lineages[lineage]:
                lineages[lineage][family_name] = []

            lineages[lineage][family_name].append(member)

        family_roots.append(
            {
                "code": root_code,
                "name": root_name,
                "lineages": lineages,
                "member_count": root_members.count(),
            }
        )

    context = {
        "foundation_name": "UMUOTUTO",
        "family_roots": family_roots,
    }

    return render(
        request,
        "registry/ancestry_map.html",
        context,
    )