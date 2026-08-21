"""Train AML scoring XGBoost model on synthetic data.

This is a demo training script showing the pipeline. Production deployment
should train on real historical transaction data + sanctions lists.

Features:
- amount_usd: transaction amount
- hour_of_day: 0-23
- days_since_last_tx: velocity indicator
- jurisdiction_risk_tier: 1-5
- past_alert_count: cumulative AML alerts

Label: 0 (legitimate) or 1 (suspicious)
"""

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


def generate_synthetic_data(n_samples: int = 1000):
    """Generate synthetic transaction data for training."""
    np.random.seed(42)

    amount_usd = np.random.lognormal(mean=10, sigma=2, size=n_samples)
    hour_of_day = np.random.randint(0, 24, size=n_samples)
    days_since_last_tx = np.random.exponential(scale=10, size=n_samples)
    jurisdiction_risk_tier = np.random.randint(1, 6, size=n_samples)
    past_alert_count = np.random.poisson(lam=0.5, size=n_samples)

    labels = np.zeros(n_samples)
    for i in range(n_samples):
        risk_score = 0
        if amount_usd[i] > 100000:
            risk_score += 0.3
        if hour_of_day[i] < 6 or hour_of_day[i] > 22:
            risk_score += 0.2
        if days_since_last_tx[i] < 1:
            risk_score += 0.3
        if jurisdiction_risk_tier[i] >= 4:
            risk_score += 0.2
        if past_alert_count[i] >= 2:
            risk_score += 0.4

        if np.random.random() < risk_score:
            labels[i] = 1

    X = np.column_stack([amount_usd, hour_of_day, days_since_last_tx, jurisdiction_risk_tier, past_alert_count])
    y = labels

    return X, y


def train_model():
    """Train XGBoost model and save to disk."""
    print("Generating synthetic training data...")
    X, y = generate_synthetic_data(n_samples=5000)

    print(f"Dataset: {len(X)} samples, {sum(y)} suspicious ({sum(y)/len(y)*100:.1f}%)")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training XGBoost model...")
    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)

    print(f"Train accuracy: {train_score:.3f}")
    print(f"Test accuracy: {test_score:.3f}")

    model_path = "src/modules/ml/scripts/aml_model.pkl"
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")


if __name__ == "__main__":
    train_model()
