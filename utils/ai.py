import os
import re
import pandas as pd
import logging
import time
import streamlit as st

# Configure logging to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EduVerseAI")

if "AI_INFERENCE_TIMES" not in globals():
    globals()["AI_INFERENCE_TIMES"] = []

if "LATEST_MODEL_USED" not in globals():
    globals()["LATEST_MODEL_USED"] = "Local Fallback"

def get_average_inference_time() -> float:
    times = globals().get("AI_INFERENCE_TIMES", [])
    if not times:
        return 0.8  # Default baseline
    return sum(times) / len(times)

def get_ai_model_name() -> str:
    return globals().get("LATEST_MODEL_USED", "Local Fallback")

@st.cache_resource
def get_cached_groq_client(api_key):
    from groq import Groq
    return Groq(api_key=api_key)

def get_ai_response(prompt):
    """
    Generates a conversational response for the EduVerse AI Assistant.
    Tries to use Groq API with Llama models. Falls back to a robust rule-based
    and data-driven search engine if API is offline, keys are missing, or errors occur.
    """
    logger.info(f"Received prompt: {prompt}")
    
    start_time = time.perf_counter()
    
    def record_stats(res_text, model):
        elapsed = time.perf_counter() - start_time
        globals().setdefault("AI_INFERENCE_TIMES", []).append(elapsed)
        globals()["LATEST_MODEL_USED"] = model
        return res_text

    # 1. Load Real Data for dynamic queries (cached to avoid repeated disk reads)
    try:
        from utils.ml import generate_student_data
        df = generate_student_data()
        total_students = len(df)
        avg_gpa = round(df["final_gpa"].mean(), 2)
        at_risk_count = len(df[df["risk"] == 1])
        top_5_df = df.sort_values("final_gpa", ascending=False).head(5)
        top_5_str = ", ".join([f"{row['name']} ({row['final_gpa']:.2f})" for _, row in top_5_df.iterrows()])
    except Exception as e:
        logger.error(f"Error loading sample data: {str(e)}")
        df = pd.DataFrame()
        total_students = 500
        avg_gpa = 3.22
        at_risk_count = 25
        top_5_str = "Riya Rao (4.00), Siddharth Mukherjee (4.00), Priya Kumar (4.00), Tanvi Kumar (4.00), Kavya Verma (4.00)"

    # 2. Rule-based / Data-driven Fallback Engine (Runs if prompt matches or if API fails)
    lower_prompt = prompt.lower()
    fallback_response = None
    
    # Handle greeting
    if any(greet in lower_prompt for greet in ["hello", "hi", "hey", "hola", "namaste", "kaise ho"]):
        fallback_response = "Hello! Main aapka EduVerse AI Assistant hoon. Aaj aapki academic performance aur insights mein kaise help kar sakta hoon? "
    
    # Check for specific student searches
    elif df is not None and not df.empty and ("student" in lower_prompt or "records" in lower_prompt or any(name.lower() in lower_prompt for name in df["name"].unique())):
        matched_student = None
        for name in df["name"].unique():
            if name.lower() in lower_prompt:
                matched_student = df[df["name"] == name].iloc[0]
                break
        
        if matched_student is not None:
            status = "At Academic Risk " if matched_student["risk"] == 1 else "Good Standing "
            fallback_response = (
                f"Student Profile Mil gaya!  **{matched_student['name']}** ({matched_student['department']}):\n"
                f"- **Attendance:** {matched_student['attendance_pct']}%\n"
                f"- **Previous GPA:** {matched_student['prev_gpa']}\n"
                f"- **Assignments Completed:** {matched_student['assignments_completed']}/20\n"
                f"- **Current Status:** {status}\n"
                f"Is there anything else you want to know about this student?"
            )
    
    # Platform info
    if not fallback_response:
        if "what is eduverse" in lower_prompt or "eduverse kya hai" in lower_prompt:
            fallback_response = "EduVerse ek advanced, AI-powered education analytics platform hai. Yeh students ke attendance, assignment submissions, aur exam grades ko track karke future results ko predict karta hai, taaki high-risk students ko time par support mil sake. "
        elif "how does ml work" in lower_prompt or "how does ai work" in lower_prompt or "ml kaise kaam karta" in lower_prompt:
            fallback_response = "Humara ML (Machine Learning) engine Random Forest Classifier aur Regression models use karta hai. Yeh student ke past grades, class attendance, aur study habits analyze karke fail hone ke risk aur final GPA ko predict karta hai! "
        elif "check attendance" in lower_prompt or "attendance kaise" in lower_prompt:
            fallback_response = "Aap side navigation se 'Attendance' page par jaakar apna detailed records check kar sakte hain. Always aim for 75% or above to stay out of the risk zone! "
        elif "risk level" in lower_prompt or "risk kya hai" in lower_prompt:
            fallback_response = f"Academic Risk Level humare AI prediction se nikalta hai. 30% se zyada risk level matlab aapko performance boost karne ki zaroorat hai. EduVerse mein abhi total **{at_risk_count} at-risk students** hain jinhe extra mentorship ki zaroorat hai."
        elif "kaisa kaam karta hai" in lower_prompt or "how does it work" in lower_prompt:
            fallback_response = "EduVerse aapka SQL / Supabase database se real-time data fetch karta hai, ML models ke through analyze karta hai, aur modern interactive charts aur metrics ke through visual representation pradan karta hai. simple and powerful!"
        elif "show insights" in lower_prompt or "platform stats" in lower_prompt or "at-risk students" in lower_prompt or "top performers" in lower_prompt:
            fallback_response = (
                f" **EduVerse Current Live Stats:**\n"
                f"- **Total Registered Students:** {total_students}\n"
                f"- **Average GPA:** {avg_gpa}\n"
                f"- **Students At-Risk (risk=1):** {at_risk_count} students \n"
                f"- **Top Performers:** {top_5_str} "
            )

    # 3. If a direct rule match (like Quick Action Chips) was found, return instantly (cache/bypass)
    if fallback_response:
        return record_stats(fallback_response, "Local Rule Engine (Instant)")

    # 4. Call Groq API if Key is present
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            client = get_cached_groq_client(api_key)
            system_prompt = f"""You are EduVerse AI Assistant, a friendly and highly intelligent educational counselor.
            You have access to REAL student data. Answer questions DIRECTLY, accurately, and professionally.
            
            REAL PLATFORM DATA FACTS:
            - Total Registered Students: {total_students}
            - Average GPA: {avg_gpa}
            - At-risk students (risk=1): {at_risk_count}
            - Top 5 students: {top_5_str}
            
            Rules:
            - Never repeat the exact same response twice.
            - Answer in Hinglish (a natural, premium mix of Hindi and English) to keep interactions engaging.
            - Be concise but highly helpful, limiting responses to 3-5 lines.
            - When asked about stats or top performers, always quote the exact real data figures above.
            - Never output raw HTML tags (e.g. <div>).
            """
            
            # Primary model
            try:
                model_name = "llama-3.3-70b-versatile"
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1024,
                )
                response_text = completion.choices[0].message.content
                response_text = re.sub(r'<[^>]+>', '', response_text)
                logger.info(f"API Response generated successfully via {model_name}")
                return record_stats(response_text, model_name)
            except Exception as model_err:
                logger.warning(f"Primary model failed, trying fallback model: {str(model_err)}")
                # Fallback model
                model_name = "llama-3.1-8b-instant"
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1024,
                )
                response_text = completion.choices[0].message.content
                response_text = re.sub(r'<[^>]+>', '', response_text)
                logger.info(f"API Response generated successfully via {model_name}")
                return record_stats(response_text, model_name)
            
        except Exception as api_err:
            logger.error(f"Groq API Call failed: {str(api_err)}")
            # If the API call failed but we have a custom rule-based fallback response, use it!
            if fallback_response:
                logger.info("Using rule-based response due to API failure")
                return record_stats(fallback_response, "Local Rule Engine (API Fallback)")
            
            # General helpful AI failure message
            fail_msg = (
                f"I encountered a temporary connection issue while talking to my brain, but I'm still here to help! \n\n"
                f"**Here's what I know from our local records:**\n"
                f"- EduVerse has **{total_students} registered students** with an average GPA of **{avg_gpa}**.\n"
                f"- There are **{at_risk_count} students** flagged as academically at-risk.\n"
                f"- Top performers: {top_5_str}.\n\n"
                f"*(Tech error: {str(api_err)})*"
            )
            return record_stats(fail_msg, "Local Fallback (Error)")

    # 4. If No API Key, use fallback or generic helper response
    logger.info("No Groq API Key found. Using local fallback response.")
    if fallback_response:
        return record_stats(fallback_response, "Local Rule Engine")
        
    default_msg = (
        "Main aapka EduVerse AI Assistant hoon! (API Key is not configured, but local data engine is fully active) \n\n"
        f"Aap mujhse humare platform ke statistics aur students ke baare mein pooch sakte hain. Jaise ki:\n"
        f"- *'Show insights'* ya *'Platform stats'*\n"
        f"- *'What is EduVerse?'*\n"
        f"- *'How does AI work?'*\n"
        f"- Ya kisi student ka naam (jaise: *'Aarav Sharma'*) likhkar unka status check karein!"
    )
    return record_stats(default_msg, "Local Help Engine")
