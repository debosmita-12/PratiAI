import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score, brier_score_loss
import shap

def load_data(data_dir):
    X = pd.read_csv(f"{data_dir}/X_features.csv")
    y = pd.read_csv(f"{data_dir}/y_target.csv")['target_high_priority']
    return X, y

def train_and_evaluate(X, y, model_dir):
    # Train-test split (in reality, this should be temporal, but here we do random for synthetic data)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("--- Logistic Regression Baseline ---")
    lr = LogisticRegression(max_iter=1000)
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    y_prob_lr = lr.predict_proba(X_test)[:, 1]
    
    print("LR Classification Report:")
    print(classification_report(y_test, y_pred_lr))
    print(f"LR PR-AUC: {average_precision_score(y_test, y_prob_lr):.4f}")
    
    print("\n--- Random Forest (Calibrated) ---")
    rf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    calibrated_rf = CalibratedClassifierCV(rf, method='isotonic', cv=5)
    calibrated_rf.fit(X_train, y_train)
    
    y_pred_rf = calibrated_rf.predict(X_test)
    y_prob_rf = calibrated_rf.predict_proba(X_test)[:, 1]
    
    print("RF Classification Report:")
    print(classification_report(y_test, y_pred_rf))
    print(f"RF PR-AUC: {average_precision_score(y_test, y_prob_rf):.4f}")
    print(f"RF Brier Score: {brier_score_loss(y_test, y_prob_rf):.4f}")
    
    # Save the best model (RF in this case)
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(calibrated_rf, f"{model_dir}/calibrated_rf.joblib")
    print(f"Model saved to {model_dir}/calibrated_rf.joblib")
    
    # SHAP explanations on a subset of data (using the underlying RF model)
    rf_base = calibrated_rf.calibrated_classifiers_[0].estimator
    explainer = shap.TreeExplainer(rf_base)
    shap_values = explainer.shap_values(X_test)
    
    # Save a small sample for explanation API
    sample_idx = 0
    sample_explanation = {
        'features': X_test.iloc[sample_idx].to_dict(),
        'shap_values': dict(zip(X.columns, shap_values[sample_idx][1] if isinstance(shap_values, list) else shap_values[1][sample_idx])),
        'base_value': explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value
    }
    joblib.dump(sample_explanation, f"{model_dir}/sample_explanation.joblib")

if __name__ == "__main__":
    X, y = load_data("../data/processed")
    train_and_evaluate(X, y, "../ml/models")
