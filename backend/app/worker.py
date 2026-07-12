from __future__ import annotations

import logging

from app.schemas.story import to_api_payload
from app.services.ai_gateway import user_text_runtime
from app.services.novel_pipeline import run_pipeline
from app.services.project_queue import run_project
from app.services.task_queue import acknowledge, pop_task, requeue_processing, update_job


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("novel2gal.worker")


def run_forever() -> None:
    recovered = requeue_processing()
    LOG.info("Novel2Gal Redis worker started; recovered %s task(s)", recovered)
    while True:
        task = pop_task(timeout=5)
        if not task:
            continue
        try:
            if task.get("kind") == "pipeline":
                _run_pipeline_task(task)
            elif task.get("kind") == "project":
                settings, client = user_text_runtime(task["owner_id"])
                run_project(task["project_id"], settings=settings, llm_client=client)
            else:
                LOG.warning("Ignoring unknown task kind: %s", task.get("kind"))
        except Exception:
            LOG.exception("Task failed: %s", task.get("kind"))
            if task.get("job_id"):
                update_job(task["job_id"], status="failed", error="Worker task failed")
        finally:
            acknowledge(task)


def _run_pipeline_task(task: dict) -> None:
    job_id = task["job_id"]
    update_job(job_id, status="running")
    try:
        settings, client = user_text_runtime(task["owner_id"])
        result = run_pipeline(task["title"], task["text"], task.get("pov_character", ""),
                              max_scenes=task.get("max_scenes"), llm_model=task.get("llm_model"),
                              settings=settings, llm_client=client)
        update_job(job_id, status="done", result=to_api_payload(result), error="")
    except Exception as exc:
        update_job(job_id, status="failed", error=str(exc)[:2000])
        raise


if __name__ == "__main__":
    run_forever()
