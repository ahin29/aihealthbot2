import streamlit as st
import openai
from datetime import datetime
import re
import os

# Page config
st.set_page_config(
    page_title="LinQMD Medical Assistant",
    page_icon="🏥",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "patient_summary" not in st.session_state:
    st.session_state.patient_summary = ""
if "clinical_summary" not in st.session_state:
    st.session_state.clinical_summary = ""

# Load your prompt
@st.cache_data
def load_prompt():
    with open('medical_prompt.txt', 'r', encoding='utf-8') as f:
        return f.read()

SYSTEM_PROMPT = load_prompt()

def extract_summaries(text):
    """Extract both summaries from AI response"""
    patient_pattern = r"---BEGIN_PATIENT_SUMMARY---(.*?)---END_PATIENT_SUMMARY---"
    clinical_pattern = r"---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL---(.*?)---END_CLINICAL_SUMMARY_CONFIDENTIAL---"
    
    patient_match = re.search(patient_pattern, text, re.DOTALL)
    clinical_match = re.search(clinical_pattern, text, re.DOTALL)
    
    patient_summary = patient_match.group(1).strip() if patient_match else None
    clinical_summary = clinical_match.group(1).strip() if clinical_match else None
    
    return patient_summary, clinical_summary

def clean_response_for_display(text):
    """Remove summaries from display text"""
    # Remove both summary blocks
    text = re.sub(r"---BEGIN_PATIENT_SUMMARY---.*?---END_PATIENT_SUMMARY---", "", text, flags=re.DOTALL)
    text = re.sub(r"---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL---.*?---END_CLINICAL_SUMMARY_CONFIDENTIAL---", "", text, flags=re.DOTALL)
    return text.strip()

def call_openai(messages, api_key):
    """Call OpenAI API"""
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *messages
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# Main app
st.title("🏥 LinQMD Medical Assistant")

# Create two columns
patient_col, doctor_col = st.columns([1, 1])

# PATIENT CHAT (Left side)
with patient_col:
    st.header("💬 Patient Consultation")
    
    # API key in sidebar
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    
    if not api_key:
        st.warning("⚠️ Enter API key in sidebar")
        st.stop()
    
    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                # Show cleaned version
                display_text = msg.get("display", msg["content"])
                st.write(display_text)
            else:
                st.write(msg["content"])
    
    # Show patient summary if available
    if st.session_state.patient_summary:
        st.success("📋 Your Summary:")
        st.info(st.session_state.patient_summary)
    
    # Chat input
    if prompt := st.chat_input("Describe your symptoms..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get AI response
        with st.spinner("AI is thinking..."):
            full_response = call_openai(st.session_state.messages, api_key)
            
            # Extract summaries if present
            patient_sum, clinical_sum = extract_summaries(full_response)
            if patient_sum and clinical_sum:
                st.session_state.patient_summary = patient_sum
                st.session_state.clinical_summary = clinical_sum
            
            # Clean response for display
            display_response = clean_response_for_display(full_response)
            
            # Save message
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "display": display_response
            })
            
            # Display response
            with st.chat_message("assistant"):
                st.write(display_response)
        
        st.rerun()

# DOCTOR DASHBOARD (Right side)
with doctor_col:
    st.header("👨‍⚕️ Doctor's Dashboard")
    
    if st.session_state.clinical_summary:
        st.success("✅ Clinical Summary Available")
        
        # Display summary
        with st.expander("View Clinical Summary", expanded=True):
            st.markdown(st.session_state.clinical_summary)
        
        # Download button
        st.download_button(
            "📥 Download Summary",
            st.session_state.clinical_summary,
            f"clinical_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
    else:
        st.info("⏳ Waiting for consultation to complete...")
        st.caption("Summary will appear here automatically")

# Sidebar reset button
if st.sidebar.button("🔄 New Consultation"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
