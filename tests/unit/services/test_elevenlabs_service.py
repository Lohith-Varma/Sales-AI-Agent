import pytest
from pydantic import SecretStr
from backend.app.services.elevenlabs_service import ElevenLabsService as BackendElevenLabsService
from ai.services.elevenlabs_service import ElevenLabsService as AIElevenLabsService


def test_backend_elevenlabs_service_unconfigured():
    service = BackendElevenLabsService(api_key=None)
    assert not service.is_configured()

    service_placeholder = BackendElevenLabsService(api_key="replace-with-your-provider-key")
    assert not service_placeholder.is_configured()


def test_backend_elevenlabs_service_configured():
    service = BackendElevenLabsService(api_key="sk_test_key_12345")
    assert service.is_configured()


def test_ai_elevenlabs_service_unconfigured():
    service = AIElevenLabsService(api_key=None)
    assert not service.is_configured()

    service_placeholder = AIElevenLabsService(api_key=SecretStr("replace-with-your-provider-key"))
    assert not service_placeholder.is_configured()


def test_ai_elevenlabs_service_configured():
    service = AIElevenLabsService(api_key=SecretStr("sk_test_key_12345"))
    assert service.is_configured()
    assert service.api_key == "sk_test_key_12345"


@pytest.mark.asyncio
async def test_backend_elevenlabs_empty_text():
    service = BackendElevenLabsService(api_key="sk_test_key_12345")
    speech = await service.generate_speech("")
    assert speech == b""


@pytest.mark.asyncio
async def test_ai_elevenlabs_empty_text():
    service = AIElevenLabsService(api_key=SecretStr("sk_test_key_12345"))
    speech = await service.generate_speech("")
    assert speech == b""
