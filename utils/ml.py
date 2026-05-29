import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
import os

import streamlit as st

@st.cache_data
def generate_student_data(n=50):
    """Loads student data from sample_data.csv as the primary source."""
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    csv_path = str(ROOT / "data" / "sample_data.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # Standardize column names for ML logic
        if 'attendance_pct' in df.columns:
            df = df.rename(columns={'attendance_pct': 'attendance'})
        return df
    
    # Fallback to synthetic if CSV missing
    np.random.seed(42)
    data = {
        'student_id': range(1, n + 1),
        'attendance': np.random.randint(60, 100, n),
        'internal_marks': np.random.randint(40, 100, n),
        'study_hours': np.random.randint(1, 10, n),
        'prev_gpa': np.random.uniform(2.0, 4.0, n).round(2),
        'assignments_completed': np.random.randint(5, 15, n)
    }
    df = pd.DataFrame(data)
    df['final_gpa'] = (df['attendance'] * 0.2 + df['internal_marks'] * 0.4 + df['study_hours'] * 2 + df['prev_gpa'] * 10) / 25
    df['final_gpa'] = df['final_gpa'].clip(0, 4.0).round(2)
    df['risk'] = (df['final_gpa'] < 2.0).astype(int)
    return df

@st.cache_resource
def train_predictive_models():
    """Trains models on sample_data.csv with refreshed stats."""
    df = generate_student_data()
    
    # Ensure all required features exist for training
    features_list = ['attendance', 'internal_marks', 'study_hours', 'prev_gpa', 'assignments_completed']
    X = df[features_list]
    y_gpa = df['final_gpa']
    y_risk = df['risk']
    
    # GPA Regressor
    gpa_model = RandomForestRegressor(n_estimators=100, random_state=42)
    gpa_model.fit(X, y_gpa)
    
    # Risk Classifier
    risk_model = RandomForestClassifier(n_estimators=100, random_state=42)
    risk_model.fit(X, y_risk)
    
    return gpa_model, risk_model


def get_student_predictions(attendance, internal, study, prev_gpa, assignments):
    """Predicts GPA and Risk for a single student."""
    gpa_model, risk_model = train_predictive_models()
    features = np.array([[attendance, internal, study, prev_gpa, assignments]])
    
    predicted_gpa = gpa_model.predict(features)[0]
    predicted_risk = risk_model.predict_proba(features)[0][1] # Probability of risk
    
    return round(predicted_gpa, 2), round(predicted_risk * 100, 2)

def generate_subject_marks():
    """Generates subject-wise marks for visualization."""
    subjects = ['Mathematics', 'Physics', 'Computer Science', 'Data Structures', 'AI', 'Ethics']
    marks = np.random.randint(60, 98, len(subjects))
    return pd.DataFrame({'Subject': subjects, 'Marks': marks})
