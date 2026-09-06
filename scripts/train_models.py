import pandas as pd
import numpy as np
import os
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score, brier_score_loss, precision_score, recall_score, f1_score
import shap
import json

def load_data(data_dir):
    X = pd.read_csv(f"{data_dir}/X_features.csv")
    y = pd.read_csv(f"{data_dir}/y_target.csv")['target_failure_next_30d']
    return X, y

def temporal_train_test_split(X, y, train_ratio=0.7, val_ratio=0.15):
    # Assumes X is chronologically sorted
    n = len(X)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    X_features = X.drop(columns=['observation_timestamp', 'asset_id'])
    
    X_train = X_features.iloc[:train_end]
    y_train = y.iloc[:train_end]
    
    X_val = X_features.iloc[train_end:val_end]
    y_val = y.iloc[train_end:val_end]
    
    X_test = X_features.iloc[val_end:]
    y_test = y.iloc[val_end:]
    
    return X_train, X_val, X_test, y_train, y_val, y_test, X.iloc[val_end:]

def train_and_evaluate(X, y, model_dir):
    X_train, X_val, X_test, y_train, y_val, y_test, X_test_meta = temporal_train_test_split(X, y)
    
    print("--- Logistic Regression Baseline ---")
    lr = LogisticRegression(max_iter=1000, class_weight='balanced')
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    y_prob_lr = lr.predict_proba(X_test)[:, 1]
    
    print(f"LR PR-AUC: {average_precision_score(y_test, y_prob_lr):.4f}")
    print(f"LR Recall: {recall_score(y_test, y_pred_lr):.4f}")
    
    print("\n--- Random Forest (Calibrated) ---")
    rf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    calibrated_rf = CalibratedClassifierCV(rf, method='isotonic', cv=5)
    calibrated_rf.fit(X_train, y_train)
    
    y_pred_rf = calibrated_rf.predict(X_test)
    y_prob_rf = calibrated_rf.predict_proba(X_test)[:, 1]
    
    rf_pr_auc = average_precision_score(y_test, y_prob_rf)
    rf_recall = recall_score(y_test, y_pred_rf)
    rf_precision = precision_score(y_test, y_pred_rf)
    rf_brier = brier_score_loss(y_test, y_prob_rf)
    
    print("RF Classification Report:")
    print(classification_report(y_test, y_pred_rf))
    print(f"RF PR-AUC: {rf_pr_auc:.4f}")
    print(f"RF Recall (Critical): {rf_recall:.4f}")
    print(f"RF Brier Score (Calibration): {rf_brier:.4f}")
    
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(calibrated_rf, f"{model_dir}/calibrated_rf.joblib")
    print(f"Model saved to {model_dir}/calibrated_rf.joblib")
    
    # Save Model Card Metrics
    model_card = {
        "version": "v1.1.0",
        "primary_target": "failure_next_30d",
        "split_method": "Temporal",
        "metrics": {
            "pr_auc": float(rf_pr_auc),
            "recall": float(rf_recall),
            "precision": float(rf_precision),
            "brier_score": float(rf_brier)
        }
    }
    with open(f"{model_dir}/model_card.json", "w") as f:
        json.dump(model_card, f, indent=2)

    try:
        rf_base = calibrated_rf.calibrated_classifiers_[0].estimator
        explainer = shap.TreeExplainer(rf_base)
        shap_values = explainer.shap_values(X_test)
        
        sample_idx = 0
        sample_explanation = {
            'features': X_test.iloc[sample_idx].to_dict(),
            'shap_values': dict(zip(X_test.columns, shap_values[sample_idx][1] if isinstance(shap_values, list) else shap_values[1][sample_idx])),
            'base_value': float(explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value)
        }
        joblib.dump(sample_explanation, f"{model_dir}/sample_explanation.joblib")
    except Exception as e:
        print(f"SHAP Explainer skipped: {e}")

if __name__ == "__main__":
    X, y = load_data("data/processed")
    train_and_evaluate(X, y, "ml/models")
