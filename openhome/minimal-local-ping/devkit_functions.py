import json
import sys

try:
    from devkit_utils.devkit_logging import web_logger as log
except ImportError:
    class _Log:
        def info(self, *_args, **_kwargs):
            pass
        def error(self, *_args, **_kwargs):
            pass
    log = _Log()


def ping_devkit():
    log.info("[minimal-local-ping] ping_devkit entered")
    print(json.dumps({
        "success": True,
        "schema": "humain.minimal-local-ping.v1",
        "private_context": False,
        "message": "pong",
    }, separators=(",", ":")))


FUNCTION_REGISTRY = {"ping_devkit": ping_devkit}


if __name__ == "__main__":
    function_name = sys.argv[1] if len(sys.argv) > 1 else ""
    function = FUNCTION_REGISTRY.get(function_name)
    if function is None:
        log.error("[minimal-local-ping] unknown function")
        print(json.dumps({"success": False, "error": "unknown_function"}))
        sys.exit(1)
    function(*sys.argv[2:])
