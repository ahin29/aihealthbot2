import streamlit as st
from openai import OpenAI
from datetime import datetime
import re
import os
import json

# Page config
st.set_page_config(
    page_title="Welcome to LinQMD's Health Assistant",
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

# Prompt configuration
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
            st.error("❌ **OpenAI API Key not found!**")
            st.stop()

@st.cache_resource
def get_openai_client():
    """Initialize OpenAI client"""
    api_key = get_api_key()
    return OpenAI(api_key=api_key)

def call_openai_standard(messages):
    """Standard chat completion method"""
    try:
        client = get_openai_client()
        
        # Get the prompt from secrets or use a default
        try:
            system_prompt = st.secrets["MEDICAL_PROMPT"]
        except:
            system_prompt = """You are a medical assistant collecting patient information. 
            When the consultation ends (user says 'that's all' or similar), generate two summaries:
            1. Patient summary between ---BEGIN_PATIENT_SUMMARY--- and ---END_PATIENT_SUMMARY---
            2. Clinical summary between ---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL--- and ---END_CLINICAL_SUMMARY_CONFIDENTIAL---"""
        
        # Build messages for API
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(messages)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=api_messages,
            temperature=0.3,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

# Main app
st.title("🏥 Welcome to LinQMD's Health Assistant")

# Info header
with st.expander("ℹ️ About this Medical Assistant"):
    st.markdown("""
    This AI assistant helps collect medical information before your doctor's consultation.
    
    **Important:**
    - This is NOT a medical consultation
    - The AI cannot diagnose or provide medical advice
    - For emergencies, call emergency services immediately
    
    **How to use:**
    1. Describe your symptoms in the chat
    2. Answer the AI's questions
    3. Say "that's all" when finished
    4. Get your summary and doctor gets clinical details
    """)

# Create two columns
patient_col, doctor_col = st.columns([1, 1])

# PATIENT CHAT (Left side)
with patient_col:
    st.header("💬 Patient Consultation")
    
    # Create a container for messages
    message_container = st.container()
    
    # Display all messages
    with message_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    
    # Show patient summary if available
    if st.session_state.patient_summary:
        st.success("📋 Your Summary:")
        st.info(st.session_state.patient_summary)
    
    # Chat input at the bottom
    user_input = st.chat_input("Describe your symptoms...")
    
    if user_input:
        # Add user message to state and display
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get AI response
        assistant_response = call_openai_standard(st.session_state.messages)
        
        if assistant_response:
            # Extract summaries if present
            patient_sum, clinical_sum = extract_summaries(assistant_response)
            if patient_sum and clinical_sum:
                st.session_state.patient_summary = patient_sum
                st.session_state.clinical_summary = clinical_sum
            
            # Clean response for display
            display_response = clean_response_for_display(assistant_response)
            
            # Add assistant message to state
            st.session_state.messages.append({"role": "assistant", "content": display_response})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "I apologize, but I couldn't process your message. Please try again."})
        
        # Rerun to display new messages
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
                "conversation": st.session_state.messages
            }
            st.download_button(
                "💾 Export JSON",
                json.dumps(export_data, indent=2),
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
    
    # Session info
    st.divider()
    st.subheader("📊 Session Info")
    st.info(f"Started: {datetime.now().strftime('%I:%M %p')}")
    
    # Check configuration
    st.divider()
    st.subheader("✅ Status Check")
    api_status = "✅ Found" if get_api_key() else "❌ Missing"
    st.write(f"API Key: {api_status}")
    
    # Reset button
    st.divider()
    if st.button("🔄 New Consultation", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
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
    st.caption("⚡ Powered by AI")

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        background-color: #000000;
        border-radius: 10px;
        margin: 5px 0;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)
