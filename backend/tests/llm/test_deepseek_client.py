import unittest

from app.core.config import Settings
from app.llm.deepseek_client import DeepSeekClient


class DeepSeekClientTest(unittest.TestCase):
    def test_builds_openai_compatible_chat_payload(self):
        settings = Settings.from_env({"LLM_API_KEY": "test-key"})
        client = DeepSeekClient(settings)

        payload = client.build_chat_payload(
            [{"role": "user", "content": "把这个场景改成 Galgame。"}],
            json_output=True,
        )

        self.assertEqual(payload["model"], "deepseek-v4-pro")
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})

    def test_builds_payload_with_selected_model(self):
        settings = Settings.from_env({"LLM_API_KEY": "test-key", "LLM_MODEL": "deepseek-v4-flash"})
        client = DeepSeekClient(settings)

        payload = client.build_chat_payload([{"role": "user", "content": "hello"}])

        self.assertEqual(payload["model"], "deepseek-v4-flash")

    def test_refuses_chat_without_api_key(self):
        settings = Settings.from_env({"LLM_API_KEY": ""})
        client = DeepSeekClient(settings)

        with self.assertRaises(ValueError):
            client.chat([{"role": "user", "content": "hello"}])
