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
            
            Please add your OpenAI API key to Streamlit secrets:
            
            **In Streamlit Cloud:**
            1. Go to your app settings
            2. Navigate to 'Secrets' section
            3. Add: `OPENAI_API_KEY = "sk-your-actual-api-key"`
            """)
            st.stop()

@st.cache_data
def get_system_prompt():
    """Get system prompt from secrets"""
    try:
        return st.secrets["MEDICAL_PROMPT"]
    except:
        st.error("""
        ❌ **Medical prompt not found in secrets!**
        
        Please add your medical prompt to Streamlit secrets:
        
        1. Copy your complete prompt from OpenAI Playground
           (Prompt ID: pmpt_68906b8c98b08197884e6957b551a55a0940c6dfad2636d6)
        
        2. In Streamlit Cloud secrets, add:
        ```
        MEDICAL_PROMPT = '''
        [Paste your entire prompt here]
        '''
        ```
        
        3. Make sure your prompt includes Section J with these delimiters:
           - ---BEGIN_PATIENT_SUMMARY---
           - ---END_PATIENT_SUMMARY---
           - ---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL---
           - ---END_CLINICAL_SUMMARY_CONFIDENTIAL---
        """)
        st.stop()

@st.cache_resource
def get_openai_client():
    """Initialize OpenAI client"""
    api_key = get_api_key()
    return OpenAI(api_key=api_key)

def call_openai(messages):
    """Call OpenAI API using standard chat completion"""
    try:
        client = get_openai_client()
        system_prompt = get_system_prompt()
        model = st.session_state.get("model", "gpt-4")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                *messages
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        error_msg = str(e)
        st.error(f"❌ OpenAI API Error: {error_msg}")
        
        # Provide specific guidance
        if "api_key" in error_msg.lower():
            st.error("Please check your API key in Streamlit secrets.")
        elif "model" in error_msg.lower():
            st.error("Try switching to 'gpt-3.5-turbo' in the sidebar.")
        elif "rate" in error_msg.lower():
            st.error("Rate limit exceeded. Please wait and try again.")
        
        # Show debug info
        with st.expander("🐛 Debug Information"):
            st.write(f"Model: {model}")
            st.write(f"API Key: {'✅ Found' if get_api_key() else '❌ Missing'}")
            st.write(f"Prompt: {'✅ Found' if get_system_prompt() else '❌ Missing'}")
            st.write(f"Message count: {len(messages)}")
        
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
        with st.chat_message("assistant"):
            with st.spinner("AI is thinking..."):
                full_response = call_openai(st.session_state.messages)
                
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
                    st.write(display_response)
                else:
                    st.error("Failed to get response. Check error message above.")
        
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
    
    # Model selection
    model = st.selectbox(
        "AI Model",
        ["gpt-4", "gpt-3.5-turbo"],
        index=0,
        help="GPT-4 is more accurate, GPT-3.5 is faster/cheaper"
    )
    st.session_state["model"] = model
    
    # Session info
    st.divider()
    st.subheader("📊 Session Info")
    st.info(f"Started: {datetime.now().strftime('%I:%M %p')}")
    
    # Show prompt ID reference
    with st.expander("📝 Prompt Reference"):
        st.code("pmpt_68906b8c98b08197884e6957b551a55a0940c6dfad2636d6")
        st.caption("Your OpenAI Playground prompt ID")
    
    # Status check
    st.divider()
    st.subheader("✅ Status Check")
    
    # Check configuration
    api_status = "✅ Found" if get_api_key() else "❌ Missing"
    st.write(f"API Key: {api_status}")
    
    try:
        prompt_status = "✅ Found" if get_system_prompt() else "❌ Missing"
    except:
        prompt_status = "❌ Missing"
    st.write(f"Medical Prompt: {prompt_status}")
    
    # Reset button
    st.divider()
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
    st.caption("🏥 LinQMD Health Assistant")
    st.caption("⚡ Powered by LinqMD")

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 10px;
        margin: 5px 0;
    }
    .stAlert {
        border-radius: 10px;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

