# model.py

import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils import resample


TARGET_COL = "is_fraud"
CSV_PATH = "creditcard.csv"  # adjust path if needed


def load_raw_data(path: str = CSV_PATH) -> pd.DataFrame:
    """Load the full original dataset."""
    df = pd.read_csv(path)
    return df


def make_balanced_data(df: pd.DataFrame, fraud_ratio: float = 0.30) -> pd.DataFrame:
    """
    Return a balanced DataFrame with fraud_ratio of rows as fraud (1)
    and (1 - fraud_ratio) as non-fraud (0), total rows same as original.
    """
    total = df.shape[0]
    fraud_target = int(total * fraud_ratio)
    non_fraud_target = total - fraud_target

    fraud = df[df[TARGET_COL] == 1]
    non_fraud = df[df[TARGET_COL] == 0]

    non_fraud_bal = resample(
        non_fraud,
        replace=False,
        n_samples=non_fraud_target,
        random_state=42,
    )

    fraud_bal = resample(
        fraud,
        replace=True,
        n_samples=fraud_target,
        random_state=42,
    )

    data = pd.concat([non_fraud_bal, fraud_bal]).sample(frac=1, random_state=42)
    return data


def build_preprocessor(X_raw: pd.DataFrame) -> ColumnTransformer:
    """
    Create a ColumnTransformer that:
    - drops heavy text / ID columns
    - passes numeric columns through
    - one-hot encodes remaining categorical columns (limited categories)
    """
    drop_cols = [
        "Unnamed: 0",
        "trans_date_trans_time",
        "first",
        "last",
        "street",
        "city",
        "job",
        "dob",
        "trans_num",
    ]

    X_work = X_raw.drop(columns=[c for c in drop_cols if c in X_raw.columns])

    num_cols = X_work.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = X_work.select_dtypes(include=["object", "category"]).columns.tolist()

    pre = ColumnTransformer(
        transformers=[
            ("num", "passthrough", num_cols),
            (
                "cat",
                OneHotEncoder(
                    handle_unknown="ignore",
                    max_categories=20,
                    sparse_output=True,  # for newer sklearn
                ),
                cat_cols,
            ),
        ],
        sparse_threshold=0.3,
    )

    return pre, drop_cols


def train_and_save_model():
    """Train Random Forest on balanced data and save pipeline pieces."""
    # 1. Load and balance
    df = load_raw_data(CSV_PATH)
    data = make_balanced_data(df, fraud_ratio=0.30)

    # 2. Split features/target from BALANCED data
    X_raw = data.drop(columns=[TARGET_COL])
    y = data[TARGET_COL]

    # 3. Build preprocessor and fit on X_raw
    pre, drop_cols = build_preprocessor(X_raw)
    X_work = X_raw.drop(columns=[c for c in drop_cols if c in X_raw.columns])

    X_encoded = pre.fit_transform(X_work)

    # 4. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_encoded, y, test_size=0.20, random_state=42, stratify=y
    )

    # 5. Scale numeric data (sparse safe)
    scaler = StandardScaler(with_mean=False)
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 6. Train Random Forest
    rf = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train_scaled, y_train)

    # 7. Persist artifacts
    joblib.dump(pre, "preprocess.joblib")
    joblib.dump(scaler, "scaler.joblib")
    joblib.dump(rf, "fraud_model_rf.joblib")
    joblib.dump(drop_cols, "drop_cols.joblib")

    # optional: print simple accuracy
    acc = rf.score(X_test_scaled, y_test)
    print("Model trained. Test accuracy:", acc)
    print("Saved: preprocess.joblib, scaler.joblib, fraud_model_rf.joblib, drop_cols.joblib")


def load_pipeline():
    """Load preprocessing, scaler, model, and drop_cols from disk."""
    pre = joblib.load("preprocess.joblib")
    scaler = joblib.load("scaler.joblib")
    model = joblib.load("fraud_model_rf.joblib")
    drop_cols = joblib.load("drop_cols.joblib")
    return pre, scaler, model, drop_cols


def predict_transaction(record: dict) -> dict:
    """
    Predict fraud probability for a single transaction.

    `record` must contain the same keys as in the original CSV
    (all feature columns, except 'is_fraud'):

    ['Unnamed: 0', 'trans_date_trans_time', 'cc_num', 'merchant',
     'category', 'amt', 'first', 'last', 'gender', 'street', 'city',
     'state', 'zip', 'lat', 'long', 'city_pop', 'job', 'dob',
     'trans_num', 'unix_time', 'merch_lat', 'merch_long']
    """
    pre, scaler, model, drop_cols = load_pipeline()

    # Turn dict into DataFrame with one row
    x_df = pd.DataFrame([record])

    # Apply same column drops as during training
    x_work = x_df.drop(columns=[c for c in drop_cols if c in x_df.columns])

    # Preprocess + scale
    x_enc = pre.transform(x_work)
    x_scaled = scaler.transform(x_enc)

    # Predict
    prob = model.predict_proba(x_scaled)[0, 1]
    label = int(prob >= 0.5)

    return {"prob_fraud": float(prob), "is_fraud": label}


if __name__ == "__main__":
    # Train and save model when running this file directly
    train_and_save_model()

    # Quick sanity check using the first row of the original CSV
    df_full = load_raw_data(CSV_PATH)
    example = df_full.drop(columns=[TARGET_COL]).iloc[0].to_dict()
    result = predict_transaction(example)
    print("Example prediction:", result)
