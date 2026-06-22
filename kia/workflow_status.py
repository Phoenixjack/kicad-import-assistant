from kia.debug import (
    dbg_blank,
    dbg_print, 
    Severity, 
)
		
def mark_success(
    run_state: dict,
    script: str,
    step: str,
    function_name: str,
    message: str | None = None,
    severity: Severity = Severity.INFO,
) -> dict:
    run_state["status"] = {
        "success": True,
        "severity": severity,
        "script": script,
        "step": step,
        "function_name": function_name,
        "failure_reason": None,
        "message": message,
    }

    return run_state


def mark_failure(
    run_state: dict,
    script: str,
    step: str,
    function_name: str,
    failure_reason: str,
    severity: Severity = Severity.ERROR,
) -> dict:
    run_state["status"] = {
        "success": False,
        "severity": severity,
        "script": script,
        "step": step,
        "function_name": function_name,
        "failure_reason": failure_reason,
        "message": None,
    }
    return run_state


def stop_if_failed(run_state: dict) -> None:
    if not run_state["status"]["success"]:
        critical_error(run_state)


def critical_error(run_state: dict) -> None:
    status = run_state.get("status", {})

    print()
    print("CRITICAL ERROR")
    print(status.get("failure_reason", "Unknown failure."))
    print(
        f"{status.get('script')} / "
        f"{status.get('step')} / "
        f"{status.get('function_name')}"
    )

    raise SystemExit

