from src.agent.capability import MatchingCapability
from src.main import AgentWorker
from src.agent.capability_worker import CapabilityWorker


class MinimalLocalPingCapability(MatchingCapability):
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
                function_name="ping_devkit",
                args=[],
                timeout=10,
            )
            if isinstance(result, dict) and result.get("success"):
                await self.capability_worker.speak("The DevKit answered.")
            else:
                await self.capability_worker.speak("The DevKit did not answer.")
        except Exception as error:
            self.worker.editor_logging_handler.error(
                f"[minimal-local-ping] action failed: {error}"
            )
            await self.capability_worker.speak("The DevKit test failed.")
        finally:
            self.capability_worker.resume_normal_flow()
