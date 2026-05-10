from fastapi import FastAPI
from fastapi.responses import Response
from threading import Thread
from datetime import datetime
import logging
import traceback

from fastapi import Body
from phase3_aiops.reasoning.autonomous_controller import (
    autonomous_loop,
    get_controller_status,
    execute_action,
    log_action
)

from prometheus_client import (
    Gauge,
    Counter,
    generate_latest
)

from phase3_aiops.collector.prometheus_collector import (
    collect_loop,
    get_latest_metrics
)

from phase3_aiops.reasoning.autonomous_controller import (
    autonomous_loop,
    get_controller_status
)

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -------------------------------------------------
# FastAPI App
# -------------------------------------------------
app = FastAPI(
    title="Phase 3 Advanced AIOps Engine",
    version="7.0.0",
    description="Autonomous Predictive Self-Healing Platform"
)

# -------------------------------------------------
# Global Threads
# -------------------------------------------------
collector_thread = None
controller_thread = None

# -------------------------------------------------
# Runtime State
# -------------------------------------------------
runtime_state = {
    "started_at": None,
    "last_error": None
}

# -------------------------------------------------
# Prometheus Export Metrics
# -------------------------------------------------
ai_incident_active = Gauge(
    "ai_incident_active",
    "Current incident status"
)

ai_last_confidence = Gauge(
    "ai_last_confidence",
    "Latest model confidence"
)

ai_healing_actions_total = Gauge(
    "ai_healing_actions_total",
    "Total healing actions executed"
)

ai_predictions_total = Counter(
    "ai_predictions_total",
    "Total predictions observed"
)

ai_high_risk_total = Counter(
    "ai_high_risk_total",
    "Total high risk detections"
)

# -------------------------------------------------
# Safe Thread Starter
# -------------------------------------------------
def safe_thread_start(
    target_func,
    thread_name
):

    thread = Thread(
        target=target_func,
        daemon=True,
        name=thread_name
    )

    thread.start()

    logging.info(
        f"{thread_name} started"
    )

    return thread


# -------------------------------------------------
# Runtime Metrics Sync
# -------------------------------------------------
last_prediction_count = 0
last_high_risk_count = 0

def refresh_export_metrics():

    global last_prediction_count
    global last_high_risk_count

    controller = get_controller_status()

    # gauges
    ai_incident_active.set(
        1 if controller.get(
            "incident_active",
            False
        ) else 0
    )

    ai_last_confidence.set(
        controller.get(
            "last_confidence",
            0
        )
    )

    ai_healing_actions_total.set(
        controller.get(
            "heal_count",
            0
        )
    )

    # counters sync
    current_predictions = controller.get(
        "prediction_count",
        0
    )

    current_high_risk = controller.get(
        "high_risk_count",
        0
    )

    pred_delta = current_predictions - last_prediction_count
    risk_delta = current_high_risk - last_high_risk_count

    if pred_delta > 0:
        ai_predictions_total.inc(pred_delta)

    if risk_delta > 0:
        ai_high_risk_total.inc(risk_delta)

    last_prediction_count = current_predictions
    last_high_risk_count = current_high_risk

    
# -------------------------------------------------
# Startup
# -------------------------------------------------
@app.on_event("startup")
def startup():

    global collector_thread
    global controller_thread

    try:
        runtime_state[
            "started_at"
        ] = datetime.utcnow().isoformat()

        collector_thread = safe_thread_start(
            collect_loop,
            "collector-thread"
        )

        controller_thread = safe_thread_start(
            autonomous_loop,
            "controller-thread"
        )

        logging.info(
            "Autonomous AIOps Engine Started"
        )

    except Exception as e:

        runtime_state[
            "last_error"
        ] = str(e)

        logging.error(
            traceback.format_exc()
        )


# -------------------------------------------------
# Home
# -------------------------------------------------
@app.get("/")
def home():

    return {
        "service": "phase3_aiops",
        "version": "7.0.0",
        "status": "running",
        "mode": "autonomous"
    }


# -------------------------------------------------
# Health
# -------------------------------------------------
@app.get("/health")
def health():

    return {
        "api": True,

        "collector_alive":
            collector_thread.is_alive()
            if collector_thread
            else False,

        "controller_alive":
            controller_thread.is_alive()
            if controller_thread
            else False,

        "last_error":
            runtime_state[
                "last_error"
            ]
    }


# -------------------------------------------------
# Ready
# -------------------------------------------------
@app.get("/ready")
def ready():

    metrics = get_latest_metrics()

    return {
        "ready":
            len(metrics) > 0
            and collector_thread
            and controller_thread
    }


# -------------------------------------------------
# Live Status
# -------------------------------------------------
@app.get("/status")
def status():

    refresh_export_metrics()

    return {
        "live_metrics":
            get_latest_metrics(),

        "controller":
            get_controller_status(),

        "runtime":
            runtime_state
    }


# -------------------------------------------------
# Prediction View
# -------------------------------------------------
@app.get("/predict")
def predict():

    metrics = get_latest_metrics()
    controller = get_controller_status()

    confidence = controller.get(
        "last_confidence",
        0
    )

    mode = "HEALTHY"

    if confidence >= 0.80:
        mode = "HIGH_RISK"

    elif confidence >= 0.60:
        mode = "SHADOW"

    return {
        "timestamp":
            datetime.utcnow().isoformat(),

        "prediction_window":
            "next 2 minutes",

        "confidence":
            confidence,

        "mode":
            mode,

        "metrics":
            metrics,

        "controller":
            controller
    }


# -------------------------------------------------
# Explainability View
# -------------------------------------------------
@app.get("/predict/explain")
def predict_explain():

    metrics = get_latest_metrics()
    controller = get_controller_status()

    return {
        "timestamp":
            datetime.utcnow().isoformat(),

        "confidence":
            controller.get(
                "last_confidence",
                0
            ),

        "reason":
            controller.get(
                "last_reason",
                "No issue detected"
            ),

        "last_action":
            controller.get(
                "last_action",
                None
            ),

        "incident_active":
            controller.get(
                "incident_active",
                False
            ),

        "metrics":
            metrics
    }



# -------------------------------------------------
# Shadow Approval Route
# -------------------------------------------------
@app.post("/shadow/approve")
def shadow_approve(payload: dict = Body(...)):

    service = payload.get("service")
    action = payload.get("action")
    confidence = payload.get("confidence", 0)

    if not service or not action:
        return {
            "success": False,
            "error": "service and action required"
        }

    result = execute_action(
        service,
        action
    )

    log_action(
        1,
        confidence,
        "manual_approval",
        "shadow_mode_user_approved",
        service,
        action,
        result
    )

    return {
        "success": True,
        "service": service,
        "action": action,
        "result": result
    }

# -------------------------------------------------
# Runtime Info
# -------------------------------------------------
@app.get("/runtime")
def runtime():

    uptime_seconds = None

    if runtime_state[
        "started_at"
    ]:

        started = datetime.fromisoformat(
            runtime_state[
                "started_at"
            ]
        )

        uptime_seconds = int(
            (
                datetime.utcnow() - started
            ).total_seconds()
        )

    controller = get_controller_status()

    return {
        "started_at":
            runtime_state[
                "started_at"
            ],

        "uptime_seconds":
            uptime_seconds,

        "prediction_count":
            controller.get(
                "prediction_count",
                0
            ),

        "high_risk_count":
            controller.get(
                "high_risk_count",
                0
            ),

        "heal_count":
            controller.get(
                "heal_count",
                0
            )
    }


# -------------------------------------------------
# Metrics Export
# -------------------------------------------------
@app.get("/metrics")
def metrics():

    refresh_export_metrics()

    return Response(
        generate_latest(),
        media_type="text/plain"
    )