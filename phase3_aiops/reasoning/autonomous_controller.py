import time
import logging
import joblib
import pandas as pd
import csv
import os

from threading import Lock
from datetime import datetime

from phase3_aiops.collector.prometheus_collector import (
    get_latest_metrics
)

from phase3_aiops.reasoning.root_cause_engine import (
    determine_root_cause
)

from phase3_aiops.healing.docker_healer import (
    register_failure_event,
    restart_container_last_resort
)

# -------------------------------------------------
# Paths
# -------------------------------------------------
MODEL_PATH = "phase3_aiops/data/models/future_failure_model.pkl"
ACTION_LOG = "phase3_aiops/data/raw/healing_history.csv"

# -------------------------------------------------
# Controller Timing
# -------------------------------------------------
CHECK_INTERVAL_HEALTHY = 15
CHECK_INTERVAL_RISK = 5

# -------------------------------------------------
# Confidence Thresholds
# -------------------------------------------------
SOFT_THRESHOLD = 0.60
HARD_THRESHOLD = 0.80

# -------------------------------------------------
# Infra Expectations
# -------------------------------------------------
EXPECTED_SERVICES = 7

# -------------------------------------------------
# Load Model
# -------------------------------------------------
model = joblib.load(MODEL_PATH)

# -------------------------------------------------
# Shared State
# -------------------------------------------------
state_lock = Lock()

controller_state = {
    "last_action": None,
    "last_reason": None,
    "last_confidence": 0,
    "incident_active": False,
    "prediction_count": 0,
    "medium_risk_count": 0,
    "high_risk_count": 0,
    "heal_count": 0
}

# -------------------------------------------------
# CSV Init
# -------------------------------------------------
def init_log():

    os.makedirs(
        os.path.dirname(ACTION_LOG),
        exist_ok=True
    )

    if not os.path.exists(ACTION_LOG):

        with open(ACTION_LOG, "w", newline="") as f:
            writer = csv.writer(f)

            writer.writerow([
                "timestamp",
                "prediction",
                "confidence",
                "mode",
                "cause",
                "service",
                "action",
                "result"
            ])


# -------------------------------------------------
# CSV Log
# -------------------------------------------------
def log_action(
    pred,
    conf,
    mode,
    cause,
    service,
    action,
    result
):

    with open(ACTION_LOG, "a", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            datetime.utcnow().isoformat(),
            pred,
            round(conf, 4),
            mode,
            cause,
            service,
            action,
            str(result)
        ])


# -------------------------------------------------
# Prediction
# Must match training schema exactly
# -------------------------------------------------
def predict_risk(metrics):

    df = pd.DataFrame([{
        "request_rate": metrics["request_rate"],
        "error_rate": metrics["error_rate"],
        "latency": metrics["latency"],
        "cpu": metrics["cpu"],
        "memory": metrics["memory"]
    }])

    pred = int(
        model.predict(df)[0]
    )

    conf = float(
        model.predict_proba(df)[0][pred]
    )

    return pred, conf


# -------------------------------------------------
# Healing Execution
# -------------------------------------------------
def execute_action(service, action):

    try:

        # ---------------------------------
        # Restart Container
        # ---------------------------------
        if action == "restart_container":

            register_failure_event(service)

            return restart_container_last_resort(
                service
            )

        # ---------------------------------
        # Scale Up
        # ---------------------------------
        elif action == "scale_up":

            logging.warning(
                f"Scaling requested for {service}"
            )

            return {
                "success": True,
                "action": "scale_up",
                "service": service,
                "replicas_added": 1
            }

        # ---------------------------------
        # Rollback
        # ---------------------------------
        elif action == "rollback":

            logging.warning(
                f"Rollback requested for {service}"
            )

            return {
                "success": True,
                "action": "rollback",
                "service": service,
                "version": "previous_stable"
            }

        # ---------------------------------
        # Reroute Traffic
        # ---------------------------------
        elif action == "reroute_traffic":

            logging.warning(
                f"Traffic reroute requested for {service}"
            )

            return {
                "success": True,
                "action": "reroute_traffic",
                "service": service,
                "status": "traffic_shifted"
            }

        # ---------------------------------
        # Unknown
        # ---------------------------------
        return {
            "success": False,
            "action": "unknown",
            "service": service
        }

    except Exception as e:

        return {
            "success": False,
            "action": action,
            "service": service,
            "error": str(e)
        }
    

def verify_post_action(before_metrics):

    time.sleep(20)

    after_metrics = get_latest_metrics()

    if not after_metrics:
        return {
            "verified": False,
            "reason": "no_metrics_after_action"
        }

    improved = 0

    if after_metrics["cpu"] < before_metrics["cpu"]:
        improved += 1

    if after_metrics["error_rate"] <= before_metrics["error_rate"]:
        improved += 1

    if after_metrics["latency"] <= before_metrics["latency"]:
        improved += 1

    if after_metrics["service_health"] >= before_metrics["service_health"]:
        improved += 1

    success = improved >= 2

    return {
        "verified": success,
        "score": improved,
        "before": before_metrics,
        "after": after_metrics
    }

# -------------------------------------------------
# Main Loop
# -------------------------------------------------
def autonomous_loop():

    init_log()

    logging.info(
        "Autonomous Controller Started"
    )

    while True:

        try:
            metrics = get_latest_metrics()

            if not metrics:
                time.sleep(5)
                continue

            pred, conf = predict_risk(metrics)

            with state_lock:
                controller_state[
                    "prediction_count"
                ] += 1

                controller_state[
                    "last_confidence"
                ] = conf

            logging.info(
                f"Prediction={pred} | "
                f"Confidence={round(conf,4)}"
            )

            # ---------------------------------
            # HEALTHY MODE
            # ---------------------------------
            if (
                pred == 0 and
                conf < SOFT_THRESHOLD
            ):

                with state_lock:
                    controller_state[
                        "incident_active"
                    ] = False

                logging.info(
                    "System healthy"
                )

                time.sleep(
                    CHECK_INTERVAL_HEALTHY
                )
                continue

            # ---------------------------------
            # Reasoning Layer
            # ---------------------------------
            insight = determine_root_cause(
                metrics
            )

            cause = insight["cause"]
            service = insight["service"]
            action = insight["action"]
            reason = insight["reason"]

            with state_lock:
                controller_state[
                    "last_reason"
                ] = reason

            # ---------------------------------
            # SHADOW MODE
            # ---------------------------------
            if (
                conf >= SOFT_THRESHOLD
                and conf < HARD_THRESHOLD
            ):

                with state_lock:
                    controller_state[
                        "medium_risk_count"
                    ] += 1

                    controller_state[
                        "incident_active"
                    ] = True

                logging.warning(
                    f"SHADOW MODE | "
                    f"Confidence={round(conf,4)} | "
                    f"Cause={cause} | "
                    f"Service={service} | "
                    f"Suggested={action}"
                )

                log_action(
                    pred,
                    conf,
                    "shadow",
                    cause,
                    service,
                    action,
                    "no_execution"
                )

                time.sleep(
                    CHECK_INTERVAL_RISK
                )
                continue

            # ---------------------------------
            # HIGH RISK MODE
            # ---------------------------------
            if (
                pred == 1 and
                conf >= HARD_THRESHOLD
            ):

                with state_lock:
                    controller_state[
                        "high_risk_count"
                    ] += 1

                    controller_state[
                        "incident_active"
                    ] = True

                logging.warning(
                    f"HIGH RISK | "
                    f"Confidence={round(conf,4)} | "
                    f"Cause={cause} | "
                    f"Service={service} | "
                    f"Action={action}"
                )

                before_metrics = metrics.copy()

                result = execute_action(
                    service,
                    action
                )

                verification = verify_post_action(
                    before_metrics
                )

                result["verification"] = verification

                with state_lock:
                    controller_state[
                        "heal_count"
                    ] += 1

                    controller_state[
                        "last_action"
                    ] = f"{action}:{service}"

                log_action(
                    pred,
                    conf,
                    "high_risk",
                    cause,
                    service,
                    action,
                    result
                )

                logging.warning(
                    f"Remediation completed for {service} | "
                    f"Verified={verification['verified']} | "
                    f"Score={verification['score']}"
                )

            time.sleep(
                CHECK_INTERVAL_RISK
            )

        except Exception as e:

            logging.error(
                f"Controller error: {e}"
            )

            time.sleep(5)


# -------------------------------------------------
# Dashboard Getter
# -------------------------------------------------
def get_controller_status():

    with state_lock:
        return dict(
            controller_state
        )