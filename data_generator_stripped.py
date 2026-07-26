import numpy as np
import pandas as pd
import random
from pathlib import Path


np.random.seed(42)
random.seed(42)

def generate_score(study_hours, max_score):
\
\
\

    base_pct = 0.50 + (study_hours / 30.0) * 0.45
    variation = np.random.normal(0, 0.08)
    final_pct = max(0.35, min(0.99, base_pct + variation))
    return round(final_pct * max_score)

def pct_to_gpa(pct):
\
\
\

    if pct >= 93:
        gpa = 4.0
    elif pct >= 90:
        gpa = 3.7
    elif pct >= 87:
        gpa = 3.3
    elif pct >= 83:
        gpa = 3.0
    elif pct >= 80:
        gpa = 2.7
    elif pct >= 77:
        gpa = 2.3
    elif pct >= 73:
        gpa = 2.0
    elif pct >= 70:
        gpa = 1.7
    else:

        if pct < 40:
            gpa = 0.0
        else:
            gpa = round(0.0 + (pct - 40) * (1.7 - 0.0) / (70 - 40), 2)



    return max(1.5, gpa)

def generate_dataset(n=500, target_min=3.20, target_max=3.40):
    first_names = ['Aarav', 'Vihaan', 'Vivaan', 'Ananya', 'Diya', 'Ishani', 'Kabir', 'Aditya', 'Arjun', 'Sai', 'Aanya', 'Krishna', 'Ishaan', 'Shaurya', 'Atharv', 'Pranav', 'Dev', 'Dia', 'Riya', 'Karan', 'Pooja', 'Rahul', 'Sneha', 'Vikram', 'Neha', 'Amit', 'Siddharth', 'Tanvi', 'Saurabh', 'Tanmay', 'Preeti', 'Abhishek', 'Meera', 'Rohan', 'Kavya', 'Gaurav', 'Swati', 'Harsh', 'Shreya', 'Nikhil', 'Priya', 'Rohit']
    last_names = ['Sharma', 'Singh', 'Verma', 'Gupta', 'Mehta', 'Patel', 'Kumar', 'Yadav', 'Joshi', 'Agarwal', 'Tiwari', 'Mishra', 'Dubey', 'Nair', 'Rao', 'Iyer', 'Pandey', 'Banerjee', 'Saxena', 'Pillai', 'Bhat', 'Desai', 'Jain', 'Kapoor', 'Reddy', 'Shah', 'Sinha', 'Kulkarni', 'Malhotra', 'Choudhury', 'Shetty', 'Menon', 'Bose', 'Dutta', 'Sen', 'Das', 'Mukherjee', 'Chatterjee', 'Roy']

    departments = ['CS', 'EE', 'ME', 'Civil', 'AI', 'DS', 'MBA', 'BBA']


    names = []
    while len(names) < n:
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        if name not in names:
            names.append(name)


    mean_sh = 24.0
    attempts = 0
    df = pd.DataFrame()

    while attempts < 100:
        np.random.seed(42 + attempts)
        study_hours_list = np.clip(np.random.normal(mean_sh, 3.5, n), 5, 30)
        attendance_list = np.clip(np.random.normal(86, 7, n), 60, 100).astype(int)
        assignments_list = np.clip(np.random.normal(16, 2.5, n), 5, 20).astype(int)

        students = []
        for i in range(n):
            sh = study_hours_list[i]
            score = generate_score(sh, 100)
            final_gpa = pct_to_gpa(score)

            prev_gpa = np.clip(np.random.normal(final_gpa, 0.20), 1.5, 4.0).round(2)


            risk = 1 if final_gpa < 2.0 else 0

            students.append({
                'student_id': i + 1,
                'name': names[i],
                'department': random.choice(departments),
                'semester': random.randint(1, 8),
                'attendance_pct': int(attendance_list[i]),
                'internal_marks': int(score),
                'assignments_completed': int(assignments_list[i]),
                'study_hours': round(sh, 1),
                'prev_gpa': float(prev_gpa),
                'final_gpa': float(final_gpa),
                'risk': int(risk)
            })

        df = pd.DataFrame(students)
        avg_gpa = df['final_gpa'].mean()

        if target_min <= avg_gpa <= target_max:

            print(f"Perfect mean study hours converged: {mean_sh:.2f} (Average GPA: {avg_gpa:.4f})")
            return df
        elif avg_gpa < target_min:
            mean_sh += 0.25
        else:
            mean_sh -= 0.25

        attempts += 1

    print("Warning: Did not fully converge in 100 attempts, returning last generated dataframe.")
    return df

def main():
    print("Generating student dataset...")
    df = generate_dataset(500, 3.20, 3.40)


    avg_gpa = df['final_gpa'].mean()
    print(f"\n--- DATASET METRICS ---")
    print(f"Total Students: {len(df)}")
    print(f"Average Class GPA: {avg_gpa:.4f}")


    top_10_threshold = df['final_gpa'].quantile(0.90)
    top_10_avg = df[df['final_gpa'] >= top_10_threshold]['final_gpa'].mean()
    print(f"Top 10% Threshold: {top_10_threshold:.2f} (Average: {top_10_avg:.4f})")


    ROOT = Path(__file__).resolve().parent
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    csv_path = data_dir / "sample_data.csv"

    df.to_csv(csv_path, index=False)
    print(f"Dataset successfully saved to: {csv_path}")

if __name__ == "__main__":
    main()
