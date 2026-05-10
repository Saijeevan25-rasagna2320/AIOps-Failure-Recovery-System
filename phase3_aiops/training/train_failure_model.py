import pandas as pd
import joblib
import os
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix
)

# -------------------------------------------------
# Paths
# -------------------------------------------------
DATA_FILE = "phase3_aiops/data/raw/data.csv"
MODEL_DIR = "phase3_aiops/data/models"
MODEL_FILE = f"{MODEL_DIR}/future_failure_model.pkl"

# -------------------------------------------------
# Prediction Horizon
# 5 sec interval
# 24 rows = next 2 min
# -------------------------------------------------
LOOKAHEAD_ROWS = 24
MIN_RISK_EVENTS = 8
RANDOM_STATE = 42

# -------------------------------------------------
# Thresholds tuned to your dataset ranges
# -------------------------------------------------
REQ_HIGH = 6.5
ERR_HIGH = 1.20
LAT_HIGH = 1.50
CPU_HIGH = 0.034
MEM_HIGH = 2180000000


# -------------------------------------------------
# Load + Clean Dataset
# Schema:
# timestamp,request_rate,error_rate,latency,cpu,memory
# -------------------------------------------------
def load_data():

    df = pd.read_csv(DATA_FILE)

    df.columns = [
        c.strip().lower()
        for c in df.columns
    ]

    required_cols = [
        "timestamp",
        "request_rate",
        "error_rate",
        "latency",
        "cpu",
        "memory"
    ]

    df = df[required_cols]

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    for col in required_cols[1:]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna()
    df = df.drop_duplicates()

    # remove invalid zero rows
    df = df[
        ~(
            (df["request_rate"] == 0) &
            (df["error_rate"] == 0) &
            (df["latency"] == 0) &
            (df["cpu"] == 0) &
            (df["memory"] == 0)
        )
    ]

    # remove negatives
    for col in required_cols[1:]:
        df = df[df[col] >= 0]

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    print(
        f"Rows after cleaning: {len(df)}"
    )

    return df


# -------------------------------------------------
# Current Failure Rule
# -------------------------------------------------
def current_failure_rule(row):

    score = 0

    if row["request_rate"] > REQ_HIGH:
        score += 1

    if row["error_rate"] > ERR_HIGH:
        score += 1

    if row["latency"] > LAT_HIGH:
        score += 1

    if row["cpu"] > CPU_HIGH:
        score += 1

    if row["memory"] > MEM_HIGH:
        score += 1

    # any 2 abnormal signals
    if score >= 3:
        return 1

    return 0


# -------------------------------------------------
# Create Future Labels
# -------------------------------------------------
def create_future_labels(df):

    labels = df.apply(
        current_failure_rule,
        axis=1
    ).values

    future_targets = []

    for i in range(len(df)):

        future_window = labels[
            i + 1:i + 1 + LOOKAHEAD_ROWS
        ]

        if len(future_window) == 0:
            future_targets.append(0)
            continue

        risk_count = np.sum(
            future_window
        )

        if risk_count >= MIN_RISK_EVENTS:
            future_targets.append(1)
        else:
            future_targets.append(0)

    df["failure_risk"] = future_targets

    return df


# -------------------------------------------------
# Validation
# -------------------------------------------------
def show_distribution(df):

    counts = df[
        "failure_risk"
    ].value_counts().to_dict()

    zero_count = counts.get(0, 0)
    one_count = counts.get(1, 0)

    total = zero_count + one_count

    print("\nLabel Distribution")
    print(f"Normal (0): {zero_count}")
    print(f"Risk   (1): {one_count}")
    print(f"Total     : {total}\n")


def validate_dataset(df):

    if len(df) < 100:
        raise ValueError(
            "Too little data."
        )

    if df["failure_risk"].nunique() < 2:
        raise ValueError(
            "Only one class present."
        )


# -------------------------------------------------
# Train
# -------------------------------------------------
def train():

    df = load_data()

    df = create_future_labels(df)

    show_distribution(df)

    validate_dataset(df)

    feature_cols = [
        "request_rate",
        "error_rate",
        "latency",
        "cpu",
        "memory"
    ]

    X = df[feature_cols]
    y = df["failure_risk"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    pred = model.predict(X_test)

    print("Classification Report")
    print(
        classification_report(
            y_test,
            pred
        )
    )

    print("Confusion Matrix")
    print(
        confusion_matrix(
            y_test,
            pred
        )
    )

    print("\nFeature Importance")

    for name, score in zip(
        feature_cols,
        model.feature_importances_
    ):
        print(
            f"{name}: {round(score,4)}"
        )

    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    joblib.dump(
        model,
        MODEL_FILE
    )

    print(
        f"\nSaved: {MODEL_FILE}"
    )


# -------------------------------------------------
# Main
# -------------------------------------------------
if __name__ == "__main__":
    train()