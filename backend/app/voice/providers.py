"""Choose voice providers in one place; local mocks are the safe default."""
from .fakes import FakeSTT, FakeTTS
from .gnani import PrismaSTT, TimbreTTS
from ..config import settings


def get_voice_providers():
    if settings.use_mock_voice or not settings.gnani_api_key:
        return FakeSTT(), FakeTTS()
    return (PrismaSTT(settings.gnani_api_key, settings.prisma_model, settings.gnani_stt_url),
            TimbreTTS(settings.gnani_api_key, settings.timbre_model, settings.gnani_tts_url,
                      settings.gnani_tts_voice))


get_voice = get_voice_providers
