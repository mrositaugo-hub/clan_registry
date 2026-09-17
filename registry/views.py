from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    RegistryForm,
    LifeEventForm,
    MarriageDetailsForm,
    DivorceDetailsForm,
    MarriageDetailsFormSet,
    InitialDivorceFormSet,
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
    total_events = total_life_events

    total_marriages = LifeEvent.objects.filter(
        event_type="MARRIAGE"
    ).count()

    total_divorces = LifeEvent.objects.filter(
        event_type="DIVORCE"
    ).count()

    total_deaths = LifeEvent.objects.filter(
        event_type="DEATH"
    ).count()

    family_root_choices = getattr(
        Registry,
        "ROOT_FAMILY_CHOICES",
        []
    )

    family_root_counts = [
        {
            "label": root_name,
            "count": Registry.objects.filter(
                family_root=root_code
            ).count(),
        }
        for root_code, root_name in family_root_choices
    ]

    recent_members = (
        Registry.objects
        .all()
        .order_by("-aut_reg_date", "-id")[:5]
    )

    recent_events = (
        LifeEvent.objects
        .select_related("member")
        .order_by("-event_date", "-id")[:5]
    )

    context = {
        "total_members": total_members,
        "male_members": male_members,
        "female_members": female_members,
        "married_members": married_members,
        "single_members": single_members,
        "divorced_members": divorced_members,
        "total_life_events": total_life_events,
        "total_events": total_events,
        "total_marriages": total_marriages,
        "total_divorces": total_divorces,
        "total_deaths": total_deaths,
        "family_root_counts": family_root_counts,
        "recent_members": recent_members,
        "recent_events": recent_events,
        "recent_life_events": recent_events,
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

        # ----------------------------------------------------
        # MAIN REGISTRY FORM
        # ----------------------------------------------------

        form = RegistryForm(
            request.POST
        )

        # ----------------------------------------------------
        # MARRIAGE FORMSET
        # ----------------------------------------------------

        marriage_formset = MarriageDetailsFormSet(
            request.POST,
            prefix="marriages",
        )

        # ----------------------------------------------------
        # DIVORCE FORMSET
        # ----------------------------------------------------

        divorce_formset = InitialDivorceFormSet(
            request.POST,
            prefix="divorces",
        )

        # ----------------------------------------------------
        # VALIDATE MAIN FORM
        # ----------------------------------------------------

        form_valid = form.is_valid()

        # ----------------------------------------------------
        # VALIDATE MARRIAGE FORMSET
        # ----------------------------------------------------

        marriage_valid = marriage_formset.is_valid()

        # ----------------------------------------------------
        # DIVORCE FORMSET
        #
        # Divorce is only relevant when the member is
        # registered as DIVORCED.
        # ----------------------------------------------------

        marital_status = (
            form.cleaned_data.get("marital_status")
            if form_valid
            else request.POST.get(
                "marital_status",
                "",
            )
        )

        if marital_status == "DIVORCED":

            divorce_valid = divorce_formset.is_valid()

        else:

            divorce_valid = True

        # ----------------------------------------------------
        # SAVE EVERYTHING
        # ----------------------------------------------------

        if (
            form_valid
            and marriage_valid
            and divorce_valid
        ):

            # ------------------------------------------------
            # SAVE MEMBER
            # ------------------------------------------------

            member = form.save()

            # ------------------------------------------------
            # SAVE MARRIAGES
            # ------------------------------------------------

            saved_marriages = []

            for marriage_form in marriage_formset:

                if not marriage_form.cleaned_data:
                    continue

                if marriage_form.cleaned_data.get(
                    "DELETE"
                ):
                    continue

                spouse_name = (
                    marriage_form.cleaned_data.get(
                        "spouse_full_name"
                    )
                    or ""
                ).strip()

                marriage_date = (
                    marriage_form.cleaned_data.get(
                        "date_of_marriage"
                    )
                )

                # --------------------------------------------
                # Ignore completely empty form
                # --------------------------------------------

                if not spouse_name and not marriage_date:
                    continue

                # --------------------------------------------
                # CREATE MARRIAGE LIFE EVENT
                # --------------------------------------------

                marriage_event = LifeEvent.objects.create(
                    member=member,
                    event_type="MARRIAGE",
                    event_date=marriage_date,
                )

                # --------------------------------------------
                # CREATE MARRIAGE DETAILS
                # --------------------------------------------

                marriage = marriage_form.save(
                    commit=False
                )

                marriage.member = member
                marriage.life_event = marriage_event

                marriage.save()

                saved_marriages.append(
                    marriage
                )

            # ------------------------------------------------
            # SAVE INITIAL DIVORCES
            # ------------------------------------------------

            if marital_status == "DIVORCED":

                for divorce_form in divorce_formset:

                    if not divorce_form.cleaned_data:
                        continue

                    marriage_index = (
                        divorce_form.cleaned_data.get(
                            "marriage_index"
                        )
                    )

                    divorce_date = (
                        divorce_form.cleaned_data.get(
                            "date_of_divorce"
                        )
                    )

                    if (
                        marriage_index is None
                        or not divorce_date
                    ):
                        continue

                    # ----------------------------------------
                    # Make sure the supplied marriage index
                    # points to an actual saved marriage.
                    # ----------------------------------------

                    if (
                        marriage_index < 0
                        or marriage_index >= len(
                            saved_marriages
                        )
                    ):
                        continue

                    marriage = saved_marriages[
                        marriage_index
                    ]

                    # ----------------------------------------
                    # CREATE DIVORCE LIFE EVENT
                    # ----------------------------------------

                    divorce_event = LifeEvent.objects.create(
                        member=member,
                        event_type="DIVORCE",
                        event_date=divorce_date,
                    )

                    # ----------------------------------------
                    # CREATE DIVORCE DETAILS
                    # ----------------------------------------

                    DivorceDetails.objects.create(
                        marriage=marriage,
                        life_event=divorce_event,
                        date_of_divorce=divorce_date,
                    )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            messages.success(
                request,
                (
                    f"Registry record for "
                    f"{member.surname} "
                    f"{member.firstname} "
                    f"saved successfully as "
                    f"{member.aut_id}."
                ),
            )

            return redirect(
                "view_registry",
                pk=member.pk,
            )

    else:

        # ----------------------------------------------------
        # INITIAL PAGE LOAD
        # ----------------------------------------------------

        form = RegistryForm()

        marriage_formset = MarriageDetailsFormSet(
            prefix="marriages",
        )

        divorce_formset = InitialDivorceFormSet(
            prefix="divorces",
        )

    # --------------------------------------------------------
    # PAGE CONTEXT
    # --------------------------------------------------------

    context = {
        "form": form,
        "marriage_formset": marriage_formset,
        "divorce_formset": divorce_formset,
    }

    return render(
        request,
        "registry/new_registry.html",
        context,
    )


# ============================================================
# GLOBAL SHEET
# ============================================================

def global_sheet(request):
    search_query = (
        request.GET.get("q")
        or request.GET.get("search")
        or ""
    ).strip()

    records = (
        Registry.objects
        .all()
        .order_by(
            "-aut_reg_date",
            "-id",
        )
    )

    if search_query:
        records = records.filter(
            Q(aut_id__icontains=search_query)
            | Q(surname__icontains=search_query)
            | Q(firstname__icontains=search_query)
            | Q(middlename__icontains=search_query)
            | Q(nickname__icontains=search_query)
            | Q(family_name__icontains=search_query)
            | Q(family_lineage__icontains=search_query)
            | Q(immediate_fathers_name__icontains=search_query)
            | Q(mother_name__icontains=search_query)
            | Q(family_root__icontains=search_query)
        )

    context = {
        "total_records": Registry.objects.count(),
        "records": records,
        "members": records,
        "search_query": search_query,
        "query": search_query,
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
    record = get_object_or_404(
        Registry.objects.prefetch_related(
            "life_events",
            "marriages",
        ),
        pk=pk,
    )

    marriages = record.marriages.all().order_by(
        "date_of_marriage",
        "id",
    )

    context = {
        "record": record,
        "marriages": marriages,
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
    query = (
        request.GET.get("q")
        or request.GET.get("search")
        or ""
    ).strip()

    events = (
        LifeEvent.objects
        .select_related("member")
        .order_by(
            "-event_date",
            "-id",
        )
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
        "search_query": query,
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
    search_query = (
        request.GET.get("q")
        or request.GET.get("search")
        or ""
    ).strip()

    members = (
        Registry.objects
        .all()
        .order_by(
            "surname",
            "firstname",
            "middlename",
        )
    )

    # --------------------------------------------------------
    # SEARCH MEMBERS
    # --------------------------------------------------------

    if search_query:
        search_terms = search_query.split()

        for term in search_terms:
            members = members.filter(
                Q(aut_id__icontains=term)
                | Q(surname__icontains=term)
                | Q(firstname__icontains=term)
                | Q(middlename__icontains=term)
                | Q(nickname__icontains=term)
                | Q(family_name__icontains=term)
                | Q(family_lineage__icontains=term)
                | Q(immediate_fathers_name__icontains=term)
                | Q(mother_name__icontains=term)
            )

    selected_member = None
    details_form = None
    selected_event_type = ""

    # --------------------------------------------------------
    # GET PARAMETERS
    # --------------------------------------------------------

    member_id = request.GET.get(
        "member",
        "",
    )

    event_type = (
        request.GET.get(
            "event_type",
            "",
        )
        .upper()
    )

    if member_id:
        try:
            selected_member = Registry.objects.get(
                pk=member_id
            )
        except Registry.DoesNotExist:
            selected_member = None

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        member_id = request.POST.get(
            "member",
            "",
        )

        selected_event_type = (
            request.POST.get(
                "event_type",
                "",
            )
            .upper()
        )

        # ----------------------------------------------------
        # Get selected registry member
        # ----------------------------------------------------

        if member_id:
            selected_member = get_object_or_404(
                Registry,
                pk=member_id,
            )

        # ----------------------------------------------------
        # Main LifeEvent form
        # ----------------------------------------------------

        life_event_form = LifeEventForm(
            request.POST
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Attach required model values BEFORE validation.
        # ----------------------------------------------------

        if selected_member:
            life_event_form.instance.member = selected_member

        if selected_event_type:
            life_event_form.instance.event_type = (
                selected_event_type
            )

        # ----------------------------------------------------
        # Event-specific forms
        # ----------------------------------------------------

        if selected_event_type == "MARRIAGE":

            details_form = MarriageDetailsForm(
                request.POST,
                member=selected_member,
            )

        elif selected_event_type == "DIVORCE":

            details_form = DivorceDetailsForm(
                request.POST,
                member=selected_member,
            )

        else:
            details_form = None

        # ----------------------------------------------------
        # Validate forms
        # ----------------------------------------------------

        life_event_valid = life_event_form.is_valid()

        details_valid = True

        if details_form is not None:
            details_valid = details_form.is_valid()

        # ----------------------------------------------------
        # Save everything only when valid
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # Marriage date becomes official event date
            # ------------------------------------------------

            if selected_event_type == "MARRIAGE":

                marriage_date = (
                    details_form.cleaned_data.get(
                        "date_of_marriage"
                    )
                )

                if marriage_date:
                    life_event.event_date = (
                        marriage_date
                    )

            # ------------------------------------------------
            # Divorce date becomes official event date
            # ------------------------------------------------

            elif selected_event_type == "DIVORCE":

                divorce_date = (
                    details_form.cleaned_data.get(
                        "date_of_divorce"
                    )
                )

                if divorce_date:
                    life_event.event_date = (
                        divorce_date
                    )

            # ------------------------------------------------
            # Save main life event
            # ------------------------------------------------

            life_event.save()

            # ------------------------------------------------
            # Save marriage details
            # ------------------------------------------------

            if selected_event_type == "MARRIAGE":

                details = details_form.save(
                    commit=False
                )

                details.member = selected_member
                details.life_event = life_event

                details.save()

            # ------------------------------------------------
            # Save divorce details
            # ------------------------------------------------

            elif selected_event_type == "DIVORCE":

                details = details_form.save(
                    commit=False
                )

                details.life_event = life_event

                details.save()

            # ------------------------------------------------
            # Success message
            # ------------------------------------------------

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

    # ========================================================
    # GET
    # ========================================================

    else:

        life_event_form = LifeEventForm()

        if event_type == "MARRIAGE":

            selected_event_type = "MARRIAGE"

            details_form = MarriageDetailsForm(
                member=selected_member,
            )

        elif event_type == "DIVORCE":

            selected_event_type = "DIVORCE"

            details_form = DivorceDetailsForm(
                member=selected_member,
            )

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {
        "members": members,
        "selected_member": selected_member,
        "selected_event_type": selected_event_type,
        "life_event_form": life_event_form,
        "details_form": details_form,
        "query": search_query,
        "search_query": search_query,
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
    life_event = get_object_or_404(
        LifeEvent.objects.select_related("member"),
        pk=pk,
    )

    member = life_event.member

    context = {
        "life_event": life_event,
        "member": member,
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

        request.session[
            "historian_chat_history"
        ] = []

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

    members = (
        Registry.objects
        .all()
        .order_by(
            "family_root",
            "family_lineage",
            "family_name",
            "surname",
            "firstname",
            "middlename",
        )
    )

    family_roots = []

    for root_code, root_name in (
        Registry.ROOT_FAMILY_CHOICES
    ):

        root_members = (
            Registry.objects
            .filter(
                family_root=root_code
            )
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

            lineages[lineage][family_name].append(
                member
            )

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
        "members": members,
        "family_roots": family_roots,
    }

    return render(
        request,
        "registry/ancestry_map.html",
        context,
    )