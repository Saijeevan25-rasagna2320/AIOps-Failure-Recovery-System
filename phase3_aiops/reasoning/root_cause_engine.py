def determine_root_cause(metrics):

    cpu = metrics["cpu"]
    memory = metrics["memory"]
    error_rate = metrics["error_rate"]
    latency = metrics["latency"]
    request_rate = metrics["request_rate"]
    service_health = metrics["service_health"]

    # Service outage first
    if service_health < 7:
        return {
            "cause": "service_down",
            "service": "user-service",
            "action": "restart_container",
            "reason": "One or more services unavailable"
        }

    # CPU overload
    if cpu > 0.75:
        return {
            "cause": "cpu_saturation",
            "service": "payment-service",
            "action": "scale_up",
            "reason": "CPU usage critically high"
        }

    # Memory issue
    if memory > 2200000000:
        return {
            "cause": "memory_leak",
            "service": "inventory-service",
            "action": "restart_container",
            "reason": "Memory usage abnormally high"
        }

    # Error spike
    if error_rate > 1.2:
        return {
            "cause": "application_errors",
            "service": "order-service",
            "action": "rollback",
            "reason": "Error rate increasing rapidly"
        }

    # Traffic spike
    if request_rate > 6 and latency > 1.5:
        return {
            "cause": "traffic_spike",
            "service": "api-gateway",
            "action": "scale_up",
            "reason": "High traffic causing latency spike"
        }

    return {
        "cause": "unknown",
        "service": "unknown",
        "action": "shadow_mode",
        "reason": "No dominant cause identified"
    }