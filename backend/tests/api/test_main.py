import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_store import update_user
from tests.helpers import write_sample_epub


class MainAPITest(unittest.TestCase):
    def setUp(self):
        self.auth_tmp = tempfile.TemporaryDirectory()
        self.auth_env = patch.dict("os.environ", {"AUTH_DB_PATH": os.path.join(self.auth_tmp.name, "auth.sqlite3")})
        self.auth_env.start()

    def tearDown(self):
        self.auth_env.stop()
        self.auth_tmp.cleanup()

    def authenticated_client(self, username: str = "tester") -> TestClient:
        client = TestClient(app)
        response = client.post(
            "/api/auth/register",
            json={"username": username, "display_name": "测试用户", "password": "testing-password-123"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return client

    def test_health_endpoint(self):
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_pipeline_run_endpoint_returns_exports(self):
        client = self.authenticated_client()

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
        client = self.authenticated_client()
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
        create_response = client.get("/create")
        templates_response = client.get("/templates")
        api_404_response = client.get("/api/not-found")
        script_response = client.get("/static/app.js")

        self.assertEqual(index_response.status_code, 200)
        self.assertIn("Novel2Gal", index_response.text)
        self.assertIn('id="appRoot"', index_response.text)
        self.assertNotIn('id="pipelineForm"', index_response.text)
        self.assertNotIn('id="gamePreview"', index_response.text)
        self.assertEqual(index_response.headers["cache-control"], "no-store, no-cache, must-revalidate, max-age=0")
        self.assertEqual(index_response.headers["x-novel2gal-build"], "20260710-auth3")
        self.assertEqual(create_response.status_code, 200)
        self.assertIn('id="appRoot"', create_response.text)
        self.assertEqual(create_response.headers["cache-control"], "no-store, no-cache, must-revalidate, max-age=0")
        self.assertEqual(templates_response.status_code, 200)
        self.assertIn('id="appRoot"', templates_response.text)
        self.assertEqual(api_404_response.status_code, 404)
        self.assertEqual(script_response.status_code, 200)
        self.assertIn("runPipeline", script_response.text)
        self.assertIn("renderGamePreview", script_response.text)
        self.assertIn("renderAdapterStatus", script_response.text)
        self.assertIn("renderStage", script_response.text)
        self.assertIn("landingPageTemplate", script_response.text)
        self.assertIn("workbenchPageTemplate", script_response.text)
        self.assertIn("templatesPageTemplate", script_response.text)
        self.assertIn("projectsPageTemplate", script_response.text)
        self.assertIn("animeHeaderMarkup", script_response.text)
        self.assertIn('href="/create?new=1"', script_response.text)
        self.assertIn('type="file"', script_response.text)
        self.assertIn('id="gamePreview"', script_response.text)
        self.assertIn('id="thoughtPanel"', script_response.text)
        self.assertIn('id="adapterStatus"', script_response.text)
        self.assertIn('id="maxScenes"', script_response.text)
        self.assertIn('id="fullBookMode"', script_response.text)
        self.assertIn('id="llmModel"', script_response.text)
        self.assertIn('id="modelHint"', script_response.text)
        self.assertIn("质量优先", script_response.text)
        self.assertIn("速度优先", script_response.text)
        self.assertIn('id="gameAuto"', script_response.text)
        self.assertIn('id="gameJump"', script_response.text)
        self.assertIn('id="gameFullscreen"', script_response.text)
        self.assertIn('id="sceneRecommend"', script_response.text)
        self.assertIn("model-option", script_response.text)
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
        self.assertIn("focusedSpeakerName", script_response.text)
        self.assertIn("sprite--active", script_response.text)
        self.assertIn("normalizeCharacterToken", script_response.text)
        self.assertIn("document.createElement(\"img\")", script_response.text)
        self.assertIn('button.textContent = choice.text || "选择"', script_response.text)
        self.assertNotIn("`${choice.text} ·", script_response.text)
        self.assertIn("/api/pipeline/upload", script_response.text)
        self.assertIn("/api/pipeline/upload/jobs", script_response.text)
        self.assertIn("/api/pipeline/jobs/", script_response.text)
        self.assertIn("/api/projects/upload", script_response.text)
        self.assertIn("/api/projects/", script_response.text)
        self.assertNotIn("原书主线", script_response.text)
        self.assertNotIn("关键事件", script_response.text)
        css_response = client.get("/static/styles.css")
        self.assertEqual(css_response.status_code, 200)
        self.assertIn(".scene-art.asset-backed .stage-prop:not(.prop-image)", css_response.text)
        self.assertIn("object-fit: contain", css_response.text)
        self.assertIn(".site-header", css_response.text)
        self.assertIn("--color-primary", css_response.text)
        self.assertIn("--panel-bg", css_response.text)
        self.assertIn(".landing-page", css_response.text)
        self.assertIn(".landing-panel:hover", css_response.text)
        self.assertIn("/static/assets/landing/templates-anime.png", css_response.text)
        self.assertIn(".library-page", css_response.text)
        self.assertIn(".glass-panel", css_response.text)
        self.assertIn(".stage-character.sprite--inactive img", css_response.text)

    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_pipeline_upload_endpoint_accepts_epub(self):
        import tempfile
        from pathlib import Path

        client = self.authenticated_client()
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
        client = self.authenticated_client()

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

    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_pipeline_upload_job_endpoint_accepts_epub(self):
        import tempfile
        from pathlib import Path

        client = self.authenticated_client()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.epub"
            write_sample_epub(path)

            with path.open("rb") as file:
                response = client.post(
                    "/api/pipeline/upload/jobs",
                    data={"pov_character": "鏋楅洦", "llm_model": "deepseek-v4-flash"},
                    files={"file": ("sample.epub", file, "application/epub+zip")},
                )

        self.assertEqual(response.status_code, 200)
        job = response.json()
        self.assertIn(job["status"], {"queued", "running", "done"})

        status_response = client.get(f"/api/pipeline/jobs/{job['job_id']}")

        self.assertEqual(status_response.status_code, 200)
        status_payload = status_response.json()
        self.assertEqual(status_payload["status"], "done")
        self.assertIn("renpy", status_payload["result"]["exports"])

    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_project_upload_persists_and_generates_chapters(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"PROJECT_STORE_DIR": tmp}):
                client = self.authenticated_client()
                path = Path(tmp) / "sample.epub"
                write_sample_epub(path)

                with path.open("rb") as file:
                    response = client.post(
                        "/api/projects/upload",
                        data={"pov_character": "鏋楅洦", "llm_model": "deepseek-v4-flash", "max_scenes": "2"},
                        files={"file": ("sample.epub", file, "application/epub+zip")},
                    )

                self.assertEqual(response.status_code, 200)
                project = response.json()
                self.assertIn("project_id", project)

                status_response = client.get(f"/api/projects/{project['project_id']}")
                list_response = client.get("/api/projects")

                self.assertEqual(status_response.status_code, 200)
                payload = status_response.json()
                self.assertEqual(payload["status"], "done")
                self.assertGreaterEqual(payload["completed_chapters"], 1)
                self.assertGreaterEqual(payload["result"]["stats"]["adaptation_scenes"], 1)
                self.assertTrue(payload["result"]["adaptation_scenes"])
                self.assertIn("renpy", payload["result"]["exports"])
                self.assertEqual(list_response.status_code, 200)
                self.assertTrue(list_response.json()["projects"])

    def test_project_crud_versions_and_samples(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"PROJECT_STORE_DIR": tmp}):
                client = self.authenticated_client()
                created = client.post(
                    "/api/projects",
                    json={"title": "星轨企划", "source_text": "第一章\n她推开门。", "pov_character": "苏晚"},
                )
                self.assertEqual(created.status_code, 200)
                project_id = created.json()["project_id"]

                first_result = {"stats": {"adaptation_scenes": 1}, "adaptation_scenes": [], "exports": {"renpy": "one", "markdown": "one"}}
                second_result = {"stats": {"adaptation_scenes": 2}, "adaptation_scenes": [], "exports": {"renpy": "two", "markdown": "two"}}
                saved = client.patch(
                    f"/api/projects/{project_id}",
                    json={"status": "done", "result": first_result, "current_scene_id": "scene-1"},
                )
                versioned = client.patch(
                    f"/api/projects/{project_id}",
                    json={"result": second_result, "version_note": "重新生成场景"},
                )

                self.assertEqual(saved.status_code, 200)
                self.assertEqual(versioned.status_code, 200)
                self.assertEqual(versioned.json()["source_text"], "第一章\n她推开门。")
                versions = client.get(f"/api/projects/{project_id}/versions")
                self.assertEqual(len(versions.json()["versions"]), 1)

                sample = client.post(
                    f"/api/projects/{project_id}/samples",
                    json={"title": "星轨样例", "category": "校园恋爱", "include_script": True},
                )
                self.assertEqual(sample.status_code, 200)
                sample_id = sample.json()["sample_id"]
                self.assertEqual(client.get("/api/samples").status_code, 200)
                cloned = client.post(f"/api/samples/{sample_id}/clone")
                self.assertEqual(cloned.status_code, 200)
                self.assertNotEqual(cloned.json()["project_id"], project_id)

                duplicated = client.post(f"/api/projects/{project_id}/duplicate")
                self.assertEqual(duplicated.status_code, 200)
                deleted = client.delete(f"/api/projects/{project_id}")
                self.assertEqual(deleted.status_code, 200)
                self.assertEqual(client.get(f"/api/projects/{project_id}").status_code, 404)

    def test_public_sample_cannot_include_source_text(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"PROJECT_STORE_DIR": tmp}):
                client = self.authenticated_client()
                project = client.post("/api/projects", json={"title": "隐私测试", "source_text": "完整原文"}).json()
                response = client.post(
                    f"/api/projects/{project['project_id']}/samples",
                    json={"title": "公开样例", "visibility": "public", "include_source": True},
                )
                self.assertEqual(response.status_code, 422)

    def test_projects_are_isolated_by_authenticated_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"PROJECT_STORE_DIR": tmp}):
                alice = self.authenticated_client("alice")
                bob = self.authenticated_client("bob")
                anonymous = TestClient(app)

                created = alice.post("/api/projects", json={"title": "Alice 私密项目", "source_text": "不能泄露的原文"})
                self.assertEqual(created.status_code, 200)
                project_id = created.json()["project_id"]

                self.assertEqual(anonymous.get("/api/projects").status_code, 401)
                self.assertEqual(bob.get("/api/projects").json()["projects"], [])
                self.assertEqual(bob.get(f"/api/projects/{project_id}").status_code, 404)
                self.assertEqual(bob.patch(f"/api/projects/{project_id}", json={"title": "越权"}).status_code, 404)
                self.assertEqual(bob.post(f"/api/projects/{project_id}/duplicate").status_code, 404)
                self.assertEqual(bob.delete(f"/api/projects/{project_id}").status_code, 404)
                self.assertEqual(alice.get(f"/api/projects/{project_id}").json()["source_text"], "不能泄露的原文")

    def test_private_samples_are_hidden_and_public_samples_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"PROJECT_STORE_DIR": tmp}):
                alice = self.authenticated_client("alice")
                bob = self.authenticated_client("bob")
                anonymous = TestClient(app)
                project = alice.post("/api/projects", json={"title": "样例源项目", "source_text": "私密全文"}).json()
                sample = alice.post(
                    f"/api/projects/{project['project_id']}/samples",
                    json={"title": "私人样例", "visibility": "private", "include_source": True, "allow_clone": True},
                ).json()
                sample_id = sample["sample_id"]

                self.assertEqual(anonymous.get("/api/samples").json()["samples"], [])
                self.assertEqual(bob.get("/api/samples").json()["samples"], [])
                self.assertEqual(anonymous.get(f"/api/samples/{sample_id}").status_code, 404)
                self.assertEqual(bob.get(f"/api/samples/{sample_id}").status_code, 404)
                own_samples = alice.get("/api/samples").json()["samples"]
                self.assertEqual(own_samples[0]["visibility"], "private")
                self.assertTrue(own_samples[0]["can_manage"])

                published = alice.patch(f"/api/samples/{sample_id}", json={"visibility": "public"})
                self.assertEqual(published.status_code, 200)
                self.assertEqual(published.json()["visibility"], "public")
                self.assertEqual(published.json()["source_text"], "")
                public_samples = anonymous.get("/api/samples").json()["samples"]
                self.assertEqual(public_samples[0]["sample_id"], sample_id)
                self.assertNotIn("source_text", public_samples[0])
                clone = bob.post(f"/api/samples/{sample_id}/clone")
                self.assertEqual(clone.status_code, 200)
                self.assertEqual(clone.json()["owner_id"], bob.get("/api/auth/me").json()["user"]["user_id"])

    def test_registration_session_and_logout(self):
        client = TestClient(app)
        registered = client.post(
            "/api/auth/register",
            json={"username": "session-user", "display_name": "会话用户", "password": "strong-password-123"},
        )
        self.assertEqual(registered.status_code, 201)
        cookie = registered.headers.get("set-cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertEqual(client.get("/api/auth/me").json()["user"]["username"], "session-user")
        self.assertEqual(client.post("/api/auth/logout").status_code, 200)
        self.assertIsNone(client.get("/api/auth/me").json()["user"])

    def test_admin_can_manage_metadata_without_exposing_project_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"PROJECT_STORE_DIR": tmp}):
                owner = self.authenticated_client("owner")
                admin = self.authenticated_client("site-admin")
                admin_user = admin.get("/api/auth/me").json()["user"]
                update_user(admin_user["user_id"], role="admin")
                project = owner.post("/api/projects", json={"title": "受保护项目", "source_text": "管理员列表不应出现全文"}).json()
                private_sample = owner.post(
                    f"/api/projects/{project['project_id']}/samples",
                    json={"title": "受保护样例", "visibility": "private", "include_source": True},
                ).json()

                projects = admin.get("/api/admin/projects")
                self.assertEqual(projects.status_code, 200)
                self.assertEqual(projects.json()["projects"][0]["title"], "受保护项目")
                self.assertNotIn("source_text", projects.json()["projects"][0])
                self.assertEqual(admin.get(f"/api/projects/{project['project_id']}").status_code, 404)
                self.assertEqual(admin.get(f"/api/samples/{private_sample['sample_id']}").status_code, 404)
                self.assertEqual(admin.patch(f"/api/samples/{private_sample['sample_id']}", json={"visibility": "public"}).status_code, 404)
                moderated = admin.patch(
                    f"/api/admin/samples/{private_sample['sample_id']}",
                    json={"visibility": "public"},
                )
                self.assertEqual(moderated.status_code, 200)
                self.assertEqual(moderated.json()["sample"]["visibility"], "public")
                self.assertNotIn("source_text", moderated.json()["sample"])
                self.assertEqual(admin.get("/api/admin/overview").status_code, 200)
                self.assertEqual(admin.delete(f"/api/admin/projects/{project['project_id']}").status_code, 200)
                self.assertEqual(owner.get(f"/api/projects/{project['project_id']}").status_code, 404)

    def test_spa_fallback_only_allows_known_frontend_routes(self):
        client = TestClient(app)

        create_response = client.get("/create")
        env_response = client.get("/.env")
        scanner_response = client.get("/wp-json")

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(env_response.status_code, 404)
        self.assertEqual(scanner_response.status_code, 404)

    @patch.dict("os.environ", {"MAX_UPLOAD_BYTES": "8"})
    def test_pipeline_upload_rejects_oversized_file(self):
        client = self.authenticated_client()

        response = client.post(
            "/api/pipeline/upload",
            data={"pov_character": ""},
            files={"file": ("too-large.txt", b"0123456789", "text/plain")},
        )

        self.assertEqual(response.status_code, 413)

    @patch.dict("os.environ", {"MAX_PIPELINE_PROCESS_CHARS": "12"})
    def test_pipeline_text_is_trimmed_for_processing(self):
        from app.main import _prepare_pipeline_text

        self.assertEqual(_prepare_pipeline_text("0123456789abcdef"), "0123456789ab")

    def test_media_provider_and_plan_endpoints(self):
        client = self.authenticated_client()

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
