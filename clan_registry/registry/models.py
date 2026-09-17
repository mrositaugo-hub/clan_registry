from django.db import models
from django.core.validators import RegexValidator


phone_validator = RegexValidator(
    regex=r"^(?:0\d{10}|\+234\d{10})$",
    message="Enter a valid Nigerian phone number, e.g. 08012345678 or +2348012345678.",
)


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

    aut_id = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        blank=True,
    )

    aut_reg_date = models.DateTimeField(
        auto_now_add=True
    )

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

    def save(self, *args, **kwargs):

        if not self.aut_id:

            last_record = Registry.objects.order_by("-id").first()

            if last_record:
                next_number = last_record.id + 1
            else:
                next_number = 1

            self.aut_id = f"UM_{next_number:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aut_id} - {self.surname} {self.firstname}"

    class Meta:
        ordering = ["-aut_reg_date"]
        verbose_name = "Registry Record"
        verbose_name_plural = "Registry Records"


class LifeEvent(models.Model):

    EVENT_TYPE_CHOICES = [
        ("MARRIAGE", "Marriage"),
        ("DIVORCE", "Divorce"),
        ("DEATH", "Death"),
    ]

    member = models.ForeignKey(
        Registry,
        on_delete=models.CASCADE,
        related_name="life_events",
    )

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
    )

    event_date = models.DateField()

    event_location = models.CharField(
        max_length=200,
        blank=True,
    )

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.member}"

    class Meta:
        ordering = ["-event_date"]
        verbose_name = "Life Event"
        verbose_name_plural = "Life Events"


class MarriageDetails(models.Model):

    life_event = models.OneToOneField(
        LifeEvent,
        on_delete=models.CASCADE,
        related_name="marriage_details",
    )

    spouse_full_name = models.CharField(
        max_length=200,
    )

    date_of_marriage = models.DateField()

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

    def __str__(self):
        return f"Marriage details - {self.life_event.member}"

    class Meta:
        verbose_name = "Marriage Detail"
        verbose_name_plural = "Marriage Details"


class DivorceDetails(models.Model):

    life_event = models.OneToOneField(
        LifeEvent,
        on_delete=models.CASCADE,
        related_name="divorce_details",
    )

    spouse_full_name = models.CharField(
        max_length=200,
    )

    date_of_divorce = models.DateField()

    def __str__(self):
        return f"Divorce details - {self.life_event.member}"

    class Meta:
        verbose_name = "Divorce Detail"
        verbose_name_plural = "Divorce Details"