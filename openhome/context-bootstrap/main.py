from src.agent.capability import MatchingCapability
from src.main import AgentWorker
from src.agent.capability_worker import CapabilityWorker

RELAY_KEY = "humain_rendezvous_url"
TOKEN_KEY = "humain_rendezvous_auth_token"
KEY_REF_KEY = "humain_openhome_key_ref"
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
OBSERVER_NAME = "HumAIn Proximity Observer"


class HumAInContextBootstrapCapability(MatchingCapability):
    """Load bounded HumAIn context and perform one authenticated observer pass."""

    worker: AgentWorker = None
    capability_worker: CapabilityWorker = None

    #{{register capability}}

    def call(self, worker: AgentWorker):
        self.worker = worker
        self.capability_worker = CapabilityWorker(self)
        self.worker.session_tasks.create(self.run())

    async def run(self):
        try:
            relay_url = self.capability_worker.get_api_keys(RELAY_KEY) or ""
            auth_token = self.capability_worker.get_api_keys(TOKEN_KEY) or ""
            key_ref = self.capability_worker.get_api_keys(KEY_REF_KEY) or "openhome:marvin-bodega"

            if not relay_url or not auth_token:
                self.worker.editor_logging_handler.error(
                    "[humain-context-bootstrap] required relay keys are missing"
                )
                return

            context = (
                "HumAIn context is active for this session. "
                "Treat BLE observations as bounded corroboration only. "
                "Never call a candidate near state verified proximity or identity. "
                "The only permitted demo action is the exact public greeting: "
                "Welcome to story markets."
            )
            self.capability_worker.update_personality_agent_prompt(context)

            result = await self.capability_worker.send_devkit_capability_action(
                function_name="scan_pending",
                args=[relay_url, auth_token, key_ref, SERVICE_UUID],
                capability_name=OBSERVER_NAME,
                timeout=10,
            )
            if isinstance(result, dict) and result.get("success"):
                self.worker.editor_logging_handler.info(
                    "[humain-context-bootstrap] context loaded; observer pass completed"
                )
            else:
                self.worker.editor_logging_handler.info(
                    "[humain-context-bootstrap] context loaded; observer pass unavailable"
                )
        except Exception as exc:
            self.worker.editor_logging_handler.error(
                "[humain-context-bootstrap] bootstrap failed: %s" % exc
            )
        finally:
            self.capability_worker.resume_normal_flow()
