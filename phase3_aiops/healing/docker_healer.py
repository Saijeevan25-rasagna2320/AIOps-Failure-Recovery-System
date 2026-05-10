import time
import logging
import docker
from collections import deque
from threading import Lock
from datetime import datetime

client = docker.from_env()

# -----------------------------------
# Restart policy configuration
# -----------------------------------
FAILURE_WINDOW_SECONDS = 300        # 5 min window
MIN_CONSECUTIVE_FAILURES = 3        # require repeated failures
COOLDOWN_SECONDS = 600             # 10 min between restarts
POST_RESTART_GRACE = 45           # wait before verification

# -----------------------------------
# State
# -----------------------------------
state_lock = Lock()

restart_state = {
    "last_restart_time": {},
    "failure_events": {},
    "restart_count": {}
}


def _now():
    return time.time()


def _ensure_service(service_name):
    if service_name not in restart_state["failure_events"]:
        restart_state["failure_events"][service_name] = deque()

    if service_name not in restart_state["last_restart_time"]:
        restart_state["last_restart_time"][service_name] = 0

    if service_name not in restart_state["restart_count"]:
        restart_state["restart_count"][service_name] = 0


def register_failure_event(service_name):
    """
    Called by controller when:
    - circuit breaker remains open
    - repeated timeouts
    - repeated high-risk predictions
    - service health remains degraded
    """

    with state_lock:
        _ensure_service(service_name)

        dq = restart_state["failure_events"][service_name]
        current = _now()

        dq.append(current)

        while dq and current - dq[0] > FAILURE_WINDOW_SECONDS:
            dq.popleft()


def should_restart(service_name):
    """
    Restart only if repeated failures happened recently
    and cooldown expired.
    """

    with state_lock:
        _ensure_service(service_name)

        dq = restart_state["failure_events"][service_name]
        last_restart = restart_state["last_restart_time"][service_name]

        enough_failures = len(dq) >= MIN_CONSECUTIVE_FAILURES
        cooldown_ok = (_now() - last_restart) >= COOLDOWN_SECONDS

        return enough_failures and cooldown_ok


def verify_service_recovery(service_name):
    """
    Placeholder verification hook.
    Replace with real health probe later.
    """

    time.sleep(POST_RESTART_GRACE)

    return True


def restart_container_last_resort(service_name):
    """
    Netflix-style final remediation:
    restart only after resilience layers fail.
    """

    try:
        if not should_restart(service_name):
            return {
                "success": False,
                "action": "restart_skipped",
                "reason": "threshold_not_met_or_cooldown_active"
            }

        container = client.containers.get(service_name)

        logging.warning(
            f"Last resort restart triggered for {service_name}"
        )

        container.restart()

        with state_lock:
            restart_state["last_restart_time"][service_name] = _now()
            restart_state["restart_count"][service_name] += 1
            restart_state["failure_events"][service_name].clear()

        recovered = verify_service_recovery(service_name)

        return {
            "success": recovered,
            "action": "container_restart",
            "service": service_name,
            "verified": recovered,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "success": False,
            "action": "container_restart_failed",
            "service": service_name,
            "error": str(e)
        }


def get_restart_state():
    with state_lock:
        summary = {}

        for service in restart_state["restart_count"]:
            summary[service] = {
                "restart_count": restart_state["restart_count"][service],
                "recent_failures": len(
                    restart_state["failure_events"][service]
                ),
                "last_restart_time": restart_state[
                    "last_restart_time"
                ][service]
            }

        return summary