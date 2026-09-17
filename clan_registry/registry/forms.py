from django import forms

from .models import (
    Registry,
    LifeEvent,
    MarriageDetails,
    DivorceDetails,
)


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
            "spouse_full_name",
            "date_of_marriage",
            "spouse_clan",
            "spouse_village",
            "spouse_state",
            "spouse_country",
            "date_of_divorce",

            "academic_qualification",
            "area_of_profession",
            "occupation",
        ]

        widgets = {
            "phone_number": forms.TextInput(
                attrs={
                    "type": "tel",
                    "inputmode": "numeric",
                    "autocomplete": "tel",
                    "placeholder": "08012345678",
                }
            ),

            "date_of_birth": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),

            "date_of_marriage": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),

            "date_of_divorce": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),
        }

    def clean_phone_number(self):

        phone = self.cleaned_data.get(
            "phone_number",
            ""
        ).strip()

        if phone:

            phone = phone.replace(
                " ",
                ""
            ).replace(
                "-",
                ""
            )

            if phone.startswith("0") and len(phone) == 11:
                return phone

            if phone.startswith("+234") and len(phone) == 14:
                return phone

            raise forms.ValidationError(
                "Enter a valid Nigerian phone number, e.g. 08012345678 or +2348012345678."
            )

        return phone


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


class DivorceDetailsForm(forms.ModelForm):

    class Meta:
        model = DivorceDetails

        fields = [
            "spouse_full_name",
            "date_of_divorce",
        ]

        widgets = {
            "spouse_full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter spouse full name",
                }
            ),

            "date_of_divorce": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
        }