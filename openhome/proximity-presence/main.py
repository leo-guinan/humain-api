import json
from src.agent.capability import MatchingCapability
from src.main import AgentWorker
from src.agent.capability_worker import CapabilityWorker


class ProximityPresenceCapability(MatchingCapability):
    worker: AgentWorker = None
    capability_worker: CapabilityWorker = None

    #{{register capability}}

    def call(self, worker: AgentWorker):
        self.worker = worker
        self.capability_worker = CapabilityWorker(self)
        self.worker.session_tasks.create(self.run())

    async def run(self):
        try:
            result = await self.capability_worker.send_devkit_capability_action(
                function_name="get_presence",
                args=[],
                timeout=5,
                capability_name="humain-proximity-presence",
            )
            await self.capability_worker.speak(self._spoken_result(result))
        except Exception as error:
            self.worker.editor_logging_handler.error("[humain-proximity] %s" % error)
            await self.capability_worker.speak("Presence is unavailable. I will not activate the context flow.")
        finally:
            self.capability_worker.resume_normal_flow()

    @staticmethod
    def _spoken_result(result):
        if not isinstance(result, dict) or not result.get("success"):
            return "Presence is unavailable. I will not activate the context flow."
        output = (result.get("output") or "").strip()
        try:
            payload = json.loads(output)
        except (TypeError, json.JSONDecodeError):
            return "I could not read the presence receipt."
        state = payload.get("presence_state", "unavailable")
        if state == "near_verified" and payload.get("flow_eligible"):
            return "Paired presence is verified. The context flow is eligible, but private context remains closed."
        if state == "candidate_near":
            return "A device is nearby, but its pairing challenge is not verified. I will stay quiet."
        if state == "absent":
            return "No paired presence is verified. I will stay quiet."
        return "Presence is unavailable. I will not activate the context flow."
