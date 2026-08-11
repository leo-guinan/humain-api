from src.agent.capability import MatchingCapability
from src.main import AgentWorker
from src.agent.capability_worker import CapabilityWorker

POLL_SECONDS = 4.0


class ProximityObserverCapability(MatchingCapability):
    """Background-only DevKit scanner; emits no speech and no raw device data."""

    worker: AgentWorker = None
    capability_worker: CapabilityWorker = None

    #{{register capability}}

    def call(self, worker: AgentWorker, background_daemon_mode: bool = False):
        self.worker = worker
        self.capability_worker = CapabilityWorker(self)
        self.worker.session_tasks.create(self.observe_loop())

    async def observe_loop(self):
        try:
            relay_url = self.capability_worker.get_api_keys("humain_rendezvous_url") or ""
            auth_token = self.capability_worker.get_api_keys("humain_rendezvous_auth_token") or ""
            key_ref = self.capability_worker.get_api_keys("humain_openhome_key_ref") or "openhome:marvin-bodega"
            service_uuid = "12345678-1234-5678-1234-56789abcdef0"
            while True:
                try:
                    result = await self.capability_worker.send_devkit_capability_action(
                        function_name="scan_pending",
                        args=[relay_url, key_ref, service_uuid],
                        timeout=10,
                    )
                    if isinstance(result, dict) and result.get("success"):
                        self.worker.editor_logging_handler.info("[humain-proximity-observer] bounded scan completed")
                    else:
                        self.worker.editor_logging_handler.info("[humain-proximity-observer] scan unavailable")
                except Exception as error:
                    self.worker.editor_logging_handler.info("[humain-proximity-observer] unavailable: %s" % error)
                await self.worker.session_tasks.sleep(POLL_SECONDS)
        finally:
            self.capability_worker.resume_normal_flow()
