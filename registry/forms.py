from django import forms
from django.forms import BaseFormSet, formset_factory

from .models import (
    Registry,
    LifeEvent,
    MarriageDetails,
    DivorceDetails,
    NameChangeDetails,
)


# ============================================================
# REGISTRY FORM
# ============================================================

class RegistryForm(forms.ModelForm):
    immediate_father = forms.ModelChoiceField(
        queryset=Registry.objects.none(),
        required=False,
        label="Immediate Father's Name",
        empty_label="Select a registered father",
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    manual_immediate_father = forms.CharField(
        required=False,
        label="Or enter father's name manually",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter father's name if not registered",
            }
        ),
    )
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

            "family_name",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        queryset = Registry.objects.all().order_by(
            "firstname",
            "middlename",
            "surname",
        )

        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        self.fields["immediate_father"].queryset = queryset

        if self.instance and self.instance.immediate_father_id:
            self.fields["immediate_father"].initial = (
                self.instance.immediate_father_id
            )

        if self.instance and self.instance.immediate_fathers_name:
            if not self.instance.immediate_father_id:
                self.fields["manual_immediate_father"].initial = (
                    self.instance.immediate_fathers_name
                )

    def clean(self):
        cleaned_data = super().clean()

        father = cleaned_data.get("immediate_father")
        manual_father = (
            cleaned_data.get("manual_immediate_father") or ""
        ).strip()

        if father and manual_father:
            self.add_error(
                "manual_immediate_father",
                "Select a registered father or enter the father's name manually, not both.",
            )

        if father:
            father_name = " ".join(
                filter(
                    None,
                    [
                        father.firstname,
                        father.middlename,
                        father.surname,
                    ],
                )
            ).strip()

            cleaned_data["resolved_father_name"] = father_name

        elif manual_father:
            cleaned_data["resolved_father_name"] = manual_father

        else:
            cleaned_data["resolved_father_name"] = ""

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        father = self.cleaned_data.get("immediate_father")
        resolved_name = self.cleaned_data.get(
            "resolved_father_name",
            "",
        )

        instance.immediate_father = father
        instance.immediate_fathers_name = resolved_name

        if commit:
            instance.save()

        return instance

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

    event_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        ),
    )

    class Meta:
        model = LifeEvent

        fields = [
            "event_date",
            "event_location",
        ]

        widgets = {
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
            }
        ),
    )

    marriage_date = forms.DateField(
        label="Marriage Date",
        required=False,
        disabled=True,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "readonly": "readonly",
            }
        ),
    )

    class Meta:
        model = DivorceDetails

        fields = [
            "marriage",
            "date_of_divorce",
            "reason",
        ]

        widgets = {
            "marriage": forms.HiddenInput(),

            "date_of_divorce": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Reason for divorce (optional)",
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
                .order_by(
                    "date_of_marriage",
                    "id",
                )
            )

            self.fields["marriage"].queryset = queryset

            # Automatically select the latest undivorced marriage.
            marriage = queryset.order_by(
                "-date_of_marriage",
                "-id",
            ).first()

            if marriage:

                self.initial["marriage"] = marriage.pk

                self.fields["spouse_full_name"].initial = (
                    marriage.spouse_full_name
                )

                self.fields["marriage_date"].initial = (
                    marriage.date_of_marriage
                )

        else:

            self.fields["marriage"].queryset = (
                MarriageDetails.objects.none()
            )

    def clean(self):

        cleaned_data = super().clean()

        marriage = cleaned_data.get("marriage")
        divorce_date = cleaned_data.get("date_of_divorce")

        if marriage:

            self.cleaned_spouse_full_name = (
                marriage.spouse_full_name
            )

            if divorce_date:

                if divorce_date < marriage.date_of_marriage:
                    self.add_error(
                        "date_of_divorce",
                        "Divorce date cannot be earlier "
                        "than the marriage date.",
                    )

                if (
                    marriage.member.date_of_birth
                    and divorce_date
                    < marriage.member.date_of_birth
                ):
                    self.add_error(
                        "date_of_divorce",
                        "Divorce date cannot be earlier "
                        "than the member's date of birth.",
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

# ============================================================
# NAME CHANGE DETAILS FORM
# ============================================================

class NameChangeDetailsForm(forms.ModelForm):

    previous_name = forms.CharField(
        label="Previous Name",
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
            }
        ),
    )

    class Meta:
        model = NameChangeDetails

        fields = [
            "previous_name",
            "current_name",
        ]

        widgets = {
            "current_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter current name",
                }
            ),
        }

    def __init__(self, *args, member=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.member = member

        if member is not None:

            actual_name = " ".join(
                filter(
                    None,
                    [
                        member.firstname,
                        member.middlename,
                        member.surname,
                    ],
                )
            ).strip()

            self.fields["previous_name"].initial = (
                actual_name
            )

    def clean(self):

        cleaned_data = super().clean()

        previous_name = (
            cleaned_data.get("previous_name") or ""
        ).strip()

        current_name = (
            cleaned_data.get("current_name") or ""
        ).strip()

        if (
            previous_name
            and current_name
            and previous_name.lower()
            == current_name.lower()
        ):

            self.add_error(
                "current_name",
                "Current name must be different "
                "from the previous name.",
            )

        return cleaned_data