import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
import os

import streamlit as st

@st.cache_data
def generate_student_data(n=50):
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    csv_path = str(ROOT / "data" / "sample_data.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df

    np.random.seed(42)
    data = {
        'student_id': range(1, n + 1),
        'attendance_pct': np.random.randint(60, 100, n),
        'internal_marks': np.random.randint(40, 100, n),
        'study_hours': np.random.randint(1, 10, n),
        'prev_gpa': np.random.uniform(2.0, 4.0, n).round(2),
        'assignments_completed': np.random.randint(5, 15, n)
    }
    df = pd.DataFrame(data)
    df['final_gpa'] = (df['attendance_pct'] * 0.2 + df['internal_marks'] * 0.4 + df['study_hours'] * 2 + df['prev_gpa'] * 10) / 25
    df['final_gpa'] = df['final_gpa'].clip(0, 4.0).round(2)
    df['risk'] = (df['final_gpa'] < 2.0).astype(int)
    return df

@st.cache_resource
def train_predictive_models():
    df = generate_student_data()

    features_list = ['attendance_pct', 'internal_marks', 'study_hours', 'prev_gpa', 'assignments_completed']
    X = df[features_list]
    y_gpa = df['final_gpa']
    y_risk = df['risk']

    gpa_model = RandomForestRegressor(n_estimators=100, random_state=42)
    gpa_model.fit(X, y_gpa)

    risk_model = RandomForestClassifier(n_estimators=100, random_state=42)
    risk_model.fit(X, y_risk)

    return gpa_model, risk_model


def get_student_predictions(attendance_pct, internal, study, prev_gpa, assignments):
    gpa_model, risk_model = train_predictive_models()

    input_data = pd.DataFrame([[attendance_pct, internal, study, prev_gpa, assignments]],
                              columns=['attendance_pct', 'internal_marks', 'study_hours', 'prev_gpa', 'assignments_completed'])

    predicted_gpa = gpa_model.predict(input_data)[0]
    predicted_risk = risk_model.predict_proba(input_data)[0][1]

    return round(predicted_gpa, 2), round(predicted_risk * 100, 2)

def generate_subject_marks():
    subjects = ['Mathematics', 'Physics', 'Computer Science', 'Data Structures', 'AI', 'Ethics']
    marks = np.random.randint(60, 98, len(subjects))
    return pd.DataFrame({'Subject': subjects, 'Marks': marks})
