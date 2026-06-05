# ASIKO Boutique - Digital Product Passport (DPP) Verification Suite
# Validates cryptographic token emission, tampering defense, and error states

import pytest
from app.services.dpp_crypto import DPPCryptoService


class TestDPPCryptoServiceGeneration:
    """Test suite for DPP token generation and successful verification."""

    def test_dpp_generation_and_successful_verification(self):
        """Validates that tokens encode and decode correctly with full payload integrity."""
        service = DPPCryptoService()
        token = service.generate_passport_token(
            product_id=42, serial_number="ASK-AFA-001", artisan_id="ART-BENIN-09"
        )

        payload = service.verify_passport_token(token)

        assert payload is not None
        assert payload["p_id"] == 42
        assert payload["sn"] == "ASK-AFA-001"
        assert payload["artisan"] == "ART-BENIN-09"

    def test_dpp_different_products_yield_unique_tokens(self):
        """Ensures distinct product/serial combinations produce different tokens."""
        service = DPPCryptoService()

        token_one = service.generate_passport_token(
            product_id=1, serial_number="ASK-001", artisan_id="ART-01"
        )
        token_two = service.generate_passport_token(
            product_id=2, serial_number="ASK-002", artisan_id="ART-02"
        )

        assert token_one != token_two

    def test_dpp_token_is_string_type(self):
        """Confirms generated tokens are string format for URL compatibility."""
        service = DPPCryptoService()
        token = service.generate_passport_token(
            product_id=100, serial_number="SN-TEST", artisan_id="ART-TEST"
        )

        assert isinstance(token, str)
        assert len(token) > 0


class TestDPPCryptoTamperResistance:
    """Test suite for DPP anti-tampering validation."""

    def test_dpp_tamper_resistance_suffix_injection(self):
        """Injecting malicious data after token signature causes rejection."""
        service = DPPCryptoService()
        token = service.generate_passport_token(
            product_id=42, serial_number="ASK-AFA-001", artisan_id="ART-BENIN-09"
        )

        tampered_token = token + "malicious_payload_adjustment"
        result = service.verify_passport_token(tampered_token)

        assert result is None

    def test_dpp_tamper_resistance_prefix_injection(self):
        """Injecting malicious data before token signature causes rejection."""
        service = DPPCryptoService()
        token = service.generate_passport_token(
            product_id=42, serial_number="ASK-AFA-001", artisan_id="ART-BENIN-09"
        )

        tampered_token = "injected_attack_vector_" + token
        result = service.verify_passport_token(tampered_token)

        assert result is None

    def test_dpp_tamper_resistance_payload_corruption(self):
        """Modifying internal payload characters causes signature mismatch rejection."""
        service = DPPCryptoService()
        token = service.generate_passport_token(
            product_id=42, serial_number="ASK-AFA-001", artisan_id="ART-BENIN-09"
        )

        # Find signature delimiter and corrupt payload portion
        if ":" in token:
            parts = token.split(":")
            corrupted_payload = parts[0][:-1] + "X" + parts[0][-1:]
            tampered_token = corrupted_payload + ":" + parts[1]
            result = service.verify_passport_token(tampered_token)
            assert result is None

    def test_dpp_empty_token_raises_none(self):
        """Empty token string returns None gracefully."""
        service = DPPCryptoService()
        result = service.verify_passport_token("")

        assert result is None

    def test_dpp_garbage_token_raises_none(self):
        """Non-signed token strings return None gracefully."""
        service = DPPCryptoService()
        result = service.verify_passport_token("this_is_not_a_valid_signed_token")

        assert result is None


class TestDPPSingletonBehavior:
    """Test suite for DPPCryptoService singleton pattern."""

    def test_dpp_service_singleton_returns_same_instance(self):
        """Multiple instantiations return identical signer instances."""
        service_one = DPPCryptoService()
        service_two = DPPCryptoService()

        assert service_one is service_two
        assert service_one.signer is service_two.signer

    def test_dpp_service_factory_returns_same_instance(self):
        """Factory function returns the singleton instance."""
        from app.services.dpp_crypto import get_dpp_service

        service = get_dpp_service()
        service_direct = DPPCryptoService()

        assert service is service_direct


class TestDPPTokenStructure:
    """Test suite for DPP token structure and serialization format."""

    def test_dpp_token_contains_signature_delimiter(self):
        """Tokens contain the Django signing delimiter ':'. """
        service = DPPCryptoService()
        token = service.generate_passport_token(
            product_id=1, serial_number="SN-01", artisan_id="ART-01"
        )

        assert ":" in token

    def test_dpp_large_product_id_handling(self):
        """Large product IDs serialize and deserialize correctly."""
        service = DPPCryptoService()
        large_id = 999999999
        token = service.generate_passport_token(
            product_id=large_id, serial_number="SN-LARGE", artisan_id="ART-LARGE"
        )

        payload = service.verify_passport_token(token)

        assert payload is not None
        assert payload["p_id"] == large_id

    def test_dpp_special_characters_in_serial(self):
        """Serial numbers with special characters are handled correctly."""
        service = DPPCryptoService()
        special_serial = "ASK-AFA-ÑO-2026"
        token = service.generate_passport_token(
            product_id=1, serial_number=special_serial, artisan_id="ART-01"
        )

        payload = service.verify_passport_token(token)

        assert payload is not None
        assert payload["sn"] == special_serial