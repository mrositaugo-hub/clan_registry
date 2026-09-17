from datetime import date
import re

from django.db.models import Q

from .models import (
    Registry,
    LifeEvent,
    MarriageDetails,
    DivorceDetails,
)


# ============================================================
# SESSION KEYS
# ============================================================

SESSION_CURRENT_MEMBER = "historian_current_member_id"
SESSION_RESULT_IDS = "historian_last_result_ids"
SESSION_LAST_INTENT = "historian_last_intent"
SESSION_LAST_QUERY = "historian_last_query"
SESSION_PENDING_RELATIONSHIP = "historian_pending_relationship"


# ============================================================
# BASIC TEXT HELPERS
# ============================================================

def normalize(value):
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = re.sub(r"[^\w\s@+.-]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def format_date(value):
    if not value:
        return "Not recorded"

    return value.strftime("%d %B %Y")


def calculate_age(date_of_birth):
    if not date_of_birth:
        return None

    today = date.today()

    age = today.year - date_of_birth.year

    if (today.month, today.day) < (
        date_of_birth.month,
        date_of_birth.day,
    ):
        age -= 1

    return age


def display_value(value):
    if value in (None, ""):
        return "Not recorded"

    return str(value)


def member_name(member):
    parts = [
        clean_text(member.title),
        clean_text(member.firstname),
        clean_text(member.middlename),
        clean_text(member.surname),
    ]

    return " ".join(
        part for part in parts if part
    ).strip()


def short_member_name(member):
    parts = [
        clean_text(member.firstname),
        clean_text(member.middlename),
        clean_text(member.surname),
    ]

    return " ".join(
        part for part in parts if part
    ).strip()


def name_tokens(value):
    return [
        token
        for token in normalize(value).split()
        if token
    ]


def names_equivalent(name_a, name_b):
    a = normalize(name_a)
    b = normalize(name_b)

    if not a or not b:
        return False

    if a == b:
        return True

    tokens_a = name_tokens(a)
    tokens_b = name_tokens(b)

    if tokens_a == tokens_b:
        return True

    if set(tokens_a) == set(tokens_b):
        return True

    # Conservative handling of omitted middle names.
    # Example:
    # "John Doe" == "John Michael Doe"
    if len(tokens_a) == 2 and len(tokens_b) >= 2:
        if (
            tokens_a[0] == tokens_b[0]
            and tokens_a[-1] == tokens_b[-1]
        ):
            return True

    if len(tokens_b) == 2 and len(tokens_a) >= 2:
        if (
            tokens_b[0] == tokens_a[0]
            and tokens_b[-1] == tokens_a[-1]
        ):
            return True

    return False


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def set_current_member(request, member):
    request.session[SESSION_CURRENT_MEMBER] = member.id
    request.session.modified = True


def get_current_member(request):
    member_id = request.session.get(
        SESSION_CURRENT_MEMBER
    )

    if not member_id:
        return None

    try:
        return Registry.objects.get(pk=member_id)
    except Registry.DoesNotExist:
        request.session.pop(
            SESSION_CURRENT_MEMBER,
            None,
        )
        return None


def clear_current_member(request):
    request.session.pop(
        SESSION_CURRENT_MEMBER,
        None,
    )
    request.session.modified = True


def save_result_ids(request, members):
    request.session[SESSION_RESULT_IDS] = [
        member.id for member in members
    ]
    request.session.modified = True


def get_result_members(request):
    ids = request.session.get(
        SESSION_RESULT_IDS,
        [],
    )

    if not ids:
        return []

    members = Registry.objects.filter(
        id__in=ids
    )

    member_map = {
        member.id: member
        for member in members
    }

    return [
        member_map[member_id]
        for member_id in ids
        if member_id in member_map
    ]


def save_historian_state(
    request,
    intent=None,
    query=None,
):
    if intent is not None:
        request.session[
            SESSION_LAST_INTENT
        ] = intent

    if query is not None:
        request.session[
            SESSION_LAST_QUERY
        ] = query

    request.session.modified = True


def clear_pending_relationship(request):
    request.session.pop(
        SESSION_PENDING_RELATIONSHIP,
        None,
    )
    request.session.modified = True


def save_pending_relationship(request, data):
    request.session[
        SESSION_PENDING_RELATIONSHIP
    ] = data
    request.session.modified = True


def get_pending_relationship(request):
    return request.session.get(
        SESSION_PENDING_RELATIONSHIP
    )


def clear_historian_context(request):
    request.session.pop(
        SESSION_CURRENT_MEMBER,
        None,
    )
    request.session.pop(
        SESSION_RESULT_IDS,
        None,
    )
    request.session.pop(
        SESSION_LAST_INTENT,
        None,
    )
    request.session.pop(
        SESSION_LAST_QUERY,
        None,
    )
    request.session.pop(
        SESSION_PENDING_RELATIONSHIP,
        None,
    )
    request.session.modified = True


# ============================================================
# MEMBER SEARCH
# ============================================================

STOP_WORDS = {
    "what",
    "about",
    "tell",
    "me",
    "more",
    "information",
    "info",
    "details",
    "detail",
    "who",
    "is",
    "was",
    "are",
    "the",
    "a",
    "an",
    "this",
    "that",
    "person",
    "member",
    "one",
    "his",
    "her",
    "their",
    "him",
    "them",
    "he",
    "she",
    "they",
    "to",
    "whom",
    "does",
    "did",
    "do",
    "has",
    "have",
    "had",
    "when",
    "where",
    "which",
    "how",
    "why",
    "can",
    "could",
    "would",
    "please",
    "give",
    "show",
    "find",
    "search",
    "for",
    "name",
    "status",
    "marital",
    "spouse",
    "wife",
    "husband",
    "married",
    "marriage",
    "divorce",
    "divorced",
    "death",
    "died",
    "life",
    "event",
    "events",
    "father",
    "mother",
    "parent",
    "parents",
    "birth",
    "born",
    "age",
    "gender",
    "phone",
    "number",
    "contact",
    "occupation",
    "profession",
    "education",
    "qualification",
    "family",
    "clan",
    "village",
    "state",
    "country",
    "lineage",
    "relationship",
    "relation",
    "related",
    "with",
    "and",
}


def exact_id_search(query):
    match = re.search(
        r"\bum[_-]?(\d{1,})\b",
        query,
        flags=re.IGNORECASE,
    )

    if not match:
        return []

    try:
        number = int(match.group(1))
    except ValueError:
        return []

    aut_id = f"UM_{number:06d}"

    return list(
        Registry.objects.filter(
            aut_id__iexact=aut_id
        )
    )


def exact_full_name_search(query):
    query = normalize(query)

    if not query:
        return []

    results = []

    for member in Registry.objects.all():
        if (
            names_equivalent(
                query,
                member_name(member),
            )
            or names_equivalent(
                query,
                short_member_name(member),
            )
        ):
            results.append(member)

    return results


def field_name_search(query):
    if not query:
        return []

    return list(
        Registry.objects.filter(
            Q(firstname__iexact=query)
            | Q(surname__iexact=query)
            | Q(middlename__iexact=query)
            | Q(nickname__iexact=query)
            | Q(title__iexact=query)
        )
    )


def token_name_search(query):
    tokens = [
        token
        for token in query.split()
        if token not in STOP_WORDS
        and len(token) >= 2
    ]

    if not tokens:
        return []

    candidate_sets = []

    for token in tokens:
        matches = list(
            Registry.objects.filter(
                Q(firstname__iexact=token)
                | Q(surname__iexact=token)
                | Q(middlename__iexact=token)
                | Q(nickname__iexact=token)
            )
        )

        if matches:
            candidate_sets.extend(matches)

    unique = {}

    for member in candidate_sets:
        unique[member.id] = member

    return list(unique.values())


def find_members_mentioned(question):
    query = normalize(question)

    if not query:
        return []

    # 1. Registry ID
    id_results = exact_id_search(query)

    if id_results:
        return id_results

    # 2. Exact full/short name
    full_name_results = exact_full_name_search(query)

    if full_name_results:
        return full_name_results

    words = query.split()

    # 3. Search meaningful phrases from longest to shortest.
    for size in range(
        min(6, len(words)),
        0,
        -1,
    ):
        for start in range(
            0,
            len(words) - size + 1,
        ):
            phrase = " ".join(
                words[start:start + size]
            )

            meaningful_tokens = [
                token
                for token in phrase.split()
                if token not in STOP_WORDS
            ]

            if not meaningful_tokens:
                continue

            # Exact name comparison first.
            results = exact_full_name_search(
                phrase
            )

            if results:
                return results

            results = field_name_search(
                phrase
            )

            if results:
                return results

    # 4. Individual name tokens
    return token_name_search(query)


# ============================================================
# RESULT SELECTION
# ============================================================

ORDINALS = {
    "first": 1,
    "1st": 1,
    "one": 1,
    "second": 2,
    "2nd": 2,
    "two": 2,
    "third": 3,
    "3rd": 3,
    "three": 3,
    "fourth": 4,
    "4th": 4,
    "four": 4,
    "fifth": 5,
    "5th": 5,
    "five": 5,
    "sixth": 6,
    "6th": 6,
    "six": 6,
    "seventh": 7,
    "7th": 7,
    "seven": 7,
    "eighth": 8,
    "8th": 8,
    "eight": 8,
    "ninth": 9,
    "9th": 9,
    "nine": 9,
    "tenth": 10,
    "10th": 10,
    "ten": 10,
}


def extract_result_number(query):
    patterns = [
        r"^\s*(\d+)\s*$",
        r"\bnumber\s+(\d+)\b",
        r"\bresult\s+(\d+)\b",
        r"\boption\s+(\d+)\b",
        r"\bmember\s+(\d+)\b",
        r"#\s*(\d+)\b",
        r"\b(\d+)(?:st|nd|rd|th)"
        r"\s+(?:one|member|result)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            query,
        )

        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None

    for word, number in ORDINALS.items():
        if re.search(
            rf"\b{re.escape(word)}"
            rf"(?:\s+(?:one|member|result))?\b",
            query,
        ):
            return number

    return None


def has_gender_selector(query):
    if re.search(
        r"\b(female|woman|lady|girl)\b",
        query,
    ):
        return "FEMALE"

    if re.search(
        r"\b(male|man|gentleman|boy)\b",
        query,
    ):
        return "MALE"

    return None


def has_marital_selector(query):
    if re.search(
        r"\bmarried\b",
        query,
    ):
        return "MARRIED"

    if re.search(
        r"\bsingle\b",
        query,
    ):
        return "SINGLE"

    if re.search(
        r"\bdivorced\b",
        query,
    ):
        return "DIVORCED"

    return None


def is_pure_result_selection(query):
    query = normalize(query)

    if extract_result_number(query) is not None:
        return True

    return bool(
        re.fullmatch(
            r"(the\s+)?"
            r"(first|second|third|fourth|fifth|sixth|"
            r"seventh|eighth|ninth|tenth|last|"
            r"one|two|three|four|five|six|seven|"
            r"eight|nine|ten)"
            r"(?:\s+(one|member|result))?",
            query,
        )
    )


def is_previous_result_filter(query):
    query = normalize(query)

    return query in {
        "female",
        "male",
        "woman",
        "man",
        "lady",
        "gentleman",
        "married",
        "single",
        "divorced",
    }


def is_result_selection_query(query):
    query = normalize(query)

    return (
        is_pure_result_selection(query)
        or is_previous_result_filter(query)
    )


def resolve_from_previous_results(
    request,
    query,
):
    results = get_result_members(request)

    if not results:
        return None, None

    number = extract_result_number(query)

    if number is not None:
        if 1 <= number <= len(results):
            member = results[number - 1]

            set_current_member(
                request,
                member,
            )

            save_result_ids(
                request,
                [member],
            )

            return member, None

        return (
            None,
            (
                f"I only have {len(results)} result"
                f"{'' if len(results) == 1 else 's'} "
                "from the previous search. "
                f"Please choose a number from 1 to "
                f"{len(results)}."
            ),
        )

    if re.fullmatch(
        r"(the\s+)?last"
        r"(?:\s+(?:one|member|result))?",
        query,
    ):
        member = results[-1]

        set_current_member(
            request,
            member,
        )

        save_result_ids(
            request,
            [member],
        )

        return member, None

    gender = has_gender_selector(query)

    if gender:
        filtered = [
            member
            for member in results
            if member.gender == gender
        ]

        if len(filtered) == 1:
            member = filtered[0]

            set_current_member(
                request,
                member,
            )

            save_result_ids(
                request,
                [member],
            )

            return member, None

        if len(filtered) > 1:
            return (
                None,
                build_ambiguity_message(
                    filtered,
                    prefix=(
                        "I found several matching members."
                    ),
                ),
            )

        return (
            None,
            (
                "I could not find a member with that "
                "gender in the previous results."
            ),
        )

    marital_status = has_marital_selector(query)

    if marital_status:
        filtered = [
            member
            for member in results
            if member.marital_status == marital_status
        ]

        if len(filtered) == 1:
            member = filtered[0]

            set_current_member(
                request,
                member,
            )

            save_result_ids(
                request,
                [member],
            )

            return member, None

        if len(filtered) > 1:
            return (
                None,
                build_ambiguity_message(
                    filtered,
                    prefix=(
                        "I found several matching members."
                    ),
                ),
            )

        return (
            None,
            (
                "I could not find a member with that "
                "marital status in the previous results."
            ),
        )

    return None, None


# ============================================================
# CONTEXT / FOLLOW-UP DETECTION
# ============================================================

def contains_pronoun(query):
    words = set(query.split())

    if words & {
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
    }:
        return True

    return any(
        phrase in query
        for phrase in (
            "this member",
            "that member",
            "this person",
            "that person",
        )
    )


def is_identity_question(query):
    patterns = [
        r"^who is (he|him|she|her|they|them)$",
        r"^who is this$",
        r"^who is this member$",
        r"^who is that$",
        r"^who is that member$",
        r"^who is this person$",
        r"^who is that person$",
    ]

    return any(
        re.search(pattern, query)
        for pattern in patterns
    )


def is_full_profile_question(query):
    exact_phrases = {
        "tell me about him",
        "tell me about her",
        "tell me about them",
        "tell me about this member",
        "tell me about that member",
        "what do you know about him",
        "what do you know about her",
        "what do you know about them",
        "what do you know about this member",
        "what do you know about that member",
        "give me information about him",
        "give me information about her",
        "give me information about them",
        "give me details about him",
        "give me details about her",
        "give me details about them",
        "give me his details",
        "give me her details",
        "give me their details",
        "his details",
        "her details",
        "their details",
        "his information",
        "her information",
        "their information",
        "full profile",
        "full details",
        "full information",
        "tell me everything",
        "tell me everything about him",
        "tell me everything about her",
        "tell me everything about them",
        "tell me everything about this member",
        "tell me everything about that member",
    }

    if query in exact_phrases:
        return True

    if (
        contains_pronoun(query)
        and (
            "tell me about" in query
            or "what do you know about" in query
            or "give me information about" in query
            or "give me details about" in query
            or "tell me everything about" in query
        )
    ):
        return True

    return False


def is_short_relationship_question(query):
    patterns = [
        r"^to who$",
        r"^to whom$",
        r"^who did (he|she|they) marry$",
        r"^who did (he|she|they) get married to$",
        r"^who is (his|her|their) (wife|husband|spouse)$",
        r"^(his|her|their) (wife|husband|spouse)$",
        r"^(his|her|their) spouse$",
        r"^spouse$",
        r"^spouse name$",
        r"^who is the spouse$",
    ]

    return any(
        re.search(pattern, query)
        for pattern in patterns
    )


def is_member_attribute_question(query):
    patterns = [
        r"\bmarital status\b",
        r"\bmarried\b",
        r"\bsingle\b",
        r"\bdivorced\b",
        r"\bphone\b",
        r"\bphone number\b",
        r"\bcontact\b",
        r"\bdate of birth\b",
        r"\bplace of birth\b",
        r"\bborn\b",
        r"\bage\b",
        r"\bgender\b",
        r"\bfather\b",
        r"\bmother\b",
        r"\bparents?\b",
        r"\bfamily lineage\b",
        r"\bfamily name\b",
        r"\bfamily root\b",
        r"\bclan\b",
        r"\bvillage\b",
        r"\bstate\b",
        r"\bcountry\b",
        r"\blineage\b",
        r"\boccupation\b",
        r"\bprofession\b",
        r"\bacademic\b",
        r"\bqualification\b",
        r"\beducation\b",
        r"\bspouse\b",
        r"\bwife\b",
        r"\bhusband\b",
        r"\bmarriage\b",
        r"\bdivorce\b",
        r"\bdeath\b",
        r"\blife events?\b",
        r"\bhistory\b",
        r"\bevents\b",
        r"\bdetails\b",
        r"\bprofile\b",
        r"\binformation\b",
    ]

    return any(
        re.search(pattern, query)
        for pattern in patterns
    )


def is_contextual_followup(query):
    return (
        is_identity_question(query)
        or is_full_profile_question(query)
        or is_short_relationship_question(query)
        or contains_pronoun(query)
        or is_member_attribute_question(query)
    )


def is_member_question_query(query):
    return bool(
        re.match(
            r"^(who|what|when|where|how|is|was|are|"
            r"does|did|has|have|can|tell|give|show)\b",
            query,
        )
    )


# ============================================================
# MEMBER PROFILE / SPOUSE DATA
# ============================================================

def get_member_spouse_information(member):
    registry_spouse = clean_text(
        member.spouse_full_name
    )

    marriage = (
        MarriageDetails.objects
        .filter(
            life_event__member=member
        )
        .select_related("life_event")
        .order_by("-date_of_marriage")
        .first()
    )

    divorce = (
        DivorceDetails.objects
        .filter(
            life_event__member=member
        )
        .select_related("life_event")
        .order_by("-date_of_divorce")
        .first()
    )

    spouse_name = registry_spouse

    if not spouse_name and marriage:
        spouse_name = clean_text(
            marriage.spouse_full_name
        )

    if not spouse_name and divorce:
        spouse_name = clean_text(
            divorce.spouse_full_name
        )

    return {
        "spouse_name": spouse_name,
        "registry_marriage_date": member.date_of_marriage,
        "marriage": marriage,
        "divorce": divorce,
    }


def build_member_profile(member):
    spouse_info = get_member_spouse_information(
        member
    )

    marriage = spouse_info["marriage"]
    divorce = spouse_info["divorce"]

    age = calculate_age(
        member.date_of_birth
    )

    return {
        "registry_id": member.aut_id,
        "name": member_name(member),
        "title": display_value(member.title),
        "surname": display_value(member.surname),
        "firstname": display_value(member.firstname),
        "middlename": display_value(member.middlename),
        "nickname": display_value(member.nickname),
        "gender": member.get_gender_display(),
        "date_of_birth": format_date(
            member.date_of_birth
        ),
        "age": (
            age
            if age is not None
            else "Not available"
        ),
        "place_of_birth": display_value(
            member.place_of_birth
        ),
        "family_root": (
            member.get_family_root_display()
        ),
        "family_lineage": display_value(
            member.family_lineage
        ),
        "family_name": display_value(
            member.family_name
        ),
        "father": display_value(
            member.immediate_fathers_name
        ),
        "mother": display_value(
            member.mother_name
        ),
        "mother_clan": display_value(
            member.mother_clan
        ),
        "mother_village": display_value(
            member.mother_village
        ),
        "mother_state": display_value(
            member.mother_state
        ),
        "mother_country": display_value(
            member.mother_country
        ),
        "phone_number": display_value(
            member.phone_number
        ),
        "marital_status": (
            member.get_marital_status_display()
        ),
        "spouse": display_value(
            spouse_info["spouse_name"]
        ),
        "date_of_marriage": format_date(
            member.date_of_marriage
            or (
                marriage.date_of_marriage
                if marriage
                else None
            )
        ),
        "spouse_clan": display_value(
            member.spouse_clan
            or (
                marriage.spouse_clan
                if marriage
                else ""
            )
        ),
        "spouse_village": display_value(
            member.spouse_village
            or (
                marriage.spouse_village
                if marriage
                else ""
            )
        ),
        "spouse_state": display_value(
            member.spouse_state
            or (
                marriage.spouse_state
                if marriage
                else ""
            )
        ),
        "spouse_country": display_value(
            member.spouse_country
            or (
                marriage.spouse_country
                if marriage
                else ""
            )
        ),
        "date_of_divorce": format_date(
            member.date_of_divorce
            or (
                divorce.date_of_divorce
                if divorce
                else None
            )
        ),
        "academic_qualification": display_value(
            member.academic_qualification
        ),
        "area_of_profession": display_value(
            member.area_of_profession
        ),
        "occupation": display_value(
            member.occupation
        ),
    }


def build_full_profile_answer(member):
    profile = build_member_profile(
        member
    )

    return (
        f"{profile['name']} "
        f"({profile['registry_id']}).\n"
        f"Gender: {profile['gender']}.\n"
        f"Date of birth: "
        f"{profile['date_of_birth']}.\n"
        f"Age: {profile['age']}.\n"
        f"Place of birth: "
        f"{profile['place_of_birth']}.\n"
        f"Family root: "
        f"{profile['family_root']}.\n"
        f"Family lineage: "
        f"{profile['family_lineage']}.\n"
        f"Family name: "
        f"{profile['family_name']}.\n"
        f"Father: {profile['father']}.\n"
        f"Mother: {profile['mother']}.\n"
        f"Mother's clan: "
        f"{profile['mother_clan']}.\n"
        f"Mother's village: "
        f"{profile['mother_village']}.\n"
        f"Mother's state: "
        f"{profile['mother_state']}.\n"
        f"Mother's country: "
        f"{profile['mother_country']}.\n"
        f"Marital status: "
        f"{profile['marital_status']}.\n"
        f"Spouse: {profile['spouse']}.\n"
        f"Date of marriage: "
        f"{profile['date_of_marriage']}.\n"
        f"Spouse's clan: "
        f"{profile['spouse_clan']}.\n"
        f"Spouse's village: "
        f"{profile['spouse_village']}.\n"
        f"Spouse's state: "
        f"{profile['spouse_state']}.\n"
        f"Spouse's country: "
        f"{profile['spouse_country']}.\n"
        f"Date of divorce: "
        f"{profile['date_of_divorce']}.\n"
        f"Academic qualification: "
        f"{profile['academic_qualification']}.\n"
        f"Area of profession: "
        f"{profile['area_of_profession']}.\n"
        f"Occupation: "
        f"{profile['occupation']}."
    )


# ============================================================
# LIFE EVENTS
# ============================================================

def answer_member_life_events(member):
    events = (
        LifeEvent.objects
        .filter(member=member)
        .select_related(
            "marriage_details",
            "divorce_details",
        )
        .order_by("event_date")
    )

    if not events.exists():
        return (
            f"No Life Events are currently recorded "
            f"for {member_name(member)}."
        )

    lines = [
        f"Life Events recorded for "
        f"{member_name(member)}:"
    ]

    for event in events:
        line = (
            f"• {event.get_event_type_display()} — "
            f"{format_date(event.event_date)}"
        )

        if event.event_location:
            line += (
                f" — {event.event_location}"
            )

        if event.event_type == "MARRIAGE":
            try:
                details = event.marriage_details
                line += (
                    f" — Spouse: "
                    f"{details.spouse_full_name}"
                )
            except MarriageDetails.DoesNotExist:
                pass

        elif event.event_type == "DIVORCE":
            try:
                details = event.divorce_details
                line += (
                    f" — Spouse: "
                    f"{details.spouse_full_name}"
                )
            except DivorceDetails.DoesNotExist:
                pass

        lines.append(line)

    return "\n".join(lines)


def answer_life_event_question(question):
    query = normalize(question)

    if not any(
        word in query
        for word in (
            "how many",
            "number of",
            "count",
            "total",
        )
    ):
        return None

    if "death" in query or "deaths" in query:
        count = LifeEvent.objects.filter(
            event_type="DEATH"
        ).count()

        return (
            f"There are {count} recorded death "
            f"Life Event"
            f"{'s' if count != 1 else ''}."
        )

    if "marriage" in query or "marriages" in query:
        count = LifeEvent.objects.filter(
            event_type="MARRIAGE"
        ).count()

        return (
            f"There are {count} recorded marriage "
            f"Life Event"
            f"{'s' if count != 1 else ''}."
        )

    if "divorce" in query or "divorces" in query:
        count = LifeEvent.objects.filter(
            event_type="DIVORCE"
        ).count()

        return (
            f"There are {count} recorded divorce "
            f"Life Event"
            f"{'s' if count != 1 else ''}."
        )

    count = LifeEvent.objects.count()

    return (
        f"There are {count} recorded Life Events."
    )


# ============================================================
# MEMBER QUESTION ANSWERS
# ============================================================

def answer_member_question(
    member,
    question,
):
    query = normalize(question)
    name = member_name(member)

    if (
        is_identity_question(query)
        or is_full_profile_question(query)
    ):
        return build_full_profile_answer(member)

    if query in {
        "details",
        "detail",
        "profile",
        "information",
        "full profile",
        "full details",
        "full information",
        "tell me everything",
        "everything",
        "more",
        "more details",
        "more information",
    }:
        return build_full_profile_answer(member)

    spouse_info = get_member_spouse_information(
        member
    )

    spouse_name = spouse_info["spouse_name"]
    marriage = spouse_info["marriage"]
    divorce = spouse_info["divorce"]

    # --------------------------------------------------------
    # SPOUSE
    # --------------------------------------------------------

    if (
        is_short_relationship_question(query)
        or re.search(
            r"\b(spouse|wife|husband)\b",
            query,
        )
        or re.search(
            r"\bwho did (he|she|they) marry\b",
            query,
        )
    ):
        if spouse_name:
            return (
                f"{name}'s recorded spouse is "
                f"{spouse_name}."
            )

        return (
            f"{name} is recorded as "
            f"{member.get_marital_status_display().lower()}, "
            "but the spouse's name is not recorded."
        )

    # --------------------------------------------------------
    # MARITAL STATUS
    # --------------------------------------------------------

    if (
        "marital status" in query
        or re.search(
            r"\bmarried\b",
            query,
        )
        or re.search(
            r"\bsingle\b",
            query,
        )
        or re.search(
            r"\bdivorced\b",
            query,
        )
    ):
        status = member.get_marital_status_display()

        return (
            f"{name} is currently recorded as "
            f"{status}."
        )

    # --------------------------------------------------------
    # MARRIAGE DATE
    # --------------------------------------------------------

    if (
        "date of marriage" in query
        or "when did he marry" in query
        or "when did she marry" in query
        or "when did they marry" in query
        or "when was he married" in query
        or "when was she married" in query
        or "when was the marriage" in query
    ):
        marriage_date = (
            member.date_of_marriage
            or (
                marriage.date_of_marriage
                if marriage
                else None
            )
        )

        if marriage_date:
            return (
                f"{name} was married on "
                f"{format_date(marriage_date)}."
            )

        return (
            f"The marriage date for {name} "
            "is not recorded."
        )

    # --------------------------------------------------------
    # DIVORCE DATE
    # --------------------------------------------------------

    if (
        "date of divorce" in query
        or "when did he divorce" in query
        or "when did she divorce" in query
        or "when did they divorce" in query
        or "when was the divorce" in query
    ):
        divorce_date = (
            member.date_of_divorce
            or (
                divorce.date_of_divorce
                if divorce
                else None
            )
        )

        if divorce_date:
            return (
                f"{name}'s divorce was recorded on "
                f"{format_date(divorce_date)}."
            )

        return (
            f"The divorce date for {name} "
            "is not recorded."
        )

    profile = build_member_profile(member)

    # --------------------------------------------------------
    # SPOUSE DETAILS
    # --------------------------------------------------------

    spouse_patterns = {
        "spouse clan": (
            "spouse_clan",
            "spouse's clan",
        ),
        "spouse village": (
            "spouse_village",
            "spouse's village",
        ),
        "spouse state": (
            "spouse_state",
            "spouse's state",
        ),
        "spouse country": (
            "spouse_country",
            "spouse's country",
        ),
    }

    for pattern, (
        field,
        label,
    ) in spouse_patterns.items():
        if pattern in query:
            return (
                f"{label.capitalize()} for "
                f"{name}: {profile[field]}."
            )

    # --------------------------------------------------------
    # BIRTH
    # --------------------------------------------------------

    if (
        "date of birth" in query
        or "born" in query
    ):
        return (
            f"{name}'s date of birth is "
            f"{format_date(member.date_of_birth)}."
        )

    if (
        "place of birth" in query
        or "where was he born" in query
        or "where was she born" in query
        or "where were they born" in query
    ):
        return (
            f"{name}'s place of birth is "
            f"{display_value(member.place_of_birth)}."
        )

    # --------------------------------------------------------
    # AGE
    # --------------------------------------------------------

    if "age" in query:
        age = calculate_age(
            member.date_of_birth
        )

        if age is None:
            return (
                f"The date of birth for {name} "
                "is not recorded, so I cannot "
                "calculate the age."
            )

        return (
            f"{name} is {age} years old."
        )

    # --------------------------------------------------------
    # GENDER
    # --------------------------------------------------------

    if "gender" in query:
        return (
            f"{name}'s gender is "
            f"{member.get_gender_display()}."
        )

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    if (
        "phone" in query
        or "contact" in query
        or "telephone" in query
    ):
        return (
            f"{name}'s phone number is "
            f"{display_value(member.phone_number)}."
        )

    # --------------------------------------------------------
    # MATERNAL DETAILS
    # IMPORTANT: These come BEFORE generic "mother".
    # --------------------------------------------------------

    maternal_fields = [
        (
            "mother clan",
            member.mother_clan,
            "mother's clan",
        ),
        (
            "mother village",
            member.mother_village,
            "mother's village",
        ),
        (
            "mother state",
            member.mother_state,
            "mother's state",
        ),
        (
            "mother country",
            member.mother_country,
            "mother's country",
        ),
    ]

    for pattern, value, label in maternal_fields:
        if pattern in query:
            return (
                f"{name}'s {label} is "
                f"{display_value(value)}."
            )

    # --------------------------------------------------------
    # FATHER
    # --------------------------------------------------------

    if "father" in query:
        return (
            f"{name}'s father's name is "
            f"{display_value(member.immediate_fathers_name)}."
        )

    # --------------------------------------------------------
    # MOTHER
    # --------------------------------------------------------

    if "mother" in query:
        return (
            f"{name}'s mother's name is "
            f"{display_value(member.mother_name)}."
        )

    # --------------------------------------------------------
    # FAMILY
    # --------------------------------------------------------

    if "family root" in query:
        return (
            f"{name} belongs to the "
            f"{member.get_family_root_display()} "
            "family root."
        )

    if (
        "family lineage" in query
        or "lineage" in query
    ):
        return (
            f"{name}'s family lineage is "
            f"{display_value(member.family_lineage)}."
        )

    if "family name" in query:
        return (
            f"{name}'s family name is "
            f"{display_value(member.family_name)}."
        )

    if (
        query == "family"
        or "family information" in query
    ):
        return (
            f"{name} belongs to the "
            f"{member.get_family_root_display()} "
            f"family root. "
            f"Family lineage: "
            f"{display_value(member.family_lineage)}. "
            f"Family name: "
            f"{display_value(member.family_name)}."
        )

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    if (
        "academic qualification" in query
        or "qualification" in query
        or "education" in query
    ):
        return (
            f"{name}'s academic qualification is "
            f"{display_value(member.academic_qualification)}."
        )

    # --------------------------------------------------------
    # PROFESSION
    # --------------------------------------------------------

    if (
        "area of profession" in query
        or "profession" in query
    ):
        return (
            f"{name}'s area of profession is "
            f"{display_value(member.area_of_profession)}."
        )

    # --------------------------------------------------------
    # OCCUPATION
    # --------------------------------------------------------

    if (
        "occupation" in query
        or "job" in query
    ):
        return (
            f"{name}'s occupation is "
            f"{display_value(member.occupation)}."
        )

    # --------------------------------------------------------
    # LIFE EVENTS
    # --------------------------------------------------------

    if (
        "life event" in query
        or "life events" in query
        or "history" in query
        or "events" in query
    ):
        return answer_member_life_events(
            member
        )

    # --------------------------------------------------------
    # GENERAL ABOUT
    # --------------------------------------------------------

    if (
        "about" in query
        or "information" in query
        or "details" in query
        or "profile" in query
    ):
        return build_full_profile_answer(
            member
        )

    return (
        f"I have {name} selected. "
        "You can ask me about the member's "
        "birth, age, family, parents, marital "
        "status, spouse, marriage, divorce, "
        "occupation, education, contact details, "
        "or Life Events."
    )


# ============================================================
# STATISTICS
# ============================================================

def statistics_answer(question):
    query = normalize(question)

    count_words = [
        "how many",
        "number of",
        "count",
        "total",
    ]

    if not any(
        word in query
        for word in count_words
    ):
        return None

    # Let the family-root handler answer root-specific
    # statistics instead of returning the overall total.
    if any(
        root in query
        for root in (
            "umunangwu",
            "umugbanoke",
            "umuchukwu",
        )
    ):
        return None

    if (
        "male" in query
        and "female" not in query
    ):
        count = Registry.objects.filter(
            gender="MALE"
        ).count()

        return (
            f"There are {count} registered "
            "male members."
        )

    if "female" in query:
        count = Registry.objects.filter(
            gender="FEMALE"
        ).count()

        return (
            f"There are {count} registered "
            "female members."
        )

    if "married" in query:
        count = Registry.objects.filter(
            marital_status="MARRIED"
        ).count()

        return (
            f"There are {count} registered "
            "married members."
        )

    if "divorced" in query:
        count = Registry.objects.filter(
            marital_status="DIVORCED"
        ).count()

        return (
            f"There are {count} registered "
            "divorced members."
        )

    if "single" in query:
        count = Registry.objects.filter(
            marital_status="SINGLE"
        ).count()

        return (
            f"There are {count} registered "
            "single members."
        )

    life_event_result = answer_life_event_question(
        query
    )

    if life_event_result:
        return life_event_result

    if (
        "member" in query
        or "members" in query
        or "people" in query
        or "persons" in query
        or "registry" in query
        or "registered" in query
    ):
        count = Registry.objects.count()

        return (
            f"There are {count} registered members "
            "in the Global Registry."
        )

    return None


# ============================================================
# FAMILY ROOT ANSWERS
# ============================================================

def family_root_answer(question):
    query = normalize(question)

    roots = {
        "umunangwu": "UMUNANGWU",
        "umugbanoke": "UMUGBANOKE",
        "umuchukwu": "UMUCHUKWU",
    }

    selected_root = None

    for keyword, value in roots.items():
        if keyword in query:
            selected_root = value
            break

    if not selected_root:
        return None

    if (
        "how many" in query
        or "number of" in query
        or "count" in query
        or "members" in query
        or "people" in query
    ):
        count = Registry.objects.filter(
            family_root=selected_root
        ).count()

        return (
            f"There are {count} registered members "
            f"under {selected_root.title()}."
        )

    members = list(
        Registry.objects.filter(
            family_root=selected_root
        ).order_by(
            "surname",
            "firstname",
            "middlename",
        )
    )

    if not members:
        return (
            f"No registered members were found "
            f"under {selected_root.title()}."
        )

    return (
        f"I found {len(members)} registered members "
        f"under {selected_root.title()}.",
        members,
    )


# ============================================================
# GREETINGS / HELP
# ============================================================

def greeting_answer(query):
    greetings = {
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "greetings",
    }

    if query in greetings:
        return (
            "Welcome to the UMUOTUTO HISTORIAN. "
            "Ask me about a registered member, "
            "family information, Life Events, "
            "or registry statistics."
        )

    return None


def thanks_answer(query):
    thanks = {
        "thanks",
        "thank you",
        "thank you very much",
        "thanks a lot",
    }

    if query in thanks:
        return (
            "You're welcome. "
            "I am ready for the next registry question."
        )

    return None


def help_answer(query):
    if query in {
        "help",
        "what can you do",
        "what can you tell me",
        "how do i use this",
        "how can you help me",
    }:
        return (
            "I can search the UMUOTUTO Registry by "
            "member name or Registry ID and answer "
            "questions about a member's identity, "
            "birth, age, family, parents, marital "
            "status, spouse, marriage, divorce, "
            "education, profession, occupation, "
            "contact details and Life Events. "
            "I can also compare members when the "
            "stored registry information supports "
            "a relationship."
        )

    return None


# ============================================================
# AMBIGUITY
# ============================================================

def build_ambiguity_message(
    members,
    prefix="I found several matching members.",
):
    lines = [prefix]

    for index, member in enumerate(
        members,
        start=1,
    ):
        lines.append(
            f"{index}. {member_name(member)} "
            f"({member.aut_id})"
        )

    lines.append(
        "Please choose a number, for example: "
        "\"number 2\"."
    )

    return "\n".join(lines)


# ============================================================
# SEARCH RESPONSE
# ============================================================

def search_member_response(
    request,
    members,
):
    if not members:
        return (
            "I could not find a registered member "
            "matching that name or Registry ID. "
            "Please check the spelling or provide "
            "the member's Registry ID."
        ), []

    if len(members) == 1:
        member = members[0]

        set_current_member(
            request,
            member,
        )

        save_result_ids(
            request,
            [member],
        )

        return (
            f"I have found {member_name(member)}. "
            "What would you like to know about "
            "this member?"
        ), [member]

    save_result_ids(
        request,
        members,
    )

    clear_current_member(request)

    return (
        build_ambiguity_message(members),
        members,
    )


# ============================================================
# CONTEXT RESOLUTION
# ============================================================

def resolve_context_without_selector(request):
    current = get_current_member(request)

    if current:
        return current, None

    previous_results = get_result_members(request)

    if len(previous_results) == 1:
        member = previous_results[0]

        set_current_member(
            request,
            member,
        )

        return member, None

    if len(previous_results) > 1:
        return (
            None,
            build_ambiguity_message(
                previous_results,
                prefix=(
                    "I still have several matching "
                    "members from the previous search. "
                    "Please choose one first."
                ),
            ),
        )

    return None, None


def resolve_context_member(
    request,
    query,
):
    previous_results = get_result_members(
        request
    )

    if is_previous_result_filter(query):
        member, message = (
            resolve_from_previous_results(
                request,
                query,
            )
        )

        if member or message:
            return member, message

    return resolve_context_without_selector(
        request
    )


# ============================================================
# RELATIONSHIP QUESTIONS
# ============================================================

def clean_person_reference(text):
    text = clean_text(text)

    text = re.sub(
        r"['’]s\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\bs$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = normalize(text)

    text = re.sub(
        r"^(the|a|an)\s+",
        "",
        text,
    )

    return text.strip()


def split_person_targets(text):
    text = clean_person_reference(text)

    return [
        item.strip()
        for item in re.split(
            r"\s*,\s*|\s+and\s+",
            text,
        )
        if item.strip()
    ]


def extract_relationship_parts(question):
    query = normalize(question)

    # relationship between A and B
    match = re.search(
        r"^relationship between\s+(.+?)\s+and\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # what is the relationship between A and B
    match = re.search(
        r"^what is the relationship between\s+"
        r"(.+?)\s+and\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # how is A related to B
    match = re.search(
        r"^how is\s+(.+?)\s+related\s+"
        r"(?:to|with)\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # how are A and B related
    match = re.search(
        r"^how are\s+(.+?)\s+and\s+(.+?)\s+related$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # what is A's relationship with B
    match = re.search(
        r"^what is\s+(.+?)\s+"
        r"(?:relationship|relation)\s+"
        r"(?:with|to)\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # what is the relationship of A with B
    match = re.search(
        r"^what is the relationship of\s+"
        r"(.+?)\s+(?:with|to)\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # what relation does A have with B
    match = re.search(
        r"^what relation does\s+(.+?)\s+"
        r"have\s+(?:with|to)\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # is A related to/with B
    match = re.search(
        r"^is\s+(.+?)\s+related\s+"
        r"(?:to|with)\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # what is his relationship with B
    # his relationship with B
    match = re.search(
        r"^(?:what is\s+)?(.+?)\s+"
        r"(?:relationship|relation)\s+"
        r"(?:with|to)\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": clean_person_reference(
                match.group(1)
            ),
            "targets": split_person_targets(
                match.group(2)
            ),
        }

    # implicit current member:
    # relationship with B
    # related to B
    match = re.search(
        r"^(?:what is\s+)?"
        r"(?:the\s+)?"
        r"(?:relationship|relation)\s+"
        r"(?:with|to)\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": None,
            "targets": split_person_targets(
                match.group(1)
            ),
        }

    match = re.search(
        r"^(?:is\s+)?"
        r"(?:he|she|they|him|her|them|this member|"
        r"that member|this person|that person)\s+"
        r"related\s+(?:to|with)\s+(.+)$",
        query,
    )

    if match:
        return {
            "first": None,
            "targets": split_person_targets(
                match.group(1)
            ),
        }

    return None


def is_relationship_question(query):
    return extract_relationship_parts(
        query
    ) is not None


def resolve_person_text(
    text,
    request=None,
    allow_context=False,
):
    text = clean_person_reference(text)

    if not text:
        return []

    contextual_words = {
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
        "this member",
        "that member",
        "this person",
        "that person",
    }

    if allow_context and text in contextual_words:
        current = (
            get_current_member(request)
            if request
            else None
        )

        return [current] if current else []

    return find_members_mentioned(text)


def relationship_from_registry(
    member_a,
    member_b,
):
    name_a = member_name(member_a)
    name_b = member_name(member_b)

    if member_a.id == member_b.id:
        return (
            "same_record",
            (
                f"{name_a} and {name_b} are the "
                "same registry record."
            ),
        )

    # --------------------------------------------------------
    # SPOUSE
    # --------------------------------------------------------

    spouse_a = get_member_spouse_information(
        member_a
    )["spouse_name"]

    spouse_b = get_member_spouse_information(
        member_b
    )["spouse_name"]

    if spouse_a and (
        names_equivalent(
            spouse_a,
            name_b,
        )
        or names_equivalent(
            spouse_a,
            short_member_name(member_b),
        )
    ):
        return (
            "spouse",
            (
                f"{name_a} is recorded as "
                f"the spouse of {name_b}."
            ),
        )

    if spouse_b and (
        names_equivalent(
            spouse_b,
            name_a,
        )
        or names_equivalent(
            spouse_b,
            short_member_name(member_a),
        )
    ):
        return (
            "spouse",
            (
                f"{name_b} is recorded as "
                f"the spouse of {name_a}."
            ),
        )

    # --------------------------------------------------------
    # PARENT / CHILD
    # --------------------------------------------------------

    father_a = clean_text(
        member_a.immediate_fathers_name
    )

    father_b = clean_text(
        member_b.immediate_fathers_name
    )

    mother_a = clean_text(
        member_a.mother_name
    )

    mother_b = clean_text(
        member_b.mother_name
    )

    if father_a and (
        names_equivalent(
            father_a,
            name_b,
        )
        or names_equivalent(
            father_a,
            short_member_name(member_b),
        )
    ):
        return (
            "parent",
            (
                f"{name_b} is recorded as "
                f"{name_a}'s father."
            ),
        )

    if father_b and (
        names_equivalent(
            father_b,
            name_a,
        )
        or names_equivalent(
            father_b,
            short_member_name(member_a),
        )
    ):
        return (
            "parent",
            (
                f"{name_a} is recorded as "
                f"{name_b}'s father."
            ),
        )

    if mother_a and (
        names_equivalent(
            mother_a,
            name_b,
        )
        or names_equivalent(
            mother_a,
            short_member_name(member_b),
        )
    ):
        return (
            "parent",
            (
                f"{name_b} is recorded as "
                f"{name_a}'s mother."
            ),
        )

    if mother_b and (
        names_equivalent(
            mother_b,
            name_a,
        )
        or names_equivalent(
            mother_b,
            short_member_name(member_a),
        )
    ):
        return (
            "parent",
            (
                f"{name_a} is recorded as "
                f"{name_b}'s mother."
            ),
        )

    # --------------------------------------------------------
    # SIBLINGS
    # --------------------------------------------------------

    shared_father = (
        father_a
        and father_b
        and names_equivalent(
            father_a,
            father_b,
        )
    )

    shared_mother = (
        mother_a
        and mother_b
        and names_equivalent(
            mother_a,
            mother_b,
        )
    )

    if shared_father or shared_mother:
        return (
            "siblings",
            (
                f"{name_a} and {name_b} appear "
                "to be siblings based on their "
                "recorded parent information."
            ),
        )

    # --------------------------------------------------------
    # NO RECORDED RELATIONSHIP
    # --------------------------------------------------------

    return (
        None,
        (
            f"I cannot establish a recorded "
            f"relationship between {name_a} and "
            f"{name_b} from the information currently "
            "stored in the registry."
        ),
    )


# ============================================================
# PENDING RELATIONSHIP SUPPORT
# ============================================================

def resolve_relationship_targets(
    request,
    subject,
    target_texts,
    resolved_members=None,
    start_index=0,
):
    resolved_members = list(
        resolved_members or []
    )

    for index in range(
        start_index,
        len(target_texts),
    ):
        target_text = target_texts[index]

        target_members = resolve_person_text(
            target_text,
            request=request,
            allow_context=True,
        )

        if not target_members:
            return (
                None,
                [],
                (
                    f"I could not find a registered "
                    f"member matching '{target_text}'."
                ),
            )

        if len(target_members) > 1:
            save_result_ids(
                request,
                target_members,
            )

            save_pending_relationship(
                request,
                {
                    "mode": "target",
                    "subject_id": subject.id,
                    "target_texts": target_texts,
                    "resolved_target_ids": [
                        member.id
                        for member in resolved_members
                    ],
                    "pending_index": index,
                },
            )

            return (
                None,
                target_members,
                build_ambiguity_message(
                    target_members,
                    prefix=(
                        f"I found several members "
                        f"matching '{target_text}'. "
                        "Please choose which one you mean."
                    ),
                ),
            )

        resolved_members.append(
            target_members[0]
        )

    return resolved_members, [], None


def finish_relationship(
    request,
    subject,
    targets,
):
    answers = []
    all_members = [subject]

    for target in targets:
        _, answer = relationship_from_registry(
            subject,
            target,
        )

        answers.append(answer)

        if target.id not in {
            member.id
            for member in all_members
        }:
            all_members.append(target)

    save_result_ids(
        request,
        all_members,
    )

    set_current_member(
        request,
        subject,
    )

    save_historian_state(
        request,
        intent="relationship",
    )

    if len(answers) == 1:
        return answers[0], all_members

    return (
        "\n".join(answers),
        all_members,
    )


def resume_pending_relationship_selection(
    request,
    query,
):
    pending = get_pending_relationship(request)

    if not pending:
        return None

    if not is_pure_result_selection(query):
        return None

    selected_member, message = (
        resolve_from_previous_results(
            request,
            query,
        )
    )

    if message:
        return (
            message,
            get_result_members(request),
        )

    if not selected_member:
        return None

    mode = pending.get("mode")

    if mode == "subject":
        target_texts = pending.get(
            "target_texts",
            [],
        )

        targets, ambiguity_members, error = (
            resolve_relationship_targets(
                request,
                selected_member,
                target_texts,
            )
        )

        if error:
            return (
                error,
                ambiguity_members,
            )

        clear_pending_relationship(request)

        return finish_relationship(
            request,
            selected_member,
            targets,
        )

    if mode == "target":
        try:
            subject = Registry.objects.get(
                pk=pending["subject_id"]
            )
        except (
            Registry.DoesNotExist,
            KeyError,
            TypeError,
        ):
            clear_pending_relationship(request)
            return (
                "The previous relationship request "
                "is no longer available. Please ask "
                "the relationship question again.",
                [],
            )

        target_texts = pending.get(
            "target_texts",
            [],
        )

        pending_index = pending.get(
            "pending_index",
            0,
        )

        resolved_ids = pending.get(
            "resolved_target_ids",
            [],
        )

        resolved_members = list(
            Registry.objects.filter(
                id__in=resolved_ids
            )
        )

        member_map = {
            member.id: member
            for member in resolved_members
        }

        ordered_resolved = [
            member_map[member_id]
            for member_id in resolved_ids
            if member_id in member_map
        ]

        ordered_resolved.append(
            selected_member
        )

        targets, ambiguity_members, error = (
            resolve_relationship_targets(
                request,
                subject,
                target_texts,
                resolved_members=ordered_resolved,
                start_index=pending_index + 1,
            )
        )

        if error:
            return (
                error,
                ambiguity_members,
            )

        clear_pending_relationship(request)

        return finish_relationship(
            request,
            subject,
            targets,
        )

    clear_pending_relationship(request)

    return None


def answer_relationship_question(
    request,
    question,
):
    query = normalize(question)

    if not is_relationship_question(query):
        return None, []

    parts = extract_relationship_parts(
        question
    )

    if not parts:
        return None, []

    first_text = parts["first"]
    target_texts = parts["targets"]

    current_member = get_current_member(
        request
    )

    # --------------------------------------------------------
    # SUBJECT
    # --------------------------------------------------------

    if first_text:
        first_members = resolve_person_text(
            first_text,
            request=request,
            allow_context=True,
        )

        if not first_members:
            return (
                (
                    f"I could not find a registered "
                    f"member matching '{first_text}'."
                ),
                [],
            )

        if len(first_members) > 1:
            save_result_ids(
                request,
                first_members,
            )

            clear_current_member(request)

            save_pending_relationship(
                request,
                {
                    "mode": "subject",
                    "target_texts": target_texts,
                },
            )

            return (
                build_ambiguity_message(
                    first_members,
                    prefix=(
                        f"I found several members "
                        f"matching '{first_text}'. "
                        "Please choose which one you mean."
                    ),
                ),
                first_members,
            )

        member_a = first_members[0]

    else:
        if not current_member:
            return (
                (
                    "I understand that you are asking "
                    "about a relationship, but I need "
                    "the first member's name or Registry ID."
                ),
                [],
            )

        member_a = current_member

    # --------------------------------------------------------
    # TARGETS
    # --------------------------------------------------------

    if not target_texts:
        return (
            (
                "I understand that you are asking "
                "about a relationship, but I need "
                "the other member's name or Registry ID."
            ),
            [],
        )

    targets, ambiguity_members, error = (
        resolve_relationship_targets(
            request,
            member_a,
            target_texts,
        )
    )

    if error:
        return (
            error,
            ambiguity_members,
        )

    clear_pending_relationship(request)

    return finish_relationship(
        request,
        member_a,
        targets,
    )


# ============================================================
# CONTEXTUAL QUESTION
# ============================================================

def resolve_contextual_question(
    request,
    question,
):
    query = normalize(question)

    member, message = (
        resolve_context_member(
            request,
            query,
        )
    )

    if message:
        return (
            message,
            get_result_members(request),
        )

    if not member:
        return (
            (
                "I understand the question, but I "
                "need to know which registered member "
                "you mean. Please give me the member's "
                "name or Registry ID."
            ),
            [],
        )

    answer = answer_member_question(
        member,
        question,
    )

    set_current_member(
        request,
        member,
    )

    save_result_ids(
        request,
        [member],
    )

    save_historian_state(
        request,
        intent="member_followup",
    )

    return answer, [member]


# ============================================================
# MAIN CONVERSATION ENGINE
# ============================================================

def process_historian_question(
    request,
    question,
):
    raw_question = clean_text(
        question
    )

    if not raw_question:
        return (
            "Please enter a question.",
            [],
        )

    query = normalize(
        raw_question
    )

    save_historian_state(
        request,
        query=query,
    )

    # Any normal question starts a fresh relationship context.
    # Numeric/ordinal selection is allowed to continue a
    # pending relationship.
    if not is_pure_result_selection(query):
        clear_pending_relationship(request)

    # --------------------------------------------------------
    # 1. GREETING
    # --------------------------------------------------------

    answer = greeting_answer(query)

    if answer:
        save_historian_state(
            request,
            intent="greeting",
        )

        return answer, []

    # --------------------------------------------------------
    # 2. THANKS
    # --------------------------------------------------------

    answer = thanks_answer(query)

    if answer:
        save_historian_state(
            request,
            intent="thanks",
        )

        return answer, []

    # --------------------------------------------------------
    # 3. HELP
    # --------------------------------------------------------

    answer = help_answer(query)

    if answer:
        save_historian_state(
            request,
            intent="help",
        )

        return answer, []

    # --------------------------------------------------------
    # 4. GLOBAL STATISTICS
    # --------------------------------------------------------

    answer = statistics_answer(query)

    if answer:
        save_historian_state(
            request,
            intent="statistics",
        )

        return answer, []

    # --------------------------------------------------------
    # 5. RELATIONSHIP QUESTIONS
    # --------------------------------------------------------

    relationship_answer, relationship_results = (
        answer_relationship_question(
            request,
            raw_question,
        )
    )

    if relationship_answer:
        return (
            relationship_answer,
            relationship_results,
        )

    # --------------------------------------------------------
    # 6. CONTINUE A PENDING RELATIONSHIP SELECTION
    # --------------------------------------------------------

    if is_pure_result_selection(query):
        pending_result = (
            resume_pending_relationship_selection(
                request,
                query,
            )
        )

        if pending_result:
            return pending_result

    # --------------------------------------------------------
    # 7. EXPLICIT MEMBER SEARCH
    #
    # This happens BEFORE contextual follow-up.
    #
    # Therefore:
    #
    #   "is Osita married?"
    #
    # searches Osita directly even if another member is
    # currently active.
    # --------------------------------------------------------

    members = find_members_mentioned(
        raw_question
    )

    if members:
        if len(members) > 1:
            save_result_ids(
                request,
                members,
            )

            clear_current_member(request)

            save_historian_state(
                request,
                intent="member_search_ambiguous",
            )

            return (
                build_ambiguity_message(
                    members
                ),
                members,
            )

        member = members[0]

        set_current_member(
            request,
            member,
        )

        save_result_ids(
            request,
            [member],
        )

        save_historian_state(
            request,
            intent="member_search",
        )

        if (
            is_member_question_query(query)
            or is_member_attribute_question(query)
            or "about" in query
        ):
            return (
                answer_member_question(
                    member,
                    raw_question,
                ),
                [member],
            )

        return (
            f"I have found {member_name(member)}. "
            "What would you like to know about "
            "this member?",
            [member],
        )

    # --------------------------------------------------------
    # 8. PURE RESULT SELECTION
    #
    # IMPORTANT:
    #
    # "is he married?"
    # "is Osita married?"
    #
    # never reaches this as a selector.
    # --------------------------------------------------------

    if is_result_selection_query(query):
        previous_results = (
            get_result_members(request)
        )

        if previous_results:
            member, message = (
                resolve_from_previous_results(
                    request,
                    query,
                )
            )

            if message:
                return (
                    message,
                    previous_results,
                )

            if member:
                clear_pending_relationship(request)

                answer = build_full_profile_answer(
                    member
                )

                save_historian_state(
                    request,
                    intent="member_selected",
                )

                return answer, [member]

    # --------------------------------------------------------
    # 9. CONTEXTUAL FOLLOW-UPS
    # --------------------------------------------------------

    if is_contextual_followup(query):
        current = get_current_member(
            request
        )

        if current:
            answer, results = (
                resolve_contextual_question(
                    request,
                    raw_question,
                )
            )

            return answer, results

        previous_results = (
            get_result_members(request)
        )

        if len(previous_results) == 1:
            set_current_member(
                request,
                previous_results[0],
            )

            answer, results = (
                resolve_contextual_question(
                    request,
                    raw_question,
                )
            )

            return answer, results

        if len(previous_results) > 1:
            return (
                build_ambiguity_message(
                    previous_results,
                    prefix=(
                        "I still have several matching "
                        "members from the previous search. "
                        "Please choose one before asking "
                        "a follow-up question."
                    ),
                ),
                previous_results,
            )

    # --------------------------------------------------------
    # 10. GLOBAL LIFE EVENT QUESTIONS
    # --------------------------------------------------------

    life_event_answer = (
        answer_life_event_question(
            query
        )
    )

    if life_event_answer:
        save_historian_state(
            request,
            intent="life_event_statistics",
        )

        return life_event_answer, []

    # --------------------------------------------------------
    # 11. FAMILY ROOT QUESTIONS
    # --------------------------------------------------------

    family_result = family_root_answer(
        query
    )

    if family_result:
        if isinstance(
            family_result,
            tuple,
        ):
            answer, members = (
                family_result
            )

            save_result_ids(
                request,
                members,
            )

            clear_current_member(
                request
            )

            save_historian_state(
                request,
                intent="family_root",
            )

            return answer, members

        save_historian_state(
            request,
            intent="family_root",
        )

        return family_result, []

    # --------------------------------------------------------
    # 12. ATTRIBUTE QUESTION WITHOUT A MEMBER
    # --------------------------------------------------------

    if is_member_attribute_question(
        query
    ):
        return (
            "I can answer that, but I need to know "
            "which registered member you mean. "
            "Please give me the member's name or "
            "Registry ID.",
            [],
        )

    # --------------------------------------------------------
    # 13. LAST RESORT
    # --------------------------------------------------------

    return (
        "I could not determine which registry "
        "information you are asking for. "
        "Please provide a member's name or "
        "Registry ID, or ask a question such as "
        "\"what is a member's marital status?\" "
        "or \"how many married members are "
        "registered?\"",
        [],
    )