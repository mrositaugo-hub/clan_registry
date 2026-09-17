from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


# ============================================================
# PHONE NUMBER VALIDATOR
# ============================================================

phone_validator = RegexValidator(
    regex=r"^\+?[0-9]+$",
    message=(
        "Enter a valid phone number using digits, "
        "with an optional + at the beginning."
    ),
)


# ============================================================
# REGISTRY
# ============================================================

class Registry(models.Model):

    ROOT_FAMILY_CHOICES = [
        ("UMUNANGWU", "Umunangwu"),
        ("UMUGBANOKE", "Umugbanoke"),
        ("UMUCHUKWU", "Umuchukwu"),
    ]

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("SINGLE", "Single"),
        ("MARRIED", "Married"),
        ("DIVORCED", "Divorced"),
    ]

    # ========================================================
    # SYSTEM IDENTIFICATION
    # ========================================================

    aut_id = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        blank=True,
    )

    aut_reg_date = models.DateTimeField(
        auto_now_add=True,
    )

    # ========================================================
    # PERSONAL INFORMATION
    # ========================================================

    family_root = models.CharField(
        max_length=30,
        choices=ROOT_FAMILY_CHOICES,
    )

    title = models.CharField(
        max_length=50,
        blank=True,
    )

    surname = models.CharField(
        max_length=100,
    )

    firstname = models.CharField(
        max_length=100,
    )

    middlename = models.CharField(
        max_length=100,
        blank=True,
    )

    nickname = models.CharField(
        max_length=100,
        blank=True,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator],
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
    )

    place_of_birth = models.CharField(
        max_length=200,
        blank=True,
    )

    # ========================================================
    # FAMILY / LINEAGE INFORMATION
    # ========================================================

    family_lineage = models.CharField(
        max_length=200,
        blank=True,
    )

    family_name = models.CharField(
        max_length=200,
        blank=True,
    )

    immediate_fathers_name = models.CharField(
        max_length=200,
        blank=True,
    )

    mother_name = models.CharField(
        max_length=200,
        blank=True,
    )

    mother_clan = models.CharField(
        max_length=200,
        blank=True,
    )

    mother_village = models.CharField(
        max_length=200,
        blank=True,
    )

    mother_state = models.CharField(
        max_length=200,
        blank=True,
    )

    mother_country = models.CharField(
        max_length=200,
        blank=True,
    )

    # ========================================================
    # CURRENT MARITAL INFORMATION
    # ========================================================

    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
    )

    spouse_full_name = models.CharField(
        max_length=200,
        blank=True,
    )

    date_of_marriage = models.DateField(
        null=True,
        blank=True,
    )

    spouse_clan = models.CharField(
        max_length=200,
        blank=True,
    )

    spouse_village = models.CharField(
        max_length=200,
        blank=True,
    )

    spouse_state = models.CharField(
        max_length=200,
        blank=True,
    )

    spouse_country = models.CharField(
        max_length=200,
        blank=True,
    )

    date_of_divorce = models.DateField(
        null=True,
        blank=True,
    )

    # ========================================================
    # EDUCATION / PROFESSION
    # ========================================================

    academic_qualification = models.CharField(
        max_length=200,
        blank=True,
    )

    area_of_profession = models.CharField(
        max_length=200,
        blank=True,
    )

    occupation = models.CharField(
        max_length=200,
        blank=True,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):
        """
        Validate Registry-level information only.

        Historical marriage/divorce chronology belongs to the
        LifeEvent, MarriageDetails and DivorceDetails models.
        """

        errors = {}

        # ----------------------------------------------------
        # DATE OF BIRTH CANNOT BE IN THE FUTURE
        # ----------------------------------------------------

        from django.utils import timezone

        if self.date_of_birth:

            if self.date_of_birth > timezone.localdate():

                errors["date_of_birth"] = (
                    "Date of birth cannot be in the future."
                )

        # ----------------------------------------------------
        # RETURN VALIDATION ERRORS
        # ----------------------------------------------------

        if errors:
            raise ValidationError(errors)

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, *args, **kwargs):

        # ----------------------------------------------------
        # GENERATE PERMANENT REGISTRY ID
        # ----------------------------------------------------

        if not self.aut_id:

            last_record = (
                Registry.objects
                .order_by("-id")
                .first()
            )

            if last_record:

                next_number = last_record.id + 1

            else:

                next_number = 1

            self.aut_id = f"UM_{next_number:06d}"

        # ----------------------------------------------------
        # VALIDATE BEFORE DATABASE SAVE
        # ----------------------------------------------------

        self.full_clean()

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        super().save(*args, **kwargs)

    # ========================================================
    # STRING REPRESENTATION
    # ========================================================

    def __str__(self):

        return (
            f"{self.aut_id} - "
            f"{self.surname} "
            f"{self.firstname}"
        )

    # ========================================================
    # META
    # ========================================================

    class Meta:

        ordering = ["-aut_reg_date"]

        verbose_name = "Registry Record"

        verbose_name_plural = "Registry Records"


# ============================================================
# LIFE EVENTS
# ============================================================

class LifeEvent(models.Model):

    EVENT_TYPE_CHOICES = [
        ("MARRIAGE", "Marriage"),
        ("DIVORCE", "Divorce"),
        ("DEATH", "Death"),
        ("NAME_CHANGE", "Name Change"),
        ("MIGRATION", "Migration"),
    ]

    # ========================================================
    # MEMBER
    # ========================================================

    member = models.ForeignKey(
        Registry,
        on_delete=models.CASCADE,
        related_name="life_events",
    )

    # ========================================================
    # EVENT TYPE
    # ========================================================

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
    )

    # ========================================================
    # EVENT DATE
    # ========================================================

    event_date = models.DateField()

    # ========================================================
    # EVENT LOCATION
    # ========================================================

    event_location = models.CharField(
        max_length=200,
        blank=True,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        errors = {}

        # ----------------------------------------------------
        # MEMBER REQUIRED
        # ----------------------------------------------------

        if not self.member_id:

            errors["member"] = (
                "A life event must belong to a registry member."
            )

        # ----------------------------------------------------
        # EVENT DATE REQUIRED
        # ----------------------------------------------------

        if not self.event_date:

            errors["event_date"] = (
                "An event date is required."
            )

        # ----------------------------------------------------
        # CHRONOLOGICAL VALIDATION
        #
        # This deliberately checks BOTH directions:
        #
        # 1. A new event cannot occur after death.
        # 2. A new death cannot occur before an existing event.
        #
        # This prevents the exact problem:
        #
        # Death   -> 24 May 1996
        # Marriage -> 24 Apr 2005
        #
        # regardless of which record was entered first.
        # ----------------------------------------------------

        if self.member_id and self.event_date:

            member = self.member

            # ------------------------------------------------
            # EVENT CANNOT OCCUR BEFORE BIRTH
            # ------------------------------------------------

            if (
                member.date_of_birth
                and self.event_date < member.date_of_birth
            ):

                errors["event_date"] = (
                    "Life event date cannot be earlier than "
                    "the member's date of birth."
                )

            # ------------------------------------------------
            # FIND EXISTING DEATH
            # ------------------------------------------------

            death_event = (
                LifeEvent.objects
                .filter(
                    member=member,
                    event_type="DEATH",
                )
                .exclude(pk=self.pk)
                .order_by("event_date")
                .first()
            )

            # ------------------------------------------------
            # ANY NON-DEATH EVENT CANNOT OCCUR AFTER DEATH
            # ------------------------------------------------

            if (
                self.event_type != "DEATH"
                and death_event
                and self.event_date > death_event.event_date
            ):

                errors["event_date"] = (
                    "This life event cannot occur after "
                    "the member's recorded death date."
                )

            # ------------------------------------------------
            # A NEW DEATH CANNOT BE EARLIER THAN AN EXISTING
            # LIFE EVENT
            #
            # This is the reverse-direction check that was
            # missing before.
            # ------------------------------------------------

            if self.event_type == "DEATH":

                later_event = (
                    LifeEvent.objects
                    .filter(
                        member=member,
                        event_date__gt=self.event_date,
                    )
                    .exclude(pk=self.pk)
                    .order_by("event_date")
                    .first()
                )

                if later_event:

                    errors["event_date"] = (
                        "The death date cannot be earlier than "
                        "an already recorded life event. "
                        f"The {later_event.get_event_type_display().lower()} "
                        f"event is dated "
                        f"{later_event.event_date:%d %b %Y}."
                    )

            # ------------------------------------------------
            # ONLY ONE DEATH
            # ------------------------------------------------

            if self.event_type == "DEATH":

                existing_death = (
                    LifeEvent.objects
                    .filter(
                        member=member,
                        event_type="DEATH",
                    )
                    .exclude(pk=self.pk)
                    .first()
                )

                if existing_death:

                    errors["event_type"] = (
                        "This member already has a recorded "
                        "death event."
                    )

        # ----------------------------------------------------
        # EVENT-SPECIFIC VALIDATION
        # ----------------------------------------------------

        if self.event_type == "DEATH":

            errors.update(
                self._validate_death()
            )

        elif self.event_type == "MARRIAGE":

            errors.update(
                self._validate_marriage()
            )

        elif self.event_type == "DIVORCE":

            errors.update(
                self._validate_divorce()
            )

        # ----------------------------------------------------
        # RETURN ERRORS
        # ----------------------------------------------------

        if errors:

            raise ValidationError(errors)

    # ========================================================
    # DEATH VALIDATION
    # ========================================================

    def _validate_death(self):

        errors = {}

        if self.member_id and self.event_date:

            member = self.member

            # ------------------------------------------------
            # DEATH CANNOT BE BEFORE BIRTH
            # ------------------------------------------------

            if (
                member.date_of_birth
                and self.event_date < member.date_of_birth
            ):

                errors["event_date"] = (
                    "Death date cannot be earlier than "
                    "the member's date of birth."
                )

            # ------------------------------------------------
            # ONLY ONE DEATH
            # ------------------------------------------------

            existing_death = (
                LifeEvent.objects
                .filter(
                    member=member,
                    event_type="DEATH",
                )
                .exclude(pk=self.pk)
                .first()
            )

            if existing_death:

                errors["event_type"] = (
                    "This member already has a recorded "
                    "death event."
                )

        return errors

    # ========================================================
    # MARRIAGE VALIDATION
    # ========================================================

    def _validate_marriage(self):

        errors = {}

        if self.member_id and self.event_date:

            member = self.member

            # ------------------------------------------------
            # MARRIAGE CANNOT BE BEFORE BIRTH
            # ------------------------------------------------

            if (
                member.date_of_birth
                and self.event_date < member.date_of_birth
            ):

                errors["event_date"] = (
                    "Marriage date cannot be earlier than "
                    "the member's date of birth."
                )

            # ------------------------------------------------
            # MARRIAGE CANNOT BE AFTER DEATH
            # ------------------------------------------------

            death_event = (
                LifeEvent.objects
                .filter(
                    member=member,
                    event_type="DEATH",
                )
                .exclude(pk=self.pk)
                .order_by("event_date")
                .first()
            )

            if (
                death_event
                and self.event_date > death_event.event_date
            ):

                errors["event_date"] = (
                    "Marriage cannot occur after "
                    "the member's death date."
                )

        return errors

    # ========================================================
    # DIVORCE VALIDATION
    # ========================================================

    def _validate_divorce(self):

        errors = {}

        if self.member_id and self.event_date:

            member = self.member

            # ------------------------------------------------
            # DIVORCE CANNOT BE BEFORE BIRTH
            # ------------------------------------------------

            if (
                member.date_of_birth
                and self.event_date < member.date_of_birth
            ):

                errors["event_date"] = (
                    "Divorce date cannot be earlier than "
                    "the member's date of birth."
                )

            # ------------------------------------------------
            # DIVORCE CANNOT BE AFTER DEATH
            # ------------------------------------------------

            death_event = (
                LifeEvent.objects
                .filter(
                    member=member,
                    event_type="DEATH",
                )
                .exclude(pk=self.pk)
                .order_by("event_date")
                .first()
            )

            if (
                death_event
                and self.event_date > death_event.event_date
            ):

                errors["event_date"] = (
                    "Divorce cannot occur after "
                    "the member's death date."
                )

        return errors

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    # ========================================================
    # STRING REPRESENTATION
    # ========================================================

    def __str__(self):

        return (
            f"{self.get_event_type_display()} - "
            f"{self.member}"
        )

    # ========================================================
    # META
    # ========================================================

    class Meta:

        ordering = ["-event_date"]

        verbose_name = "Life Event"

        verbose_name_plural = "Life Events"


# ============================================================
# MARRIAGE DETAILS
# ============================================================

class MarriageDetails(models.Model):

    """
    Represents one specific marriage belonging to a registry
    member.

    A member can have multiple MarriageDetails records.

    This supports:
        - Multiple historical marriages
        - Multiple spouses
        - Polygamous marriage structures
        - Historical marriage records
    """

    # ========================================================
    # MEMBER
    # ========================================================

    member = models.ForeignKey(
        Registry,
        on_delete=models.CASCADE,
        related_name="marriages",
    )

    # ========================================================
    # LINKED LIFE EVENT
    # ========================================================

    life_event = models.OneToOneField(
        LifeEvent,
        on_delete=models.CASCADE,
        related_name="marriage_details",
    )

    # ========================================================
    # SPOUSE
    # ========================================================

    spouse_full_name = models.CharField(
        max_length=200,
    )

    # ========================================================
    # MARRIAGE DATE
    # ========================================================

    date_of_marriage = models.DateField()

    # ========================================================
    # SPOUSE LOCATION / ORIGIN
    # ========================================================

    spouse_clan = models.CharField(
        max_length=200,
        blank=True,
    )

    spouse_village = models.CharField(
        max_length=200,
        blank=True,
    )

    spouse_state = models.CharField(
        max_length=200,
        blank=True,
    )

    spouse_country = models.CharField(
        max_length=200,
        blank=True,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        errors = {}

        # ----------------------------------------------------
        # LIFE EVENT MUST EXIST
        # ----------------------------------------------------

        if self.life_event_id:

            if self.life_event.event_type != "MARRIAGE":

                errors["life_event"] = (
                    "Marriage details must be connected "
                    "to a Marriage life event."
                )

        # ----------------------------------------------------
        # MEMBER MUST MATCH LIFE EVENT MEMBER
        # ----------------------------------------------------

        if self.member_id and self.life_event_id:

            if (
                self.life_event.member_id
                != self.member_id
            ):

                errors["member"] = (
                    "The marriage member must match "
                    "the member attached to the life event."
                )

        # ----------------------------------------------------
        # MARRIAGE DATE MUST MATCH LIFE EVENT DATE
        # ----------------------------------------------------

        if self.life_event_id:

            if (
                self.date_of_marriage
                and self.life_event.event_date
                and (
                    self.date_of_marriage
                    != self.life_event.event_date
                )
            ):

                errors["date_of_marriage"] = (
                    "The marriage date must match "
                    "the date recorded for the "
                    "marriage life event."
                )

        # ----------------------------------------------------
        # MARRIAGE CANNOT BE BEFORE BIRTH
        # ----------------------------------------------------

        if (
            self.member_id
            and self.date_of_marriage
            and self.member.date_of_birth
            and (
                self.date_of_marriage
                < self.member.date_of_birth
            )
        ):

            errors["date_of_marriage"] = (
                "Marriage date cannot be earlier than "
                "the member's date of birth."
            )

        # ----------------------------------------------------
        # MARRIAGE CANNOT BE AFTER DEATH
        # ----------------------------------------------------

        if self.member_id and self.date_of_marriage:

            death_event = (
                LifeEvent.objects
                .filter(
                    member=self.member,
                    event_type="DEATH",
                )
                .order_by("event_date")
                .first()
            )

            if (
                death_event
                and self.date_of_marriage
                > death_event.event_date
            ):

                errors["date_of_marriage"] = (
                    "Marriage cannot occur after "
                    "the member's death date."
                )

        # ----------------------------------------------------
        # RETURN ERRORS
        # ----------------------------------------------------

        if errors:

            raise ValidationError(errors)

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    # ========================================================
    # STRING REPRESENTATION
    # ========================================================

    def __str__(self):

        return (
            f"Marriage - "
            f"{self.member} - "
            f"{self.spouse_full_name}"
        )

    # ========================================================
    # META
    # ========================================================

    class Meta:

        ordering = ["date_of_marriage"]

        verbose_name = "Marriage Detail"

        verbose_name_plural = "Marriage Details"


# ============================================================
# DIVORCE DETAILS
# ============================================================

class DivorceDetails(models.Model):

    """
    Represents the dissolution of one specific marriage.

    The spouse's name is NOT duplicated here.

    Relationship:

        DivorceDetails
            |
            -> MarriageDetails
                    |
                    -> spouse_full_name

    One MarriageDetails record can have at most one divorce.
    """

    # ========================================================
    # MARRIAGE BEING DISSOLVED
    # ========================================================

    marriage = models.OneToOneField(
        MarriageDetails,
        on_delete=models.CASCADE,
        related_name="divorce",
    )

    # ========================================================
    # DIVORCE LIFE EVENT
    # ========================================================

    life_event = models.OneToOneField(
        LifeEvent,
        on_delete=models.CASCADE,
        related_name="divorce_details",
    )

    # ========================================================
    # DIVORCE DATE
    # ========================================================

    date_of_divorce = models.DateField()

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        errors = {}

        # ----------------------------------------------------
        # DIVORCE LIFE EVENT MUST BE DIVORCE
        # ----------------------------------------------------

        if self.life_event_id:

            if self.life_event.event_type != "DIVORCE":

                errors["life_event"] = (
                    "Divorce details must be connected "
                    "to a Divorce life event."
                )

        # ----------------------------------------------------
        # MARRIAGE RELATIONSHIP
        # ----------------------------------------------------

        if self.marriage_id:

            marriage = self.marriage

            # ------------------------------------------------
            # DIVORCE EVENT MUST BELONG TO SAME MEMBER
            # ------------------------------------------------

            if self.life_event_id:

                if (
                    self.life_event.member_id
                    != marriage.member_id
                ):

                    errors["life_event"] = (
                        "The divorce and marriage must belong "
                        "to the same registry member."
                    )

            # ------------------------------------------------
            # DIVORCE DATE MUST MATCH LIFE EVENT DATE
            # ------------------------------------------------

            if self.life_event_id:

                if (
                    self.date_of_divorce
                    and self.life_event.event_date
                    and (
                        self.date_of_divorce
                        != self.life_event.event_date
                    )
                ):

                    errors["date_of_divorce"] = (
                        "The divorce date must match "
                        "the date recorded for the "
                        "divorce life event."
                    )

            # ------------------------------------------------
            # DIVORCE CANNOT BE BEFORE MARRIAGE
            # ------------------------------------------------

            if (
                self.date_of_divorce
                and marriage.date_of_marriage
                and (
                    self.date_of_divorce
                    < marriage.date_of_marriage
                )
            ):

                errors["date_of_divorce"] = (
                    "Divorce date cannot be earlier than "
                    "the marriage date."
                )

            # ------------------------------------------------
            # DIVORCE CANNOT BE BEFORE BIRTH
            # ------------------------------------------------

            if (
                marriage.member.date_of_birth
                and self.date_of_divorce
                and (
                    self.date_of_divorce
                    < marriage.member.date_of_birth
                )
            ):

                errors["date_of_divorce"] = (
                    "Divorce date cannot be earlier than "
                    "the member's date of birth."
                )

            # ------------------------------------------------
            # DIVORCE CANNOT BE AFTER DEATH
            # ------------------------------------------------

            death_event = (
                LifeEvent.objects
                .filter(
                    member=marriage.member,
                    event_type="DEATH",
                )
                .order_by("event_date")
                .first()
            )

            if (
                death_event
                and self.date_of_divorce
                and (
                    self.date_of_divorce
                    > death_event.event_date
                )
            ):

                errors["date_of_divorce"] = (
                    "Divorce cannot occur after "
                    "the member's death date."
                )

        # ----------------------------------------------------
        # MARRIAGE REQUIRED
        # ----------------------------------------------------

        if not self.marriage_id:

            errors["marriage"] = (
                "A divorce must be connected "
                "to a specific marriage."
            )

        # ----------------------------------------------------
        # LIFE EVENT REQUIRED
        # ----------------------------------------------------

        if not self.life_event_id:

            errors["life_event"] = (
                "A divorce must be connected "
                "to a Divorce life event."
            )

        # ----------------------------------------------------
        # RETURN ERRORS
        # ----------------------------------------------------

        if errors:

            raise ValidationError(errors)

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    # ========================================================
    # STRING REPRESENTATION
    # ========================================================

    def __str__(self):

        return (
            f"Divorce - "
            f"{self.marriage.member} - "
            f"{self.marriage.spouse_full_name}"
        )

    # ========================================================
    # META
    # ========================================================

    class Meta:

        ordering = ["-date_of_divorce"]

        verbose_name = "Divorce Detail"

        verbose_name_plural = "Divorce Details"