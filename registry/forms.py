from django import forms
from django.forms import BaseFormSet, formset_factory

from .models import (
    Registry,
    LifeEvent,
    MarriageDetails,
    DivorceDetails,
)


# ============================================================
# REGISTRY FORM
# ============================================================

class RegistryForm(forms.ModelForm):

    class Meta:
        model = Registry

        fields = [
            "family_root",
            "title",
            "surname",
            "firstname",
            "middlename",
            "nickname",
            "phone_number",
            "gender",
            "date_of_birth",
            "place_of_birth",

            "family_lineage",
            "family_name",
            "immediate_fathers_name",
            "mother_name",
            "mother_clan",
            "mother_village",
            "mother_state",
            "mother_country",

            "marital_status",

            "academic_qualification",
            "area_of_profession",
            "occupation",
        ]

        widgets = {
            # ====================================================
            # DATE OF BIRTH
            # Same native date input as Date of Marriage
            # ====================================================
            "date_of_birth": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            # ====================================================
            # PHONE NUMBER
            # ====================================================
            "phone_number": forms.TextInput(
                attrs={
                    "type": "tel",
                    "inputmode": "tel",
                    "autocomplete": "tel",
                    "placeholder": "e.g. 08123456789 or +2348123456789",
                    "maxlength": "14",
                }
            ),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number", "").strip()

        # Phone number is optional.
        if not phone:
            return phone

        # Remove common formatting characters.
        phone = (
            phone
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )

        # Maximum allowed length.
        if len(phone) > 14:
            raise forms.ValidationError(
                "Phone number cannot be more than 14 characters."
            )

        # Allow only digits, with an optional + at the beginning.
        if phone.startswith("+"):
            if not phone[1:].isdigit():
                raise forms.ValidationError(
                    "Enter a valid phone number using digits only."
                )
        else:
            if not phone.isdigit():
                raise forms.ValidationError(
                    "Enter a valid phone number using digits only."
                )

        return phone


# ============================================================
# LIFE EVENT FORM
# ============================================================

class LifeEventForm(forms.ModelForm):

    class Meta:
        model = LifeEvent

        fields = [
            "event_date",
            "event_location",
        ]

        widgets = {
            "event_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "event_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter event location",
                }
            ),
        }


# ============================================================
# MARRIAGE DETAILS FORM
# ============================================================

class MarriageDetailsForm(forms.ModelForm):

    class Meta:
        model = MarriageDetails

        fields = [
            "spouse_full_name",
            "date_of_marriage",
            "spouse_clan",
            "spouse_village",
            "spouse_state",
            "spouse_country",
        ]

        widgets = {
            "spouse_full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter spouse full name",
                }
            ),

            # Same date input configuration as Date of Birth.
            "date_of_marriage": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "spouse_clan": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter spouse clan",
                }
            ),

            "spouse_village": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter spouse village",
                }
            ),

            "spouse_state": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter spouse state",
                }
            ),

            "spouse_country": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter spouse country",
                }
            ),
        }

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.member = member

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data:
            return cleaned_data

        spouse_name = cleaned_data.get("spouse_full_name")
        marriage_date = cleaned_data.get("date_of_marriage")

        if not spouse_name:
            return cleaned_data

        if self.member and marriage_date:

            if (
                self.member.date_of_birth
                and marriage_date < self.member.date_of_birth
            ):
                self.add_error(
                    "date_of_marriage",
                    "Marriage date cannot be earlier than "
                    "the member's date of birth.",
                )

        return cleaned_data


# ============================================================
# MARRIAGE FORMSET
# ============================================================

class BaseMarriageDetailsFormSet(BaseFormSet):

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        marriage_dates = set()
        spouse_names = set()

        for form in self.forms:

            if not form.cleaned_data:
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            spouse_name = (
                form.cleaned_data.get("spouse_full_name") or ""
            ).strip()

            marriage_date = form.cleaned_data.get(
                "date_of_marriage"
            )

            # Completely empty marriage row is allowed.
            if not spouse_name and not marriage_date:
                continue

            # A used marriage row must contain spouse name.
            if not spouse_name:
                form.add_error(
                    "spouse_full_name",
                    "Enter the spouse's full name.",
                )

            # A used marriage row must contain marriage date.
            if not marriage_date:
                form.add_error(
                    "date_of_marriage",
                    "Enter the marriage date.",
                )

            # Prevent duplicate marriage dates.
            if marriage_date:

                if marriage_date in marriage_dates:
                    form.add_error(
                        "date_of_marriage",
                        "The same marriage date has been entered "
                        "more than once.",
                    )

                marriage_dates.add(marriage_date)

            # Prevent duplicate spouse names.
            normalized_name = spouse_name.casefold()

            if normalized_name:

                if normalized_name in spouse_names:
                    form.add_error(
                        "spouse_full_name",
                        "The same spouse name has been entered "
                        "more than once.",
                    )

                spouse_names.add(normalized_name)


MarriageDetailsFormSet = formset_factory(
    MarriageDetailsForm,
    formset=BaseMarriageDetailsFormSet,
    extra=1,
    can_delete=True,
)


# ============================================================
# DIVORCE DETAILS FORM
# ============================================================

class DivorceDetailsForm(forms.ModelForm):

    spouse_full_name = forms.CharField(
        label="Spouse Full Name",
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
                "placeholder": "Spouse name will appear automatically",
            }
        ),
    )

    class Meta:
        model = DivorceDetails

        fields = [
            "marriage",
            "date_of_divorce",
        ]

        widgets = {
            "marriage": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "date_of_divorce": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.member = member

        if member is not None:
            queryset = (
                MarriageDetails.objects
                .filter(
                    member=member,
                    divorce__isnull=True,
                )
                .select_related("member")
                .order_by("date_of_marriage", "id")
            )

            self.fields["marriage"].queryset = queryset

            # ------------------------------------------------
            # Automatically select the marriage when there is
            # exactly one eligible marriage.
            # ------------------------------------------------
            if queryset.count() == 1:
                marriage = queryset.first()

                if marriage:
                    self.initial["marriage"] = marriage.pk
                    self.initial["spouse_full_name"] = (
                        marriage.spouse_full_name
                    )

            # ------------------------------------------------
            # Add spouse information to each dropdown option.
            # JavaScript uses this to update the read-only
            # spouse name field when the user changes marriage.
            # ------------------------------------------------
            for option in self.fields["marriage"].choices:
                pass

            self.fields["marriage"].label_from_instance = (
                self.marriage_label
            )

        else:
            self.fields["marriage"].queryset = (
                MarriageDetails.objects.none()
            )

            self.fields["marriage"].label_from_instance = (
                self.marriage_label
            )

    @staticmethod
    def marriage_label(marriage):
        return (
            f"{marriage.spouse_full_name} "
            f"(married {marriage.date_of_marriage:%d %b %Y})"
        )

    def clean(self):
        cleaned_data = super().clean()

        marriage = cleaned_data.get("marriage")
        divorce_date = cleaned_data.get("date_of_divorce")

        # ----------------------------------------------------
        # Never trust the displayed spouse name.
        # The selected MarriageDetails record is the
        # authoritative source.
        # ----------------------------------------------------
        if marriage:
            self.cleaned_spouse_full_name = (
                marriage.spouse_full_name
            )

        if marriage and divorce_date:

            if divorce_date < marriage.date_of_marriage:
                self.add_error(
                    "date_of_divorce",
                    "Divorce date cannot be earlier than "
                    "the marriage date.",
                )

            if (
                marriage.member.date_of_birth
                and divorce_date < marriage.member.date_of_birth
            ):
                self.add_error(
                    "date_of_divorce",
                    "Divorce date cannot be earlier than "
                    "the member's date of birth.",
                )

        return cleaned_data


# ============================================================
# INITIAL REGISTRATION DIVORCE FORM
# ============================================================

class InitialDivorceForm(forms.Form):

    marriage_index = forms.IntegerField(
        min_value=0,
        widget=forms.HiddenInput(),
    )

    # A divorce date is optional on each individual marriage row.
    # This allows some marriages to remain without a divorce date.
    date_of_divorce = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        ),
    )

    def __init__(
        self,
        *args,
        marriage_date=None,
        date_of_birth=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.marriage_date = marriage_date
        self.date_of_birth = date_of_birth

    def clean_date_of_divorce(self):

        divorce_date = self.cleaned_data.get(
            "date_of_divorce"
        )

        # Blank divorce date is allowed.
        if not divorce_date:
            return divorce_date

        # Divorce cannot happen before marriage.
        if (
            self.marriage_date
            and divorce_date < self.marriage_date
        ):

            raise forms.ValidationError(
                "Divorce date cannot be earlier than "
                "the marriage date."
            )

        # Divorce cannot happen before birth.
        if (
            self.date_of_birth
            and divorce_date < self.date_of_birth
        ):

            raise forms.ValidationError(
                "Divorce date cannot be earlier than "
                "the member's date of birth."
            )

        return divorce_date


# ============================================================
# INITIAL DIVORCE FORMSET
# ============================================================

class BaseInitialDivorceFormSet(BaseFormSet):

    def clean(self):

        super().clean()

        if any(self.errors):
            return

        selected_marriages = set()

        for form in self.forms:

            if not form.cleaned_data:
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            marriage_index = form.cleaned_data.get(
                "marriage_index"
            )

            if marriage_index is None:
                continue

            # The same marriage cannot be divorced twice.
            if marriage_index in selected_marriages:

                form.add_error(
                    "marriage_index",
                    (
                        "This marriage has already been "
                        "selected for divorce."
                    ),
                )

            selected_marriages.add(marriage_index)


InitialDivorceFormSet = formset_factory(
    InitialDivorceForm,
    formset=BaseInitialDivorceFormSet,
    extra=0,
    can_delete=True,
)