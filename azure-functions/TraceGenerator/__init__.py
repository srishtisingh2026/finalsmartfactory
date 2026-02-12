import os

import random
from datetime import datetime, timezone
from azure.cosmos import CosmosClient, exceptions

# 🔐 Key Vault (shared across App Service & Functions)
from shared.secrets import get_secret


# ============================================================
# RATIOS
# ============================================================
GOOD_RATIO = 0.65
BAD_CONTEXT_RATIO = 0.20
BAD_ANSWER_RATIO = 0.15


# ============================================================
# USERS / TRACE TYPES
# ============================================================
USERS = [f"user-{str(i).zfill(4)}" for i in range(1, 501)]

TRACE_NAMES = [
    "simple-qa",
    "multi-hop-reasoning",
    "tool-use-flow"
]


# ============================================================
# EXPANDED SMART-FACTORY DATASET
# ============================================================
DATA = [

# ================= PROCESS & OPERATIONS =================

{
    "input": "Explain valve shutdown procedure",
    "context": (
        "Standard valve shutdown includes isolating flow from both ends and slowly relieving "
        "pressure. Some legacy diagrams mention manual bleed-off valves which may not exist "
        "in newer installations. Incorrect sequencing can cause pressure shock."
    ),
    "outputs": [
        "Valve shutdown requires isolating upstream and downstream flow and relieving pressure.",
        "Valve shutdown requires isolating upstream and downstream flow and carefully relieving pressure.",
        "Valve shutdown requires isolating flow paths and gradually relieving pressure to safely reach a zero-energy state.",
        "Valve shutdown requires isolating upstream and downstream flow, gradually relieving internal pressure, verifying isolation points, and ensuring safety procedures are followed to prevent pressure shock."
    ]
},

{
    "input": "Why does the circuit breaker trip repeatedly?",
    "context": (
        "Repeated tripping usually indicates sustained overload, short circuits, or thermal fatigue. "
        "Humidity inside panels can cause intermittent leakage currents."
    ),
    "outputs": [
        "Circuit breakers trip due to overloads or thermal fatigue.",
        "Breakers trip repeatedly because of overloads, short circuits, or moisture-related leakage.",
        "Repeated breaker tripping often indicates overload conditions, insulation degradation, or environmental moisture affecting leakage currents.",
        "Circuit breakers may trip repeatedly due to overloads, thermal fatigue, humidity-related leakage currents, or protective mechanisms reacting to prolonged abnormal operating conditions."
    ]
},

{
    "input": "What caused the temperature spike in the reactor?",
    "context": (
        "Temperature spikes often arise from cooling-loop imbalance, fouled heat exchangers, "
        "or sensor drift. Flow meters may falsely indicate normal flow."
    ),
    "outputs": [
        "Temperature spikes are caused by cooling-loop imbalance or fouled heat exchangers.",
        "Reactor temperature spikes usually occur due to cooling-loop issues or sensor drift.",
        "Temperature spikes often result from cooling-loop imbalance, fouled heat exchangers, or inaccurate sensor readings.",
        "Reactor temperature spikes can occur when cooling-loop imbalance, fouled heat exchangers, or sensor drift prevent accurate temperature regulation and timely corrective action."
    ]
},

{
    "input": "How do you stabilize steam pipeline pressure?",
    "context": (
        "Steam pressure instability results from feed variability and clogged steam traps. "
        "Gradual valve modulation prevents water hammer."
    ),
    "outputs": [
        "Steam pressure is stabilized through gradual valve modulation.",
        "Pressure stabilization involves gradual valve modulation and maintaining steam traps.",
        "Steam pipeline pressure is stabilized by controlling valve adjustments and ensuring steam traps function correctly.",
        "Steam pressure stabilization requires gradual valve modulation, proper maintenance of steam traps, and careful monitoring to prevent water hammer and pressure fluctuations."
    ]
},

{
    "input": "Why did the robotic arm freeze during operation?",
    "context": (
        "Robotic freezes may be caused by encoder desynchronization, PLC communication delays, "
        "or electromagnetic interference from nearby equipment."
    ),
    "outputs": [
        "Robotic arms freeze due to encoder desynchronization or communication delays.",
        "Freezing occurs when encoders lose synchronization or PLC communication is delayed.",
        "Robotic arms may freeze when encoder feedback becomes desynchronized or PLC communication is disrupted.",
        "Robotic arm freezing can result from encoder desynchronization, PLC communication delays, or electromagnetic interference affecting control signal reliability."
    ]
},

{
    "input": "How do you detect compressed air leakage?",
    "context": (
        "Leak detection uses ultrasonic sensors or pressure decay testing. "
        "Environmental noise reduces ultrasonic accuracy."
    ),
    "outputs": [
        "Compressed air leaks are detected using ultrasonic sensors.",
        "Leaks are identified through ultrasonic scanning or pressure decay testing.",
        "Compressed air leakage detection involves ultrasonic sensors and pressure decay analysis.",
        "Compressed air leaks are detected using ultrasonic sensors or pressure decay testing while accounting for environmental noise that may affect measurement accuracy."
    ]
},

{
    "input": "Why is the conveyor belt misaligned?",
    "context": (
        "Misalignment results from uneven loading, worn idlers, warped frames, "
        "or humidity-induced belt expansion."
    ),
    "outputs": [
        "Conveyor belts misalign due to uneven loading or worn idlers.",
        "Misalignment occurs because of uneven loads or worn belt components.",
        "Conveyor belt misalignment often results from uneven loading, worn idlers, or structural deformation.",
        "Conveyor belt misalignment can occur due to uneven loading, worn idlers, warped frames, or environmental factors such as humidity causing belt expansion."
    ]
},

{
    "input": "What causes abnormal vibration in motors?",
    "context": (
        "Abnormal vibration originates from shaft imbalance, bearing wear, "
        "loose mounting bolts, or electrical air-gap issues."
    ),
    "outputs": [
        "Abnormal motor vibration is caused by imbalance or bearing wear.",
        "Motor vibration usually indicates mechanical imbalance or bearing degradation.",
        "Abnormal vibration originates from shaft imbalance, bearing wear, or loose mounting components.",
        "Abnormal motor vibration can result from shaft imbalance, bearing wear, loose mounting bolts, or electrical air-gap issues affecting smooth operation."
    ]
},

{
    "input": "How do you handle hydraulic pressure loss?",
    "context": (
        "Pressure loss may occur due to seal leaks, pump cavitation, clogged return lines, "
        "or faulty pressure gauges."
    ),
    "outputs": [
        "Hydraulic pressure loss is handled by checking seals and pumps.",
        "Pressure loss handling involves inspecting seals, pumps, and return lines.",
        "Hydraulic pressure loss is addressed by checking seals, pumps, return lines, and gauge accuracy.",
        "Handling hydraulic pressure loss requires inspecting seals, identifying pump cavitation, clearing return lines, and verifying pressure gauge functionality."
    ]
},

{
    "input": "Why did the PLC stop responding?",
    "context": (
        "PLC failures are often caused by I/O bus saturation, firmware corruption, "
        "aging power supplies, or grounding noise."
    ),
    "outputs": [
        "PLCs stop responding due to firmware or power supply issues.",
        "PLC failures often occur due to I/O saturation or electrical noise.",
        "PLC responsiveness issues are commonly caused by firmware corruption or I/O bus saturation.",
        "PLCs may stop responding because of I/O bus saturation, firmware corruption, aging power supplies, or grounding noise disrupting stable operation."
    ]
},

# ================= SAFETY & OPERATIONS =================

{
    "input": "Why did the emergency shutdown trigger unexpectedly?",
    "context": (
        "Emergency shutdowns may trigger due to faulty limit switches, "
        "false positives from vibration sensors, or wiring insulation breakdown."
    ),
    "outputs": [
        "Emergency shutdowns trigger due to sensor or wiring faults.",
        "Unexpected shutdowns often result from faulty limit switches or sensors.",
        "Emergency shutdowns may trigger unexpectedly because of sensor faults or wiring insulation issues.",
        "Unexpected emergency shutdowns can occur due to faulty limit switches, vibration sensor false positives, or wiring insulation breakdown."
    ]
},

{
    "input": "How do you test safety interlocks?",
    "context": (
        "Safety interlocks are tested by simulating fault conditions and verifying "
        "that actuators respond within certified time limits."
    ),
    "outputs": [
        "Safety interlocks are tested by simulating faults.",
        "Interlocks are tested by simulating fault conditions and observing responses.",
        "Safety interlocks are validated by simulating fault conditions and checking actuator response times.",
        "Testing safety interlocks involves simulating fault scenarios and verifying that actuators respond correctly within certified time limits."
    ]
},

{
    "input": "What causes false fire alarm activation?",
    "context": (
        "False alarms occur due to dust accumulation, steam ingress, "
        "or aging optical sensors."
    ),
    "outputs": [
        "False fire alarms occur due to dust or steam.",
        "Fire alarms activate falsely because of dust accumulation or sensor aging.",
        "False fire alarm activation often results from dust, steam ingress, or aging sensors.",
        "False fire alarms may be triggered by dust accumulation, steam ingress, or degradation of optical sensors over time."
    ]
},

# ================= ENERGY & UTILITIES =================

{
    "input": "Why is energy consumption higher during night shifts?",
    "context": (
        "Higher energy use may result from idle machines left powered, "
        "inefficient lighting systems, or improper shift shutdown procedures."
    ),
    "outputs": [
        "Energy use is higher due to idle equipment.",
        "Night shift energy consumption increases because machines remain powered.",
        "Higher energy use during night shifts often results from idle equipment and inefficient lighting.",
        "Energy consumption during night shifts can be higher due to idle machines, inefficient lighting systems, and improper shutdown procedures."
    ]
},

{
    "input": "How do you improve power factor in industrial plants?",
    "context": (
        "Power factor is improved using capacitor banks, synchronous condensers, "
        "or VFD tuning."
    ),
    "outputs": [
        "Power factor is improved using capacitor banks.",
        "Power factor improvement involves capacitor banks and VFD tuning.",
        "Industrial power factor is improved through capacitor banks and synchronous condensers.",
        "Improving power factor in industrial plants requires using capacitor banks, synchronous condensers, or tuning variable frequency drives."
    ]
},

# ================= MAINTENANCE =================

{
    "input": "Why do bearings fail prematurely?",
    "context": (
        "Premature bearing failure is caused by contamination, misalignment, "
        "improper lubrication, or overloading."
    ),
    "outputs": [
        "Bearings fail due to contamination or lubrication issues.",
        "Premature bearing failure often results from misalignment or contamination.",
        "Bearing failure occurs due to contamination, misalignment, or improper lubrication.",
        "Premature bearing failure can result from contamination, misalignment, improper lubrication, or excessive loading conditions."
    ]
},

{
    "input": "How do you predict equipment failure?",
    "context": (
        "Predictive maintenance relies on vibration analysis, thermal imaging, "
        "oil analysis, and trend monitoring."
    ),
    "outputs": [
        "Equipment failure is predicted using vibration analysis.",
        "Failure prediction involves vibration and thermal monitoring.",
        "Predictive maintenance uses vibration, thermal imaging, and oil analysis.",
        "Predicting equipment failure involves vibration analysis, thermal imaging, oil analysis, and long-term trend monitoring."
    ]
},

# ================= DATA & CONTROL =================

{
    "input": "Why are sensor readings inconsistent?",
    "context": (
        "Inconsistent readings may stem from calibration drift, EMI interference, "
        "or loose signal wiring."
    ),
    "outputs": [
        "Sensor readings are inconsistent due to calibration drift.",
        "Inconsistent readings often result from interference or wiring issues.",
        "Sensor inconsistencies are caused by calibration drift or EMI interference.",
        "Inconsistent sensor readings can occur due to calibration drift, electromagnetic interference, or loose signal wiring."
    ]
},

{
    "input": "How do you validate SCADA data accuracy?",
    "context": (
        "SCADA data is validated by cross-checking with field instruments, "
        "manual readings, and redundancy logic."
    ),
    "outputs": [
        "SCADA accuracy is validated by cross-checking data.",
        "Data accuracy is verified using field instruments.",
        "SCADA data accuracy is validated through field instrument and manual cross-checks.",
        "Validating SCADA data accuracy involves cross-checking with field instruments, manual readings, and redundancy logic."
    ]
},

# ================= NETWORK & IT =================

{
    "input": "Why is industrial Ethernet communication dropping packets?",
    "context": (
        "Packet loss may result from EMI, incorrect switch configuration, "
        "or overloaded control networks."
    ),
    "outputs": [
        "Packet loss occurs due to EMI or network overload.",
        "Industrial Ethernet drops packets because of interference or configuration issues.",
        "Packet loss is caused by EMI, incorrect switch configuration, or overloaded networks.",
        "Industrial Ethernet packet loss can result from electromagnetic interference, incorrect switch configuration, or overloaded control networks."
    ]
},

{
    "input": "How do you secure PLC networks?",
    "context": (
        "PLC networks are secured using segmentation, firewalls, "
        "role-based access, and firmware updates."
    ),
    "outputs": [
        "PLC networks are secured using segmentation.",
        "Security is achieved through access control and firewalls.",
        "PLC networks are secured using segmentation, firewalls, and role-based access.",
        "Securing PLC networks involves segmentation, firewalls, role-based access controls, and regular firmware updates."
    ]
}

]


BAD_ANSWERS = [
    "This issue is caused by gravitational anomalies in the facility.",
    "The machine stopped because it was tired after long usage.",
    "Cosmic radiation interfered with the control system.",
    "The reactor overheated due to internet connectivity issues.",
    "A software bug in the login system caused the pressure spike."
]

ALL_CONTEXTS = [d["context"] for d in DATA]


# ============================================================
# TRACE COUNTER
# ============================================================
def get_next_trace_number(counter_container):
    try:
        doc = counter_container.read_item(
            item="trace_counter",
            partition_key="trace_counter"
        )
        next_no = doc["value"] + 1
    except exceptions.CosmosResourceNotFoundError:
        next_no = 1
        doc = {
            "id": "trace_counter",
            "partitionKey": "trace_counter",
            "value": 0
        }

    doc["value"] = next_no
    counter_container.upsert_item(doc)
    return next_no


# ============================================================
# TRACE BUILDER
# ============================================================
def make_trace(trace_no, session_id, user_id, trace_name,
               input_text, context_text, output_text):

    tokens_in = random.randint(200, 3500)
    tokens_out = random.randint(50, 1500)

    trace_id = f"trace-{str(trace_no).zfill(4)}"

    return {
        "id": trace_id,
        "partitionKey": trace_id,
        "trace_id": trace_id,

        "session_id": session_id,
        "user_id": user_id,
        "trace_name": trace_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),

        # 🔥 RAG CORE
        "input": input_text,
        "context": context_text,
        "output": output_text,

        "latency_ms": random.randint(200, 8000),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens": tokens_in + tokens_out,
        "cost": round((tokens_in + tokens_out) * random.uniform(0.00008, 0.00025), 5),

        "model": random.choice(["gpt-4o", "gpt-4o-mini", "llama-3.3-70b"]),
    }


# ============================================================
# TIMER FUNCTION (AZURE FUNCTION ENTRY)
# ============================================================
def main(mytimer):

    # 🔐 Read Cosmos connection securely from Key Vault
    COSMOS_CONN_WRITE = get_secret("COSMOS-CONN-WRITE")

    cosmos = CosmosClient.from_connection_string(
        COSMOS_CONN_WRITE
    )

    db = cosmos.get_database_client("llmops-data")
    traces_container = db.get_container_client("traces")
    counter_container = db.get_container_client("metrics")

    # 🔥 HIGH VOLUME TRACE GENERATION
    for _ in range(random.randint(2, 5)):
        base = random.choice(DATA)

        input_text = base["input"]
        context_text = base["context"]
        output_text = random.choice(base["outputs"])

        r = random.random()
        if GOOD_RATIO <= r < GOOD_RATIO + BAD_CONTEXT_RATIO:
            context_text = random.choice(
                [c for c in ALL_CONTEXTS if c != context_text]
            )
        elif r >= GOOD_RATIO + BAD_CONTEXT_RATIO:
            output_text = random.choice(BAD_ANSWERS)

        trace_no = get_next_trace_number(counter_container)

        trace = make_trace(
            trace_no=trace_no,
            session_id=f"session-{random.randint(1, 200)}",
            user_id=random.choice(USERS),
            trace_name=random.choice(TRACE_NAMES),
            input_text=input_text,
            context_text=context_text,
            output_text=output_text
        )

        # ✅ MUST use create_item for Cosmos DB trigger
        traces_container.create_item(trace)
