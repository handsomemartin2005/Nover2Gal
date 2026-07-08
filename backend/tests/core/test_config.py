import unittest

from app.core.config import Settings


class SettingsTest(unittest.TestCase):
    def test_uses_deepseek_v4_defaults_without_persisting_secret(self):
        settings = Settings.from_env({})

        self.assertEqual(settings.llm_provider, "deepseek")
        self.assertEqual(settings.llm_base_url, "https://api.deepseek.com")
        self.assertEqual(settings.llm_model, "deepseek-v4-pro")
        self.assertEqual(settings.embedding_model, "deepseek-v4-pro")
        self.assertEqual(settings.embedding_dim, 1536)
        self.assertEqual(settings.llm_api_key, "")
        self.assertEqual(settings.image_provider, "glm")
        self.assertEqual(settings.image_model, "cogview-4")
        self.assertEqual(settings.tts_provider, "openai-compatible")

    def test_environment_overrides_model_and_key(self):
        settings = Settings.from_env(
            {
                "LLM_API_KEY": "secret-value",
                "LLM_MODEL": "deepseek-v4-flash",
                "EMBEDDING_DIM": "1024",
                "IMAGE_API_KEY": "image-secret",
                "IMAGE_MODEL": "custom-image",
                "TTS_API_KEY": "tts-secret",
                "TTS_BASE_URL": "https://tts.example.test",
                "TTS_MODEL": "voice-model",
            }
        )

        self.assertEqual(settings.llm_api_key, "secret-value")
        self.assertEqual(settings.llm_model, "deepseek-v4-flash")
        self.assertEqual(settings.embedding_dim, 1024)
        self.assertEqual(settings.image_api_key, "image-secret")
        self.assertEqual(settings.image_model, "custom-image")
        self.assertEqual(settings.tts_api_key, "tts-secret")
        self.assertEqual(settings.tts_base_url, "https://tts.example.test")
        self.assertEqual(settings.tts_model, "voice-model")

    def test_reads_user_deepseek_api_alias(self):
        settings = Settings.from_env({"DEEPSEEK_API": "alias-secret"})

        self.assertEqual(settings.llm_api_key, "alias-secret")
