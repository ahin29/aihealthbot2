import streamlit as st
from openai import OpenAI
import re

# Page config
st.set_page_config(
    page_title="Medical Intake",
    page_icon="🏥",
    layout="wide"
)

# Initialize OpenAI client with API key from secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Prompt configuration
PROMPT_ID = "pmpt_6890c2093c388190a66ef880c473a00203ff24f87032e5f6"
PROMPT_VERSION = "4"

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'patient_summary' not in st.session_state:
    st.session_state.patient_summary = ""
if 'clinical_summary' not in st.session_state:
    st.session_state.clinical_summary = ""

# Simple styling
st.markdown("""
<style>
    .clinical-summary { 
        background: #fff9f9; 
        padding: 15px; 
        border-radius: 10px;
        border: 1px solid #ffcccc;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏥 Medical Intake Assistant")

# Extract summaries from text
def extract_summaries(text):
    display_text = text
    patient_summary = ""
    clinical_summary = ""
    
    # Extract patient summary
    if "---BEGIN_PATIENT_SUMMARY---" in text:
        patient_match = re.search(
            r'---BEGIN_PATIENT_SUMMARY---(.*?)---END_PATIENT_SUMMARY---', 
            text, re.DOTALL
        )
        if patient_match:
            patient_summary = patient_match.group(1).strip()
            display_text = display_text.replace(patient_match.group(0), "")
    
    # Extract clinical summary
    if "---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL---" in text:
        clinical_match = re.search(
            r'---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL---(.*?)---END_CLINICAL_SUMMARY_CONFIDENTIAL---', 
            text, re.DOTALL
        )
        if clinical_match:
            clinical_summary = clinical_match.group(1).strip()
            display_text = display_text.replace(clinical_match.group(0), "")
    
    return display_text.strip(), patient_summary, clinical_summary

# Get AI response using stored prompt
def get_ai_response(conversation_history):
    try:
        # Format the conversation as a single input string
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in conversation_history
        ])
        
        # Use the stored prompt with conversation history as input
        response = client.responses.create(
            prompt={
                "id": PROMPT_ID,
                "version": PROMPT_VERSION
            },
            input=[conversation_text],
            text={
                "format": {
                    "type": "text"
                }
            },
            reasoning={},
            max_output_tokens=2048,
            store=True
        )
        
        return response.text
        
    except Exception as e:
        return f"Error: {str(e)}"

# Two columns layout
col1, col2 = st.columns(2)

# Patient Chat (Left)
with col1:
    st.subheader("💬 Patient Chat")
    
    # Chat display
    chat_box = st.container(height=400)
    with chat_box:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                display_text, _, _ = extract_summaries(msg['content'])
                if display_text:
                    st.markdown(f"**Assistant:** {display_text}")
    
    # Input
    user_input = st.text_input("Your message:", key="input", placeholder="Describe symptoms or type 'done' when finished")
    
    if st.button("Send") and user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get AI response using stored prompt
        with st.spinner("Processing..."):
            ai_response = get_ai_response(st.session_state.messages)
        
        # Add assistant response
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        
        # Extract summaries
        _, patient_sum, clinical_sum = extract_summaries(ai_response)
        if patient_sum:
            st.session_state.patient_summary = patient_sum
        if clinical_sum:
            st.session_state.clinical_summary = clinical_sum
        
        st.rerun()
    
    # Show patient summary
    if st.session_state.patient_summary:
        st.markdown("---")
        st.markdown("**Your Summary:**")
        st.info(st.session_state.patient_summary)

# Doctor's Summary (Right)
with col2:
    st.subheader("👨‍⚕️ Clinical Summary")
    
    if st.session_state.clinical_summary:
        st.markdown(f'<div class="clinical-summary">{st.session_state.clinical_summary}</div>', 
                   unsafe_allow_html=True)
    else:
        st.info("Clinical summary will appear here after consultation")

# Reset button
if st.button("🔄 New Consultation"):
    st.session_state.messages = []
    st.session_state.patient_summary = ""
    st.session_state.clinical_summary = ""
    st.rerun()
