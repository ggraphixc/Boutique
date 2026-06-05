from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.signing import Signer
import json
import uuid


class MeasurementVault(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(null=True, blank=True)
    session_key = models.CharField(max_length=40, unique=True, null=True, blank=True)
    display_unit = models.CharField(
        max_length=2,
        default="cm",
        choices=[("cm", "cm"), ("in", "in")],
    )
    chest = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(50.0), MaxValueValidator(200.0)],
    )
    waist = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(40.0), MaxValueValidator(180.0)],
    )
    hips = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(60.0), MaxValueValidator(220.0)],
    )
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(100.0), MaxValueValidator(250.0)],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asiko_measurement_vault"

    def __str__(self):
        key = self.session_key or f"user:{self.user_id}"
        return f"Measurements({key}) [{self.display_unit}]"


class AllocationWindow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_product_id = models.UUIDField(unique=True)
    tier_level_required = models.IntegerField(default=1)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    max_allocation_units = models.PositiveIntegerField()
    allocated_units = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "asiko_allocation_windows"

    def __str__(self):
        return f"AllocationWindow({self.target_product_id}) tier={self.tier_level_required}"

    @property
    def is_active(self):
        now = timezone.now()
        return (
            self.start_time <= now <= self.end_time
            and self.allocated_units < self.max_allocation_units
        )

    @property
    def spots_remaining(self):
        return max(0, self.max_allocation_units - self.allocated_units)


def generate_signed_concierge_payload(
    cart_id: str, line_items_summary: list, total_price: int
) -> str:
    """Generate a tamper-proof signed token for the WhatsApp concierge bridge."""
    signer = Signer(salt="asiko.concierge.vector")
    payload = {
        "cart_id": cart_id,
        "items": line_items_summary,
        "total": total_price,
    }
    return signer.sign(json.dumps(payload))


def verify_signed_concierge_payload(token: str) -> dict:
    """Verify and decode a concierge token. Raises BadSignature on tamper."""
    signer = Signer(salt="asiko.concierge.vector")
    return json.loads(signer.unsign(token))
