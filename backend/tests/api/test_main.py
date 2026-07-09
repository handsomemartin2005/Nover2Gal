import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import write_sample_epub


class MainAPITest(unittest.TestCase):
    def test_health_endpoint(self):
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_pipeline_run_endpoint_returns_exports(self):
        client = TestClient(app)

        response = client.post(
            "/api/pipeline/run",
            json={
                "title": "雨夜旧楼",
                "pov_character": "林雨",
                "text": "第一章 雨夜\n林雨推开门。\n苏晚把纸藏到身后。\n“别问。”苏晚说。",
                "llm_model": "deepseek-v4-flash",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "雨夜旧楼")
        self.assertIn("adaptation_scenes", payload)
        self.assertIn("exports", payload)
        self.assertIn("renpy", payload["exports"])

    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_pipeline_run_endpoint_accepts_max_scenes(self):
        client = TestClient(app)
        text = (
            "第一章 雨夜\n"
            "林雨停在门口，苏晚把纸条藏到身后。雨声压住了走廊里的脚步声，他还是听见门缝后有人移动，便伸手按住门把。\n\n"
            "林雨走进教室，苏晚退到讲台旁边。那张泛黄的纸被她压在书本下面，只露出一个角，像是在等他主动开口。"
        )

        response = client.post(
            "/api/pipeline/run",
            json={"title": "雨夜旧楼", "pov_character": "林雨", "text": text, "max_scenes": 1},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(len(payload["source_scenes"]), 1)
        self.assertEqual(len(payload["adaptation_scenes"]), 1)
        self.assertIn("stats", payload)
        self.assertNotIn("text", payload["source_scenes"][0])
        self.assertNotIn("text", payload["source_chunks"][0])

    def test_serves_static_frontend(self):
        client = TestClient(app)

        index_response = client.get("/")
        script_response = client.get("/static/app.js")

        self.assertEqual(index_response.status_code, 200)
        self.assertIn("Novel2Gal", index_response.text)
        self.assertIn('type="file"', index_response.text)
        self.assertIn('id="gamePreview"', index_response.text)
        self.assertIn('id="thoughtPanel"', index_response.text)
        self.assertIn('id="adapterStatus"', index_response.text)
        self.assertIn('id="maxScenes"', index_response.text)
        self.assertIn('id="llmModel"', index_response.text)
        self.assertIn('id="modelHint"', index_response.text)
        self.assertIn("质量优先", index_response.text)
        self.assertIn("速度优先", index_response.text)
        self.assertIn('id="gameAuto"', index_response.text)
        self.assertIn('id="gameJump"', index_response.text)
        self.assertIn('id="gameFullscreen"', index_response.text)
        self.assertIn('id="sceneRecommend"', index_response.text)
        self.assertIn("model-option", index_response.text)
        self.assertEqual(script_response.status_code, 200)
        self.assertIn("runPipeline", script_response.text)
        self.assertIn("renderGamePreview", script_response.text)
        self.assertIn("renderAdapterStatus", script_response.text)
        self.assertIn("renderStage", script_response.text)
        self.assertIn("CHARACTER_PORTRAITS", script_response.text)
        self.assertIn("stage-character", script_response.text)
        self.assertIn("applyChoiceBranch", script_response.text)
        self.assertIn("choiceModeLabel", script_response.text)
        self.assertIn("updateThinkingStep", script_response.text)
        self.assertIn("selectedModel", script_response.text)
        self.assertIn("updateModelHint", script_response.text)
        self.assertIn("MODEL_DETAILS", script_response.text)
        self.assertIn("llm_model", script_response.text)
        self.assertIn("loadExternalAssets", script_response.text)
        self.assertIn("scheduleAutoplay", script_response.text)
        self.assertIn("isPlayableAnimePortrait", script_response.text)
        self.assertIn("usedPortraits", script_response.text)
        self.assertIn("document.createElement(\"img\")", script_response.text)
        self.assertIn('button.textContent = choice.text || "选择"', script_response.text)
        self.assertNotIn("`${choice.text} ·", script_response.text)
        self.assertIn("/api/pipeline/upload", script_response.text)
        self.assertNotIn("原书主线", script_response.text)
        self.assertNotIn("关键事件", script_response.text)
        css_response = client.get("/static/styles.css")
        self.assertEqual(css_response.status_code, 200)
        self.assertIn(".scene-art.asset-backed .stage-prop:not(.prop-image)", css_response.text)
        self.assertIn("object-fit: contain", css_response.text)

    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_pipeline_upload_endpoint_accepts_epub(self):
        import tempfile
        from pathlib import Path

        client = TestClient(app)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.epub"
            write_sample_epub(path)

            with path.open("rb") as file:
                response = client.post(
                    "/api/pipeline/upload",
                    data={"pov_character": "林雨", "llm_model": "deepseek-v4-pro"},
                    files={"file": ("sample.epub", file, "application/epub+zip")},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "雨夜旧楼")
        self.assertIn("林雨", [character["name"] for character in payload["analysis"]["characters"]])
        self.assertIn("renpy", payload["exports"])

    def test_pipeline_run_endpoint_rejects_unknown_model(self):
        client = TestClient(app)

        response = client.post(
            "/api/pipeline/run",
            json={
                "title": "demo",
                "pov_character": "我",
                "text": "我推开门。",
                "llm_model": "deepseek-v4",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_media_provider_and_plan_endpoints(self):
        client = TestClient(app)

        providers = client.get("/api/media/providers")
        image_plan = client.post(
            "/api/media/image/plan",
            json={"prompt": "anime classroom background", "scene_id": "common_001_001", "style": "anime"},
        )
        tts_plan = client.post("/api/media/tts/plan", json={"text": "你好。", "voice": "female-soft"})

        self.assertEqual(providers.status_code, 200)
        self.assertIn("image", providers.json())
        self.assertEqual(image_plan.status_code, 200)
        self.assertEqual(image_plan.json()["style"], "anime")
        self.assertEqual(tts_plan.status_code, 200)
        self.assertEqual(tts_plan.json()["voice"], "female-soft")
