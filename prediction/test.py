import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.model_selection import train_test_split

# ==============================
# STEP 1: LOAD DATA
# ==============================

df = pd.read_csv("data.csv")

print("✅ Data loaded")
print("Rows:", len(df))


print(df.describe())