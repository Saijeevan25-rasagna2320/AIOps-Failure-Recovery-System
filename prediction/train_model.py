import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# ==============================
# LOAD DATA
# ==============================
df = pd.read_csv("../data/data.csv")

# ==============================
# CREATE LABEL
# ==============================
df["failure"] = (
    (df["error_rate"] > df["error_rate"].quantile(0.85)) &
    (df["latency"] > df["latency"].quantile(0.85))
).astype(int)

# ==============================
# FEATURE ENGINEERING
# ==============================
df["error_rate_change"] = df["error_rate"].diff().fillna(0)
df["latency_change"] = df["latency"].diff().fillna(0)

features = [
    "request_rate",
    "error_rate",
    "latency",
    "cpu",
    "memory",
    "error_rate_change",
    "latency_change"
]

df["memory"] = df["memory"] / df["memory"].max()

scaler = MinMaxScaler()
df[features] = scaler.fit_transform(df[features])

# ==============================
# SEQUENCE CREATION (FUTURE PREDICTION)
# ==============================
SEQ_LEN = 30
PRED_HORIZON = 60
threshold_pred = 0.35

def create_sequences(data, labels, seq_len, horizon):
    X, y = [], []
    for i in range(len(data) - seq_len - horizon):
        X.append(data[i:i+seq_len])
        y.append(labels[i + seq_len + horizon])
    return np.array(X), np.array(y)

X, y = create_sequences(df[features].values, df["failure"].values, SEQ_LEN, PRED_HORIZON)

# ==============================
# SPLIT (IMPORTANT FIX: NO SHUFFLE)
# ==============================
split_index = int(len(X) * 0.8)

X_train, X_test = X[:split_index], X[split_index:]
y_train, y_test = y[:split_index], y[split_index:]

# ==============================
# MODEL
# ==============================
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(X.shape[1], X.shape[2])),
    LSTM(32),
    Dense(1, activation="sigmoid")
])

model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])

# ==============================
# TRAIN
# ==============================
model.fit(
    X_train, y_train,
    epochs=20,
    batch_size=32,
    validation_data=(X_test, y_test),
    class_weight={0: 1.0, 1: 4.0}
)

# ==============================
# PREDICTION
# ==============================
y_prob = model.predict(X_test)
y_pred = (y_prob > threshold_pred).astype(int)

# ==============================
# SEVERITY CLASSIFICATION
# ==============================
def get_severity(prob):
    if prob > 0.6:
        return "CRITICAL"
    elif prob > 0.35:
        return "WARNING"
    return "NORMAL"

severity_levels = [get_severity(p[0]) for p in y_prob]

# ==============================
# BUFFER (SMOOTHING)
# ==============================
def apply_buffer(predictions, buffer_size=5, threshold_count=1):
    final = []
    for i in range(len(predictions)):
        window = predictions[i:i+buffer_size]
        final.append(1 if np.sum(window) >= threshold_count else 0)
    return np.array(final)

final_alerts = apply_buffer(y_pred)

print("\nClassification Report:")
print(classification_report(y_test[:len(final_alerts)], final_alerts))

# ==============================
# ADVANCED REASONING (HYBRID SCORING)
# ==============================
def explain_failure(row):
    scores = {}

    scores["CPU Overload"] = row["cpu"] * 0.4 + row["latency"] * 0.3
    scores["Memory Issue"] = row["memory"] * 0.5
    scores["Error Spike"] = row["error_rate"] * 0.5 + row["error_rate_change"] * 0.5
    scores["Latency Issue"] = row["latency"] * 0.6

    cause = max(scores, key=scores.get)

    return cause, scores

# ==============================
# ACTION ENGINE
# ==============================
def take_action(severity, cause):

    if severity == "CRITICAL":
        if cause == "CPU Overload":
            return "Scale service horizontally"
        elif cause == "Memory Issue":
            return "Restart service / optimize memory"
        elif cause == "Error Spike":
            return "Rollback recent deployment"
        elif cause == "Latency Issue":
            return "Adjust traffic routing"
        return "Trigger incident alert"

    elif severity == "WARNING":
        return "Monitor and log metrics"

    return "No action"

# ==============================
# TEMPORAL CONFIRMATION
# ==============================
def confirm_alert(predictions, index, window=3):
    return np.sum(predictions[index:index+window]) >= 2

# ==============================
# SYSTEM OUTPUT
# ==============================
print("\nSYSTEM OUTPUT\n")

for i in range(20):

    prob = y_prob[i][0]
    severity = severity_levels[i]

    if severity != "NORMAL":

        if confirm_alert(y_pred, i):

            # FIX: correct row mapping
            data_index = split_index + i
            row = df.iloc[data_index]

            cause, scores = explain_failure(row)
            action = take_action(severity, cause)

            print(f"\nALERT @ {i}")
            print(f"Probability: {prob:.2f}")
            print(f"Severity: {severity}")
            print(f"Root Cause: {cause}")
            print(f"Scores: {scores}")
            print(f"Action: {action}")

# ==============================
# SAVE MODEL
# ==============================
model.save("../models/model.h5")