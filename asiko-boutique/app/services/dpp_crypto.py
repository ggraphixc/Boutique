# ASIKO Boutique - Digital Product Passport (DPP) Cryptographic Service
# Provides verifiable garment provenance tokens using Django signing infrastructure

import json
import django
from django.conf import settings

# Initialize Django settings at module level for Signer availability
if not settings.configured:
    settings.configure(
        SECRET_KEY="asiko-django-dev-key-2026-insecure-change-in-prod",
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
        USE_TZ=True,
        TIME_ZONE="UTC",
    )
    django.setup()

from django.core.signing import Signer, BadSignature, SignatureExpired


class DPPCryptoService:
    """Cryptographic signing service for Verifiable Digital Product Passports."""

    _instance = None
    _signer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._signer = Signer(salt="asiko.concierge.vector")
        return cls._instance

    @property
    def signer(self) -> Signer:
        return self._signer

    def generate_passport_token(self, product_id: int, serial_number: str, artisan_id: str) -> str:
        """Serializes garment provenance parameters into a cryptographically signed web token."""
        payload = {
            "p_id": product_id,
            "sn": serial_number,
            "artisan": artisan_id,
        }
        serialized_data = json.dumps(payload, separators=(",", ":"))
        return self.signer.sign(serialized_data)

    def verify_passport_token(self, token: str) -> dict | None:
        """Validates token authenticity. Returns the decoded payload if valid, else None."""
        try:
            unsigned_data = self.signer.unsign(token)
            return json.loads(unsigned_data)
        except (BadSignature, SignatureExpired):
            return None


def get_dpp_service() -> DPPCryptoService:
    """Factory function to retrieve the singleton DPPCryptoService instance."""
    return DPPCryptoService()