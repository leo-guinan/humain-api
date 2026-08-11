from src.agent.capability import MatchingCapability
from src.main import AgentWorker
from src.agent.capability_worker import CapabilityWorker
import json
import urllib.request

BRIDGE_URL = "http://127.0.0.1:8790/v1/openhome/next"
POLL_SECONDS = 2.0


class HumAInContextSpeaker(MatchingCapability):
    """Speak only scoped envelopes emitted by the local HumAIn bridge."""

    worker: AgentWorker = None
    capability_worker: CapabilityWorker = None
    last_delivery_id: str = ""

    # {{register capability}}

    def call(self, worker: AgentWorker, background_daemon_mode: bool):
        self.worker = worker
        self.capability_worker = CapabilityWorker(self)
        self.worker.session_tasks.create(self.observe_loop())

    async def observe_loop(self):
        while True:
            try:
                request = urllib.request.Request(BRIDGE_URL, headers={"User-Agent": "humain-openhome-context/0.1"})
                with urllib.request.urlopen(request, timeout=2) as response:
                    data = json.loads(response.read().decode("utf-8"))
                envelope = data.get("speech_envelope") or {}
                delivery_id = str(envelope.get("delivery_id", ""))
                speech_text = str(envelope.get("speech_text", "")).strip()
                if data.get("status") == "ready" and delivery_id and delivery_id != self.last_delivery_id and speech_text:
                    self.last_delivery_id = delivery_id
                    await self.capability_worker.send_interrupt_signal()
                    await self.capability_worker.speak(speech_text[:500])
                    self.worker.editor_logging_handler.info("[humain-openhome] delivered scoped context %s" % delivery_id)
            except Exception as exc:
                self.worker.editor_logging_handler.info("[humain-openhome] bridge unavailable: %s" % exc)
            await self.worker.session_tasks.sleep(POLL_SECONDS)
