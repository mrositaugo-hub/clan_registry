import csv
from django.http import HttpResponse
from django.db import transaction
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    RegistryForm,
    LifeEventForm,
    MarriageDetailsForm,
    DivorceDetailsForm,
    MarriageDetailsFormSet,
    InitialDivorceFormSet,
    NameChangeDetailsForm,
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

    total_events = LifeEvent.objects.count()

    total_marriages = LifeEvent.objects.filter(
        event_type="MARRIAGE"
    ).count()

    total_divorces = LifeEvent.objects.filter(
        event_type="DIVORCE"
    ).count()

    total_name_changes = LifeEvent.objects.filter(
        event_type__icontains="NAME"
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
        "total_events": total_events,
        "total_marriages": total_marriages,
        "total_divorces": total_divorces,
        "total_name_changes": total_name_changes,
        "total_deaths": total_deaths,
        "family_root_counts": family_root_counts,
        "recent_members": recent_members,
        "recent_events": recent_events,
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

            with transaction.atomic():

                # --------------------------------------------
                # SAVE MEMBER
                # --------------------------------------------

                member = form.save()

                # --------------------------------------------
                # SAVE MARRIAGES
                # --------------------------------------------

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

                    if not spouse_name and not marriage_date:
                        continue

                    marriage_event = LifeEvent.objects.create(
                        member=member,
                        event_type="MARRIAGE",
                        event_date=marriage_date,
                    )

                    marriage = marriage_form.save(
                        commit=False
                    )

                    marriage.member = member
                    marriage.life_event = marriage_event

                    marriage.save()

                    saved_marriages.append(
                        marriage
                    )

                # --------------------------------------------
                # SAVE INITIAL DIVORCES
                # --------------------------------------------

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

                        divorce_event = LifeEvent.objects.create(
                            member=member,
                            event_type="DIVORCE",
                            event_date=divorce_date,
                        )

                        DivorceDetails.objects.create(
                            marriage=marriage,
                            life_event=divorce_event,
                            date_of_divorce=divorce_date,
                        )

                # --------------------------------------------
                # SUCCESS
                # --------------------------------------------

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
            messages.error(
                request,
                "Please correct the errors highlighted below."
            )

    else:

        form = RegistryForm()

        marriage_formset = MarriageDetailsFormSet(
            prefix="marriages",
        )

        divorce_formset = InitialDivorceFormSet(
            prefix="divorces",
        )

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

    export_format = request.GET.get("export", "").strip().lower()

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
            | Q(immediate_fathers_name__icontains=search_query)
            | Q(mother_name__icontains=search_query)
            | Q(family_root__icontains=search_query)
        )

    # --------------------------------------------------------
    # EXCEL / CSV EXPORT
    # --------------------------------------------------------
    if export_format in ["excel", "csv"]:
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="umuotuto_global_sheet.csv"'

        # Write UTF-8 BOM for Microsoft Excel auto-encoding
        response.write('\ufeff')

        writer = csv.writer(response)
        
        # Header Row
        writer.writerow([
            "Registry ID",
            "Surname",
            "First Name",
            "Middle Name",
            "Nickname",
            "Father's Name",
            "Mother's Name",
            "Family Root",
            "Family Name",
            "Gender",
            "Marital Status",
            "Date of Birth",
            "Phone Number",
            "Registration Date",
        ])

        for record in records:
            # Safe Date of Birth formatting
            dob = getattr(record, "date_of_birth", None)
            dob_str = dob.strftime("%Y-%m-%d") if dob and hasattr(dob, "strftime") else (str(dob) if dob else "")

            # Safe Registration Date formatting
            reg_date = getattr(record, "aut_reg_date", None)
            reg_date_str = reg_date.strftime("%Y-%m-%d %H:%M") if reg_date and hasattr(reg_date, "strftime") else (str(reg_date) if reg_date else "")

            # Safe Choice Display
            gender_str = record.get_gender_display() if hasattr(record, "get_gender_display") and getattr(record, "gender", None) else getattr(record, "gender", "")
            root_str = record.get_family_root_display() if hasattr(record, "get_family_root_display") and getattr(record, "family_root", None) else getattr(record, "family_root", "")
            marital_str = record.get_marital_status_display() if hasattr(record, "get_marital_status_display") and getattr(record, "marital_status", None) else getattr(record, "marital_status", "")

            writer.writerow([
                getattr(record, "aut_id", ""),
                getattr(record, "surname", ""),
                getattr(record, "firstname", ""),
                getattr(record, "middlename", "") or "",
                getattr(record, "nickname", "") or "",
                getattr(record, "immediate_fathers_name", "") or "",
                getattr(record, "mother_name", "") or "",
                root_str or "",
                getattr(record, "family_name", "") or "",
                gender_str or "",
                marital_str or "",
                dob_str,
                getattr(record, "phone_number", "") or "",
                reg_date_str,
            ])

        return response

    context = {
        "total_records": Registry.objects.count(),
        "records": records,
        "search_query": search_query,
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
    # Check if 'pk' is a string custom ID like 'UM_000001' or an integer ID
    if str(pk).isdigit():
        lookup = Q(pk=pk)
    else:
        lookup = Q(aut_id=pk)

    record = get_object_or_404(
        Registry.objects.prefetch_related(
            "life_events",
            "marriages",
        ),
        lookup,
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

    event_type_filter = (
        request.GET.get("type")
        or request.GET.get("event_type")
        or ""
    ).strip().upper()

    # Calculate overall stats for dashboard summary cards
    total_events = LifeEvent.objects.count()
    total_marriages = LifeEvent.objects.filter(event_type="MARRIAGE").count()
    total_divorces = LifeEvent.objects.filter(event_type="DIVORCE").count()
    total_name_changes = LifeEvent.objects.filter(event_type__icontains="NAME").count()
    total_deaths = LifeEvent.objects.filter(event_type="DEATH").count()

    events = (
        LifeEvent.objects
        .select_related("member")
        .order_by(
            "-event_date",
            "-id",
        )
    )

    if event_type_filter:
        if "NAME" in event_type_filter:
            events = events.filter(event_type__icontains="NAME")
        else:
            events = events.filter(event_type=event_type_filter)

    if query:
        events = events.filter(
            Q(member__aut_id__icontains=query)
            | Q(member__surname__icontains=query)
            | Q(member__firstname__icontains=query)
            | Q(member__middlename__icontains=query)
            | Q(event_location__icontains=query)
            | Q(event_type__icontains=query)
        )

    # --------------------------------------------------------
    # EXCEL / CSV EXPORT FOR LIFE EVENTS
    # --------------------------------------------------------
    export_format = request.GET.get("export", "").strip().lower()
    if export_format in ["excel", "csv"]:
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="umuotuto_life_events.csv"'
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow([
            "Member ID",
            "Surname",
            "First Name",
            "Middle Name",
            "Event Type",
            "Event Date",
            "Event Location",
        ])

        for event in events:
            member = event.member
            event_date_str = (
                event.event_date.strftime("%Y-%m-%d")
                if event.event_date and hasattr(event.event_date, "strftime")
                else (str(event.event_date) if event.event_date else "")
            )
            event_type_str = (
                event.get_event_type_display()
                if hasattr(event, "get_event_type_display")
                else getattr(event, "event_type", "")
            )

            writer.writerow([
                getattr(member, "aut_id", "") if member else "",
                getattr(member, "surname", "") if member else "",
                getattr(member, "firstname", "") if member else "",
                getattr(member, "middlename", "") or "" if member else "",
                event_type_str or "",
                event_date_str,
                getattr(event, "event_location", "") or "",
            ])

        return response

    context = {
        "events": events,
        "query": query,
        "event_type_filter": event_type_filter,
        "total_events": total_events,
        "total_marriages": total_marriages,
        "total_divorces": total_divorces,
        "total_name_changes": total_name_changes,
        "total_deaths": total_deaths,
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
                | Q(immediate_fathers_name__icontains=term)
                | Q(mother_name__icontains=term)
            )

    selected_member = None
    life_event_form = None
    marriage_form = None
    divorce_form = None
    name_change_form = None
    details_form = None
    selected_event_type = ""

    member_id = request.GET.get("member", "")

    event_type = (
        request.GET.get("event_type", "")
        .upper()
    )

    if member_id:
        try:
            selected_member = Registry.objects.get(
                pk=member_id
            )
        except Registry.DoesNotExist:
            selected_member = None

    if request.method == "POST":

        member_id = request.POST.get("member", "")

        selected_event_type = (
            request.POST.get("event_type", "")
            .upper()
        )

        if member_id:
            selected_member = get_object_or_404(
                Registry,
                pk=member_id,
            )

        life_event_post = request.POST.copy()

        if selected_event_type == "MARRIAGE":
            life_event_post["event_date"] = (
                request.POST.get("date_of_marriage", "")
            )

        elif selected_event_type == "DIVORCE":
            life_event_post["event_date"] = (
                request.POST.get("date_of_divorce", "")
            )

        life_event_form = LifeEventForm(
            life_event_post
        )

        if selected_member:
            life_event_form.instance.member = (
                selected_member
            )

        if selected_event_type:
            life_event_form.instance.event_type = (
                selected_event_type
            )

        if selected_event_type == "MARRIAGE":

            marriage_form = MarriageDetailsForm(
                request.POST,
                member=selected_member,
            )

            details_form = marriage_form

        elif selected_event_type == "DIVORCE":

            divorce_form = DivorceDetailsForm(
                request.POST,
                member=selected_member,
            )

            details_form = divorce_form

        elif selected_event_type == "NAME_CHANGE":

            name_change_form = NameChangeDetailsForm(
                request.POST,
                member=selected_member,
            )

            details_form = name_change_form    

        details_valid = True

        if details_form is not None:
            details_valid = details_form.is_valid()

        if (
            selected_event_type == "MARRIAGE"
            and details_valid
        ):
            life_event_form.instance.event_date = (
                marriage_form.cleaned_data.get(
                    "date_of_marriage"
                )
            )

        elif (
            selected_event_type == "DIVORCE"
            and details_valid
        ):
            life_event_form.instance.event_date = (
                divorce_form.cleaned_data.get(
                    "date_of_divorce"
                )
            )

        life_event_valid = (
            life_event_form.is_valid()
        )

        if (
            selected_member
            and life_event_valid
            and details_valid
        ):

            with transaction.atomic():

                life_event = life_event_form.save(
                    commit=False
                )

                life_event.member = selected_member
                life_event.event_type = (
                    selected_event_type
                )

                if selected_event_type == "MARRIAGE":

                    life_event.event_date = (
                        marriage_form.cleaned_data.get(
                            "date_of_marriage"
                        )
                    )

                elif selected_event_type == "DIVORCE":

                    life_event.event_date = (
                        divorce_form.cleaned_data.get(
                            "date_of_divorce"
                        )
                    )

                life_event.save()

                if selected_event_type == "MARRIAGE":

                    marriage = marriage_form.save(
                        commit=False
                    )

                    marriage.member = selected_member
                    marriage.life_event = life_event

                    marriage.save()

                elif selected_event_type == "DIVORCE":

                    divorce = divorce_form.save(
                        commit=False
                    )

                    divorce.life_event = life_event

                    divorce.save()

                elif selected_event_type == "NAME_CHANGE":

                    name_change = name_change_form.save(
                        commit=False
                    )

                    name_change.life_event = life_event

                    previous_name = (
                        name_change_form.cleaned_data.get("previous_name")
                        or name_change_form.cleaned_data.get("old_name")
                    )

                    current_name = (
                        name_change_form.cleaned_data.get("current_name")
                        or name_change_form.cleaned_data.get("new_name")
                    )

                    name_change.previous_name = previous_name
                    name_change.current_name = current_name

                    if hasattr(name_change, "old_name"):
                        name_change.old_name = previous_name

                    if hasattr(name_change, "new_name"):
                        name_change.new_name = current_name

                    name_change.save()

                    new_surname = name_change_form.cleaned_data.get("new_surname")
                    new_firstname = name_change_form.cleaned_data.get("new_firstname")
                    new_middlename = name_change_form.cleaned_data.get("new_middlename")

                    if new_surname or new_firstname:
                        if new_surname:
                            selected_member.surname = new_surname
                        if new_firstname:
                            selected_member.firstname = new_firstname
                        if new_middlename is not None:
                            selected_member.middlename = new_middlename
                        selected_member.save()

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
            messages.error(
                request,
                "Please correct the errors highlighted below."
            )

    else:

        life_event_form = LifeEventForm()

        if selected_member:

            marriage_form = MarriageDetailsForm(
                member=selected_member,
            )

            divorce_form = DivorceDetailsForm(
                member=selected_member,
            )

            name_change_form = NameChangeDetailsForm(
                 member=selected_member,
            )

        if event_type == "MARRIAGE":

            selected_event_type = "MARRIAGE"
            details_form = marriage_form

        elif event_type == "DIVORCE":

            selected_event_type = "DIVORCE"
            details_form = divorce_form

        elif event_type == "NAME_CHANGE":

            selected_event_type = "NAME_CHANGE"
            details_form = name_change_form

    context = {
        "members": members,
        "selected_member": selected_member,
        "selected_event_type": selected_event_type,
        "life_event_form": life_event_form,
        "details_form": details_form,
        "marriage_form": marriage_form,
        "divorce_form": divorce_form,
        "name_change_form": name_change_form,
        "query": search_query,
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

    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
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

            if is_ajax:
                chips = [
                    "How many female members are registered?",
                    "How many married members are registered?",
                    "Who is the oldest living member?",
                    "Umunangwu lineage",
                    "How many marriage records are there?",
                ]
                return JsonResponse(
                    {
                        "success": True,
                        "answer": answer,
                        "results": result_cards,
                        "chips": chips,
                    }
                )

        elif is_ajax:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Please enter a valid question.",
                }
            )

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
# MEMBER SUMMARY API (FOR HISTORIAN CHAT QUICK VIEW)
# ============================================================

def member_summary(request, pk):
    member = get_object_or_404(Registry, pk=pk)

    gender = (
        member.get_gender_display()
        if hasattr(member, "get_gender_display")
        else getattr(member, "gender", "N/A")
    )

    marital_status = (
        member.get_marital_status_display()
        if hasattr(member, "get_marital_status_display")
        else getattr(member, "marital_status", "N/A")
    )

    name_components = [
        getattr(member, "surname", ""),
        getattr(member, "firstname", ""),
        getattr(member, "middlename", ""),
    ]
    full_name = " ".join([n for n in name_components if n]).strip()

    lineage = (
        getattr(member, "family_root", "")
        or getattr(member, "family_name", "")
        or "N/A"
    )

    data = {
        "id": member.pk,
        "aut_id": getattr(member, "aut_id", ""),
        "name": full_name or "N/A",
        "gender": gender or "N/A",
        "lineage": lineage,
        "marital_status": marital_status or "N/A",
        "father_name": getattr(member, "immediate_fathers_name", "") or "N/A",
    }

    return JsonResponse(data)


# ============================================================
# ANCESTRY MAP
# ============================================================

def ancestry_map(request):
    members = (
        Registry.objects
        .all()
        .order_by(
            "family_root",
            "family_name",
            "surname",
            "firstname",
            "middlename",
        )
    )

    family_roots = []

    for root_code, root_name in Registry.ROOT_FAMILY_CHOICES:

        root_members = (
            Registry.objects
            .filter(
                family_root=root_code
            )
            .order_by(
                "family_name",
                "surname",
                "firstname",
                "middlename",
            )
        )

        families = {}

        for member in root_members:

            family_name = (
                member.family_name.strip()
                if member.family_name
                else "Unspecified Family"
            )

            if family_name not in families:
                families[family_name] = []

            families[family_name].append(member)

        family_roots.append(
            {
                "code": root_code,
                "name": root_name,
                "families": families,
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