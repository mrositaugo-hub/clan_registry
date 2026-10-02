import re
from datetime import date
from django.db import models
from django.db.models import Q
from .models import Registry, LifeEvent, MarriageDetails, DivorceDetails

# Common English stop words and conversational fillers
STOP_WORDS = {
    "who", "is", "are", "was", "were", "be", "been", "being",
    "he", "she", "it", "they", "them", "his", "her", "him", "hers",
    "i", "me", "my", "myself", "we", "our", "you", "your",
    "mean", "what", "where", "which", "when", "how", "why",
    "about", "tell", "show", "find", "search", "lookup", "for",
    "the", "a", "an", "do", "does", "did", "know",
    "can", "could", "would", "should", "please", "there", "here",
    "give", "list", "get", "info", "information", "record", "records",
    "many", "much", "total", "count", "number", "exist", "exists",
    "have", "has", "had", "of", "in", "on", "at", "to", "from", "with",
    "lineage", "family", "kindred", "umunna", "clan", "root", "branch"
}


def clear_historian_context(request):
    """Clears cached session context for the historian."""
    if "historian_last_member_ids" in request.session:
        del request.session["historian_last_member_ids"]
    if "historian_last_topic" in request.session:
        del request.session["historian_last_topic"]
    request.session.modified = True


def _get_registry_text_fields():
    """Dynamically finds all text field names on Registry."""
    text_fields = []
    for field in Registry._meta.get_fields():
        if hasattr(field, 'get_internal_type'):
            try:
                internal_type = field.get_internal_type()
                if internal_type in ['CharField', 'TextField', 'SlugField', 'EmailField']:
                    text_fields.append(field.name)
            except Exception:
                pass
    return text_fields


def _generate_spelling_variants(term):
    """
    Generates common orthographic and Igbo dialect/spelling variants 
    (e.g., 'umunagwu' <-> 'umunangwu', double consonants, nasalized consonants).
    """
    variants = {term.lower()}

    # Handle ngw <-> gw interchangeability
    if "ngw" in term.lower():
        variants.add(term.lower().replace("ngw", "gw"))
    elif "gw" in term.lower():
        variants.add(term.lower().replace("gw", "ngw"))

    # Handle nna <-> na interchangeability
    if "nna" in term.lower():
        variants.add(term.lower().replace("nna", "na"))
    elif "na" in term.lower():
        variants.add(term.lower().replace("na", "nna"))

    return list(variants)


def _get_dob_field_name():
    """Dynamically detects the date of birth field on Registry."""
    text_fields = [f.name for f in Registry._meta.get_fields() if hasattr(f, 'name')]
    for field_name in ["date_of_birth", "dob", "birth_date", "date_birth", "birthday"]:
        if field_name in text_fields:
            return field_name
    return None


def _calculate_age(dob):
    """Calculates age in years given a date object."""
    if not dob or not isinstance(dob, date):
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _has_word(text, keywords):
    """Checks if any keyword exists as a full word within text."""
    pattern = r'\b(' + '|'.join([re.escape(k) for k in keywords]) + r')\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _extract_search_keywords(query_text):
    """Strips conversational prefixes, punctuation, and stop words."""
    text = query_text.lower().strip()

    phrases_to_remove = [
        r'\bi mean\b', r'\bwho is\b', r'\bwho are\b', r'\btell me about\b',
        r'\bsearch for\b', r'\blookup\b', r'\bfind\b', r'\bshow me\b',
        r'\bdo you know\b', r'\bwhat about\b', r'\bcan you tell me\b',
        r'\bis there a\b', r'\bis there any\b', r'\bplease\b',
        r'\bhow many\b', r'\bhow much\b'
    ]
    for phrase in phrases_to_remove:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)

    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = text.split()
    keywords = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

    if not keywords:
        keywords = [t for t in text.split() if len(t) > 1]

    return keywords


def _get_member_children(member):
    """Dynamically locates children for a given member across common schema relationships."""
    children_q = Q()

    if hasattr(Registry, "father"):
        children_q |= Q(father=member)
    if hasattr(Registry, "father_id"):
        children_q |= Q(father_id=member.id)
    if hasattr(Registry, "mother"):
        children_q |= Q(mother=member)
    if hasattr(Registry, "mother_id"):
        children_q |= Q(mother_id=member.id)
    if hasattr(Registry, "parent"):
        children_q |= Q(parent=member)
    if hasattr(Registry, "parent_id"):
        children_q |= Q(parent_id=member.id)

    if hasattr(Registry, "immediate_fathers_name") and getattr(member, "firstname", None):
        children_q |= Q(
            immediate_fathers_name__icontains=member.firstname,
            surname__icontains=member.surname,
        )

    if children_q:
        return Registry.objects.filter(children_q)
    return Registry.objects.none()


def _get_member_life_events_summary(member):
    """Formats a clean summary of all life event updates associated with a member."""
    events = LifeEvent.objects.filter(member=member).order_by("event_date", "id")
    if not events.exists():
        return ""

    summary_lines = []
    for ev in events:
        ev_type = ev.get_event_type_display() if hasattr(ev, "get_event_type_display") else ev.event_type
        date_str = ev.event_date.strftime("%B %d, %Y") if ev.event_date else "Date not specified"

        details_str = ""

        if str(ev.event_type).upper() in ["NAME_CHANGE", "NAME CHANGE"]:
            details = (
                getattr(ev, "name_change_details", None)
                or getattr(ev, "namechangedetails", None)
                or getattr(ev, "name_change", None)
            )
            prev = getattr(details, "previous_name", None) or getattr(details, "old_name", None) or getattr(ev, "previous_name", None) or getattr(ev, "old_name", None)
            curr = getattr(details, "current_name", None) or getattr(details, "new_name", None) or getattr(ev, "current_name", None) or getattr(ev, "new_name", None)

            if prev and curr:
                details_str = f" (Changed from '{prev}' to '{curr}')"
            elif curr:
                details_str = f" (New name: '{curr}')"
            elif prev:
                details_str = f" (Previous name: '{prev}')"

        elif str(ev.event_type).upper() == "MARRIAGE":
            m_details = (
                getattr(ev, "marriage_details", None)
                or getattr(ev, "marriagedetails", None)
            )
            spouse_name = getattr(m_details, "spouse_full_name", None) if m_details else None
            if spouse_name:
                details_str = f" (Spouse: {spouse_name})"

        summary_lines.append(f"  • {ev_type} on {date_str}{details_str}")

    if summary_lines:
        return "\n\nLife Event Updates:\n" + "\n".join(summary_lines)
    return ""


def search_members_comprehensively(keywords):
    """Searches across ALL text fields in Registry and Life Event records using term variants."""
    if not keywords:
        return Registry.objects.none()

    text_fields = _get_registry_text_fields()

    and_registry_q = Q()
    for term in keywords:
        variants = _generate_spelling_variants(term)
        term_q = Q()
        for variant in variants:
            for field in text_fields:
                term_q |= Q(**{f"{field}__icontains": variant})
        and_registry_q &= term_q

    direct_matches = list(Registry.objects.filter(and_registry_q).values_list("id", flat=True)) if text_fields else []

    life_event_member_ids = set()

    name_change_events = LifeEvent.objects.filter(
        event_type__in=["NAME_CHANGE", "NAME CHANGE", "name_change", "name change"]
    ).select_related("member")

    for ev in name_change_events:
        text_data = [
            getattr(ev, "previous_name", ""),
            getattr(ev, "current_name", ""),
            getattr(ev, "old_name", ""),
            getattr(ev, "new_name", ""),
        ]

        details = (
            getattr(ev, "name_change_details", None)
            or getattr(ev, "namechangedetails", None)
            or getattr(ev, "name_change", None)
        )

        if details:
            text_data.extend([
                getattr(details, "previous_name", ""),
                getattr(details, "current_name", ""),
                getattr(details, "old_name", ""),
                getattr(details, "new_name", ""),
                getattr(details, "new_surname", ""),
                getattr(details, "new_firstname", ""),
                getattr(details, "new_middlename", ""),
            ])

        combined_text = " ".join([str(f) for f in text_data if f]).lower()
        if all(any(variant in combined_text for variant in _generate_spelling_variants(term)) for term in keywords):
            if ev.member_id:
                life_event_member_ids.add(ev.member_id)

    marriage_records = MarriageDetails.objects.select_related("member", "life_event")
    for m in marriage_records:
        spouse_name = (getattr(m, "spouse_full_name", "") or "").lower()
        if all(any(variant in spouse_name for variant in _generate_spelling_variants(term)) for term in keywords):
            if m.member_id:
                life_event_member_ids.add(m.member_id)
            elif m.life_event and m.life_event.member_id:
                life_event_member_ids.add(m.life_event.member_id)

    all_member_ids = set(direct_matches).union(life_event_member_ids)
    if all_member_ids:
        return Registry.objects.filter(id__in=all_member_ids)

    return Registry.objects.none()


def process_historian_question(request, question):
    q_raw = question.strip()
    q_lower = q_raw.lower()

    if not q_lower:
        return "Please ask a question about registry members or historical records.", []

    last_member_ids = request.session.get("historian_last_member_ids", [])
    keywords = _extract_search_keywords(q_raw)

    # ============================================================
    # 1. GREETINGS & INTRODUCTIONS
    # ============================================================
    greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    if q_lower in greetings or any(q_lower.startswith(g + " ") or q_lower.startswith(g + "!") for g in greetings):
        return (
            "Greetings! I am the UMUOTUTO Historian. You can ask me about:\n"
            "• Member details (e.g., 'Who is Ebube Emmanuel?', 'Is he married?', 'Who is his father?')\n"
            "• Lineages & Families (e.g., 'Umunagwu lineage')\n"
            "• Oldest/Youngest members (e.g., 'Who is the oldest living member?')\n"
            "• Member status counts (e.g., 'How many married members are registered?')\n"
            "• Event records (e.g., 'How many marriage/death/name change records exist?')",
            [],
        )

    # ============================================================
    # 2. GLOBAL AGGREGATION & COUNTS (Evaluated BEFORE individual member follow-ups)
    # ============================================================
    is_count_query = _has_word(q_lower, ["how many", "count", "total", "number of"])

    if is_count_query or "how many" in q_lower:
        # Married Count
        if "married" in q_lower:
            members = list(Registry.objects.filter(marital_status__iexact="MARRIED"))
            count = len(members)
            request.session["historian_last_member_ids"] = [m.id for m in members]
            request.session["historian_last_topic"] = "married members"
            request.session.modified = True
            return f"There are {count} registered married member(s).", members

        # Single Count
        if "single" in q_lower:
            members = list(Registry.objects.filter(marital_status__iexact="SINGLE"))
            count = len(members)
            request.session["historian_last_member_ids"] = [m.id for m in members]
            request.session["historian_last_topic"] = "single members"
            request.session.modified = True
            return f"There are {count} single member(s) registered.", members

        # Female Count
        if _has_word(q_lower, ["female", "women", "girls"]):
            members = list(Registry.objects.filter(gender__iexact="FEMALE"))
            count = len(members)
            request.session["historian_last_member_ids"] = [m.id for m in members]
            request.session["historian_last_topic"] = "female members"
            request.session.modified = True
            return f"There are {count} registered female member(s).", members

        # Male Count
        if _has_word(q_lower, ["male", "men", "boys"]):
            members = list(Registry.objects.filter(gender__iexact="MALE"))
            count = len(members)
            request.session["historian_last_member_ids"] = [m.id for m in members]
            request.session["historian_last_topic"] = "male members"
            request.session.modified = True
            return f"There are {count} registered male member(s).", members

    # Global Life Event Counts
    if _has_word(q_lower, ["marriage", "marriages"]):
        event_count = LifeEvent.objects.filter(event_type__icontains="MARRIAGE").count()
        detail_count = MarriageDetails.objects.count()
        count = max(event_count, detail_count)
        return f"There are {count} recorded marriage record(s) in the registry.", []

    if _has_word(q_lower, ["death", "deaths", "deceased", "died"]):
        death_events = LifeEvent.objects.filter(event_type__icontains="DEATH")
        count = death_events.count()
        deceased_members = [e.member for e in death_events.select_related("member") if e.member]
        return f"There are {count} registered death record(s) in the registry.", deceased_members

    if _has_word(q_lower, ["name change", "name changes", "changed name"]):
        count = LifeEvent.objects.filter(event_type__icontains="NAME").count()
        return f"There are {count} recorded name change event(s) in the registry.", []

    # ============================================================
    # 3. OLDEST / YOUNGEST LIVING MEMBER LOOKUP
    # ============================================================
    if _has_word(q_lower, ["oldest", "eldest", "youngest", "senior", "age"]):
        is_oldest = _has_word(q_lower, ["oldest", "eldest", "senior"])
        label = "oldest" if is_oldest else "youngest"

        deceased_ids = set(
            LifeEvent.objects.filter(event_type__icontains="DEATH")
            .values_list("member_id", flat=True)
        )
        living_qs = Registry.objects.exclude(id__in=deceased_ids)

        all_fields = [f.name for f in Registry._meta.get_fields() if hasattr(f, 'name')]
        if "is_deceased" in all_fields:
            living_qs = living_qs.filter(is_deceased=False)
        if "status" in all_fields:
            living_qs = living_qs.exclude(status__iexact="DECEASED")

        dob_field = _get_dob_field_name()
        if dob_field:
            order_clause = dob_field if is_oldest else f"-{dob_field}"
            member_with_dob = living_qs.filter(**{f"{dob_field}__isnull": False}).order_by(order_clause).first()

            if member_with_dob:
                dob_val = getattr(member_with_dob, dob_field)
                age = _calculate_age(dob_val)
                age_str = f" (Age: {age})" if age is not None else ""
                dob_str = dob_val.strftime("%B %d, %Y") if hasattr(dob_val, "strftime") else str(dob_val)

                m_name = f"{member_with_dob.surname} {member_with_dob.firstname}"
                m_id = getattr(member_with_dob, "aut_id", member_with_dob.id)

                request.session["historian_last_member_ids"] = [member_with_dob.id]
                request.session["historian_last_topic"] = f"{label} living member"
                request.session.modified = True

                return (
                    f"The {label} living registered member is {m_name} (ID: {m_id}).\n"
                    f"• Date of Birth: {dob_str}{age_str}\n"
                    f"• Family Root: {getattr(member_with_dob, 'family_root', getattr(member_with_dob, 'lineage', 'N/A'))}\n"
                    f"• Marital Status: {getattr(member_with_dob, 'marital_status', 'N/A')}",
                    [member_with_dob],
                )

        first_member = living_qs.order_by("id").first() if is_oldest else living_qs.order_by("-id").first()
        if first_member:
            m_name = f"{first_member.surname} {first_member.firstname}"
            m_id = getattr(first_member, "aut_id", first_member.id)
            return (
                f"Date of birth values are not specified in member profiles to calculate exact age. "
                f"However, based on registry entry order, the earliest registered living member on file is {m_name} (ID: {m_id}).",
                [first_member],
            )
        return "No living members were found in the registry.", []

    # ============================================================
    # 4. ROBUST LINEAGE / FAMILY SEARCH (WITH SPELLING VARIANTS)
    # ============================================================
    lineage_triggers = ["lineage", "family", "root", "kindred", "branch", "belong", "belongs", "umunna", "village", "quarter", "compound", "clan"]
    if _has_word(q_lower, lineage_triggers):
        clean_lineage = re.sub(
            r'\b(lineage|family|root|kindred|umunna|clan|branch|members?|show|list|who|belongs?|belong|is|in|of|to|the)\b',
            '',
            q_lower,
            flags=re.IGNORECASE
        ).strip()
        clean_lineage = re.sub(r'[^\w\s]', '', clean_lineage).strip()

        search_term = clean_lineage if clean_lineage else q_lower
        variants = _generate_spelling_variants(search_term)

        text_fields = _get_registry_text_fields()
        lineage_q = Q()
        for variant in variants:
            for field in text_fields:
                lineage_q |= Q(**{f"{field}__icontains": variant})

        lineage_matches = Registry.objects.filter(lineage_q) if text_fields else Registry.objects.none()
        count = lineage_matches.count()
        topic_label = f"the '{search_term.title()}' lineage/family"

        if count > 0:
            members = list(lineage_matches)
            request.session["historian_last_member_ids"] = [m.id for m in members]
            request.session["historian_last_topic"] = topic_label
            request.session.modified = True

            names = "\n".join([f"• {m.surname} {m.firstname} (ID: {getattr(m, 'aut_id', m.id)})" for m in members[:20]])
            more_suffix = f"\n...and {count - 20} more." if count > 20 else ""

            return f"Found {count} member(s) in {topic_label}:\n{names}{more_suffix}", members

    # ============================================================
    # 5. PRONOUN & SESSION CONTEXT RESOLUTION
    # ============================================================
    context_member = None
    has_he = _has_word(q_lower, ["he", "him", "his"])
    has_she = _has_word(q_lower, ["she", "her", "hers"])

    if (has_he or has_she) and last_member_ids:
        cached_members = list(Registry.objects.filter(id__in=last_member_ids))
        target_gender = "MALE" if has_he else "FEMALE"

        gender_matches = [m for m in cached_members if getattr(m, "gender", "").upper() == target_gender]

        if len(gender_matches) == 1:
            context_member = gender_matches[0]
        elif len(gender_matches) > 1 and not keywords:
            names = "\n".join([f"• {m.surname} {m.firstname} (ID: {getattr(m, 'aut_id', m.id)})" for m in gender_matches])
            label = "male" if target_gender == "MALE" else "female"
            return (
                f"There are {len(gender_matches)} {label} members in context from your previous query. Which one are you asking about?\n{names}",
                gender_matches,
            )
        elif len(cached_members) == 1:
            context_member = cached_members[0]
    elif len(last_member_ids) == 1:
        context_member = Registry.objects.filter(id=last_member_ids[0]).first()

    # ============================================================
    # 6. INDIVIDUAL MEMBER FOLLOW-UPS
    # ============================================================
    followup_keywords = [
        "he", "she", "his", "her", "him", "married", "single", "divorced",
        "status", "child", "children", "daughter", "son", "father", "dad",
        "mother", "mom", "parent", "parents", "wife", "husband", "spouse", "age", "born",
        "life event", "life events", "name change", "changed name", "events"
    ]

    if context_member and _has_word(q_lower, followup_keywords):
        m_name = f"{context_member.surname} {context_member.firstname}"
        m_id = getattr(context_member, "aut_id", context_member.id)

        # Life Events check
        if _has_word(q_lower, ["life event", "life events", "name change", "changed name", "events"]):
            events_summary = _get_member_life_events_summary(context_member)
            if events_summary:
                return f"Here are the recorded life events for {m_name} (ID: {m_id}):{events_summary}", [context_member]
            return f"No recorded life events were found for {m_name} (ID: {m_id}).", [context_member]

        # Father / Mother Lookup
        if _has_word(q_lower, ["father", "dad", "mother", "mom", "parent", "parents"]):
            if _has_word(q_lower, ["father", "dad"]):
                father = getattr(context_member, "father", None)
                if not father and hasattr(context_member, "father_id") and context_member.father_id:
                    father = Registry.objects.filter(id=context_member.father_id).first()

                if father:
                    f_name = f"{father.surname} {father.firstname}"
                    f_id = getattr(father, "aut_id", father.id)
                    request.session["historian_last_member_ids"] = [father.id]
                    request.session["historian_last_topic"] = f"father of {m_name}"
                    request.session.modified = True
                    return f"The father of {m_name} is {f_name} (ID: {f_id}).", [father]

                fathers_name = getattr(context_member, "immediate_fathers_name", None) or getattr(context_member, "father_name", None)
                if fathers_name:
                    matched_father = Registry.objects.filter(
                        Q(firstname__icontains=fathers_name) | Q(surname__icontains=fathers_name)
                    ).first()
                    if matched_father:
                        f_name = f"{matched_father.surname} {matched_father.firstname}"
                        f_id = getattr(matched_father, "aut_id", matched_father.id)
                        request.session["historian_last_member_ids"] = [matched_father.id]
                        request.session["historian_last_topic"] = f"father of {m_name}"
                        request.session.modified = True
                        return f"The father of {m_name} is {f_name} (ID: {f_id}).", [matched_father]

                    return f"The recorded father's name for {m_name} (ID: {m_id}) is '{fathers_name}'.", []

                return f"No father record was found on file for {m_name} (ID: {m_id}).", []

            elif _has_word(q_lower, ["mother", "mom"]):
                mother = getattr(context_member, "mother", None)
                if not mother and hasattr(context_member, "mother_id") and context_member.mother_id:
                    mother = Registry.objects.filter(id=context_member.mother_id).first()

                if mother:
                    mo_name = f"{mother.surname} {mother.firstname}"
                    mo_id = getattr(mother, "aut_id", mother.id)
                    request.session["historian_last_member_ids"] = [mother.id]
                    request.session["historian_last_topic"] = f"mother of {m_name}"
                    request.session.modified = True
                    return f"The mother of {m_name} is {mo_name} (ID: {mo_id}).", [mother]

                mothers_name = getattr(context_member, "mothers_name", None) or getattr(context_member, "mother_name", None)
                if mothers_name:
                    matched_mother = Registry.objects.filter(
                        Q(firstname__icontains=mothers_name) | Q(surname__icontains=mothers_name)
                    ).first()
                    if matched_mother:
                        mo_name = f"{matched_mother.surname} {matched_mother.firstname}"
                        mo_id = getattr(matched_mother, "aut_id", matched_mother.id)
                        request.session["historian_last_member_ids"] = [matched_mother.id]
                        request.session["historian_last_topic"] = f"mother of {m_name}"
                        request.session.modified = True
                        return f"The mother of {m_name} is {mo_name} (ID: {matched_mother.id}).", [matched_mother]

                    return f"The recorded mother's name for {m_name} (ID: {m_id}) is '{mothers_name}'.", []

                return f"No mother record was found on file for {m_name} (ID: {m_id}).", []

        # Spouse Lookup
        if _has_word(q_lower, ["wife", "husband", "spouse", "partner"]):
            spouse = getattr(context_member, "spouse", None)
            if spouse:
                sp_name = f"{spouse.surname} {spouse.firstname}"
                sp_id = getattr(spouse, "aut_id", spouse.id)
                return f"The registered spouse of {m_name} is {sp_name} (ID: {sp_id}).", [spouse]

            marriage = MarriageDetails.objects.filter(Q(husband=context_member) | Q(wife=context_member)).first()
            if marriage:
                sp = marriage.wife if marriage.husband == context_member else marriage.husband
                if sp:
                    sp_name = f"{sp.surname} {sp.firstname}"
                    sp_id = getattr(sp, "aut_id", sp.id)
                    return f"The registered spouse of {m_name} is {sp_name} (ID: {sp_id}).", [sp]

            return f"No registered spouse record was found on file for {m_name} (ID: {m_id}).", []

        # Marital Status Check
        if _has_word(q_lower, ["married", "single", "divorced", "status", "marital"]):
            status = getattr(context_member, "marital_status", "NOT RECORDED")
            return f"{m_name} (ID: {m_id}) is currently registered as {status}.", [context_member]

        # Children Lookup
        if _has_word(q_lower, ["daughter", "son", "child", "children", "kid", "kids", "offspring"]):
            children = _get_member_children(context_member)

            if _has_word(q_lower, ["daughter"]):
                daughters = list(children.filter(gender="FEMALE"))
                count = len(daughters)
                if count > 0:
                    names = "\n".join([f"• {d.surname} {d.firstname} (ID: {getattr(d, 'aut_id', d.id)})" for d in daughters])
                    return f"Yes, {m_name} has {count} registered daughter(s):\n{names}", daughters
                return f"No registered daughters were found on file for {m_name} (ID: {m_id}).", []

            elif _has_word(q_lower, ["son"]):
                sons = list(children.filter(gender="MALE"))
                count = len(sons)
                if count > 0:
                    names = "\n".join([f"• {s.surname} {s.firstname} (ID: {getattr(s, 'aut_id', s.id)})" for s in sons])
                    return f"Yes, {m_name} has {count} registered son(s):\n{names}", sons
                return f"No registered sons were found on file for {m_name} (ID: {m_id}).", []

            else:
                all_children = list(children)
                count = len(all_children)
                if count > 0:
                    names = "\n".join([f"• {c.surname} {c.firstname} (ID: {getattr(c, 'aut_id', c.id)})" for c in all_children])
                    return f"{m_name} has {count} registered child(ren) on file:\n{names}", all_children
                return f"No registered children were found on file for {m_name} (ID: {m_id}).", []

    # ============================================================
    # 7. DIRECT MEMBER & FALLBACK KEYWORD LOOKUP
    # ============================================================
    if keywords:
        matches = search_members_comprehensively(keywords)
        count = matches.count()

        if count > 0:
            members = list(matches[:15])
            request.session["historian_last_member_ids"] = [m.id for m in members]
            request.session["historian_last_topic"] = f"search matching '{' '.join(keywords)}'"
            request.session.modified = True

            if count == 1:
                m = members[0]
                life_events_text = _get_member_life_events_summary(m)

                return (
                    f"Found record for {m.surname} {m.firstname} {getattr(m, 'middlename', '') or ''}\n"
                    f"• Registry ID: {getattr(m, 'aut_id', m.id)}\n"
                    f"• Gender: {getattr(m, 'gender', 'N/A')}\n"
                    f"• Family Root: {getattr(m, 'family_root', getattr(m, 'lineage', 'N/A'))}\n"
                    f"• Marital Status: {getattr(m, 'marital_status', 'N/A')}"
                    f"{life_events_text}",
                    members,
                )
            else:
                names = "\n".join([f"• {m.surname} {m.firstname} (ID: {getattr(m, 'aut_id', m.id)})" for m in members])
                return f"Found {count} matching record(s) for '{' '.join(keywords)}':\n{names}", members

    # ============================================================
    # DEFAULT FALLBACK
    # ============================================================
    query_display = ' '.join(keywords) if keywords else q_raw
    return (
        f"I couldn't find any registered member or life event matching '{query_display}'. "
        "Please provide a member's current or former name, Registry ID, or ask questions like:\n"
        "• 'Who is Ebube Emmanuel?'\n"
        "• 'Who is the oldest living member?'\n"
        "• 'How many married/single members are registered?'\n"
        "• 'Umunagwu lineage' or 'Who belongs to Umunagwu?'\n"
        "• 'How many Marriage/Death/Name Change records are there?'",
        [],
    )