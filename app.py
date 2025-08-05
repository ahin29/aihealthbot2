import streamlit as st
from openai import OpenAI
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

# Constants
PROMPT_ID = "pmpt_68906b8c98b08197884e6957b551a55a0940c6dfad2636d6"
PROMPT_VERSION = "3"

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
    text = re.sub(r"---BEGIN_PATIENT_SUMMARY---.*?---END_PATIENT_SUMMARY---", "", text, flags=re.DOTALL)
    text = re.sub(r"---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL---.*?---END_CLINICAL_SUMMARY_CONFIDENTIAL---", "", text, flags=re.DOTALL)
    return text.strip()

def get_api_key():
    """Get API key from Streamlit secrets or environment"""
    try:
        return st.secrets["OPENAI_API_KEY"]
    except:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            return api_key
        else:
            st.error("""
            ❌ **OpenAI API Key not found!**
            
            **For Streamlit Cloud:**
            Add to your app secrets:
            ```
            OPENAI_API_KEY = "sk-your-key-here"
            ```
            
            **For local development:**
            Set environment variable:
            ```bash
            export OPENAI_API_KEY="sk-your-key-here"
            ```
            """)
            st.stop()

@st.cache_resource
def get_openai_client():
    """Initialize OpenAI client"""
    api_key = get_api_key()
    return OpenAI(api_key=api_key)

def call_openai_with_prompt_id(messages):
    """Call OpenAI API using prompt ID"""
    try:
        client = get_openai_client()
        
        # Try using the prompt ID method first
        try:
            response = client.responses.create(
                prompt={
                    "id": PROMPT_ID,
                    "version": PROMPT_VERSION
                },
                messages=messages
            )
            return response.choices[0].message.content
        
        except AttributeError:
            # Fallback to standard chat completion if responses.create is not available
            # This happens when using standard OpenAI API
            st.warning("Using standard API method. Make sure your prompt is saved in OpenAI Playground.")
            
            # Use standard chat completion with system prompt
            response = client.chat.completions.create(
                model=st.session_state.get("model", "gpt-4"),
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    *messages
                ],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content
            
    except Exception as e:
        st.error(f"❌ Error calling OpenAI: {str(e)}")
        return None

def get_system_prompt():
    """Get system prompt as fallback"""
    # Try to load from file if prompt ID method fails
    try:
        with open('medical_prompt.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """You are a medical assistant collecting patient information for professional doctors.
        
        IMPORTANT: Generate two summaries at the end:
        1. Patient summary between ---BEGIN_PATIENT_SUMMARY--- and ---END_PATIENT_SUMMARY---
        2. Clinical summary between ---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL--- and ---END_CLINICAL_SUMMARY_CONFIDENTIAL---
        
        The clinical summary should be detailed and technical, while the patient summary should be simple.
        """

# Main app
st.title("Weocome to LinQMD's Health Assistant")

# Info header
with st.expander("ℹ️ About this Medical Assistant"):
    st.markdown("""
    This AI assistant helps collect medical information before your doctor's consultation.
    
    **Important:**
    - This is NOT a medical consultation
    - The AI cannot diagnose or provide medical advice
    - For emergencies, call emergency services immediately
    
    **Prompt ID:** `pmpt_68906b8c98b08197884e6957b551a55a0940c6dfad2636d6`
    """)

# Create two columns
patient_col, doctor_col = st.columns([1, 1])

# PATIENT CHAT (Left side)
with patient_col:
    st.header("💬 Patient Consultation")
    
    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
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
            full_response = call_openai_with_prompt_id(st.session_state.messages)
            
            if full_response:
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
    
    # Show session info
    if st.session_state.messages:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages", len(st.session_state.messages))
        with col2:
            st.metric("Status", "Complete" if st.session_state.clinical_summary else "In Progress")
    
    if st.session_state.clinical_summary:
        st.success("✅ Clinical Summary Generated")
        
        # Display summary
        with st.expander("View Clinical Summary", expanded=True):
            st.markdown(st.session_state.clinical_summary)
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download Summary",
                st.session_state.clinical_summary,
                f"clinical_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        with col2:
            # Export as JSON
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "patient_summary": st.session_state.patient_summary,
                "clinical_summary": st.session_state.clinical_summary,
                "conversation": st.session_state.messages,
                "prompt_id": PROMPT_ID
            }
            st.download_button(
                "💾 Export JSON",
                str(export_data),
                f"consultation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.info("⏳ Waiting for consultation to complete...")
        st.caption("Clinical summary will appear here automatically")
        
        # Show tips
        with st.expander("💡 Tips"):
            st.markdown("""
            - Patient should say "that's all" or "I'm done" to generate summaries
            - Clinical summary includes full medical details
            - Patient only sees simplified summary
            """)

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Controls")
    
    # Model selection (for fallback method)
    model = st.selectbox(
        "AI Model (fallback)",
        ["gpt-4", "gpt-3.5-turbo"],
        help="Used if prompt ID method fails"
    )
    st.session_state["model"] = model
    
    # Session info
    st.divider()
    st.subheader("📊 Session Info")
    st.info(f"Started: {datetime.now().strftime('%I:%M %p')}")
    st.code(f"Prompt: {PROMPT_ID[:20]}...", language=None)
    
    # Reset button
    if st.button("🔄 New Consultation", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key != "model":
                del st.session_state[key]
        st.rerun()
    
    # Quick guide
    st.divider()
    st.subheader("📋 Quick Guide")
    st.markdown("""
    **For Patients:**
    1. Describe symptoms
    2. Answer questions
    3. Say "that's all"
    
    **For Doctors:**
    - View clinical summary
    - Download reports
    - All automatic!
    """)
    
    # Footer
    st.divider()
    st.caption("🏥 LinQMD Medical Assistant")
    st.caption("⚡ Powered by OpenAI")

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        background-color: #f0f2f6;
        border-radius: 10px;
        margin: 5px 0;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)
