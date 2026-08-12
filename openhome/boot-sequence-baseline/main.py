from src.agent.capability import MatchingCapability
from src.main import AgentWorker
from src.agent.capability_worker import CapabilityWorker
import uuid
import requests


RELAY_KEY = "humain_rendezvous_url"
TOKEN_KEY = "humain_rendezvous_auth_token"


class BootSequenceBaselineCapability(MatchingCapability):
    """No-op baseline: records whether OpenHome reaches capability code."""

    worker: AgentWorker = None
    capability_worker: CapabilityWorker = None

    #{{register capability}}

    def call(self, worker: AgentWorker):
        self.worker = worker
        self.capability_worker = CapabilityWorker(self)
        self.run_id = "baseline_" + uuid.uuid4().hex[:16]
        self.worker.editor_logging_handler.info(
            "[boot-sequence-baseline] call entered"
        )
        self.worker.session_tasks.create(self.run())

    async def run(self):
        relay_url = ""
        auth_token = ""
        try:
            relay_url = self.capability_worker.get_api_keys(RELAY_KEY) or ""
            auth_token = self.capability_worker.get_api_keys(TOKEN_KEY) or ""
            self._receipt(relay_url, auth_token, "invoked", "started")
            self.worker.editor_logging_handler.info(
                "[boot-sequence-baseline] run started"
            )
            await self.capability_worker.speak("Baseline capability reached.")
            self._receipt(relay_url, auth_token, "spoken_output", "completed")
            self.worker.editor_logging_handler.info(
                "[boot-sequence-baseline] run completed"
            )
        except Exception as error:
            if relay_url and auth_token:
                self._receipt(relay_url, auth_token, "execution", "failed", type(error).__name__)
            self.worker.editor_logging_handler.error(
                "[boot-sequence-baseline] run failed: %s" % type(error).__name__
            )
            await self.capability_worker.speak("Baseline capability failed.")
        finally:
            self.worker.editor_logging_handler.info(
                "[boot-sequence-baseline] resuming normal flow"
            )
            if relay_url and auth_token:
                self._receipt(relay_url, auth_token, "normal_flow", "called")
            self.capability_worker.resume_normal_flow()

    def _receipt(self, relay_url, auth_token, stage, status, error_type=None):
        if not relay_url or not auth_token:
            return
        detail = {"error_type": error_type} if error_type else {}
        try:
            requests.post(
                relay_url.rstrip("/") + "/v1/observability/events",
                json={
                    "run_id": self.run_id,
                    "source": "cloud_skill",
                    "stage": stage,
                    "status": status,
                    "ability": "Boot Sequence Baseline",
                    "function": "run",
                    "detail": detail,
                },
                headers={"Authorization": "Bearer " + auth_token},
                timeout=5,
            )
        except Exception:
            self.worker.editor_logging_handler.info(
                "[boot-sequence-baseline] receipt unavailable"
            )
