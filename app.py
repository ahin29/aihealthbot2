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
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

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
            st.error("""
            ❌ **OpenAI API Key not found!**
            
            Please add your OpenAI API key to Streamlit secrets:
            `OPENAI_API_KEY = "sk-your-actual-api-key"`
            """)
            st.stop()

@st.cache_resource
def get_openai_client():
    """Initialize OpenAI client"""
    api_key = get_api_key()
    return OpenAI(api_key=api_key)

def build_conversation_text():
    """Build conversation history as a single text string"""
    conversation = ""
    for msg in st.session_state.messages:
        role = "Patient" if msg["role"] == "user" else "Assistant"
        conversation += f"{role}: {msg['content']}\n\n"
    return conversation.strip()

def call_openai_with_prompt_id(user_message):
    """Call OpenAI API using prompt ID and responses.create method"""
    try:
        client = get_openai_client()
        
        # Build the conversation history
        conversation_history = build_conversation_text()
        
        # Prepare the input with the new user message
        if conversation_history:
            full_input = f"{conversation_history}\n\nPatient: {user_message}"
        else:
            full_input = f"Patient: {user_message}"
        
        # Debug info
        with st.sidebar:
            with st.expander("🐛 Debug Info", expanded=False):
                st.write(f"Prompt ID: {PROMPT_ID}")
                st.write(f"Version: {PROMPT_VERSION}")
                st.write(f"Messages: {len(st.session_state.messages)}")
                st.write("Using responses.create method")
        
        # Call OpenAI using the prompt ID
        response = client.responses.create(
            prompt={
                "id": PROMPT_ID,
                "version": PROMPT_VERSION
            },
            input=[{
                "type": "text",
                "text": full_input
            }],
            text={
                "format": {
                    "type": "text"
                }
            },
            reasoning={},
            max_output_tokens=2048,
            store=True
        )
        
        # Extract the response text
        if hasattr(response, 'text') and hasattr(response.text, 'value'):
            return response.text.value
        elif hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            # Try to extract text from response object
            response_text = str(response)
            st.write("Debug - Response structure:", response)
            return response_text
            
    except AttributeError as e:
        st.error(f"The responses.create method is not available. Error: {str(e)}")
        st.info("Falling back to standard chat completion...")
        return call_openai_standard(user_message)
        
    except Exception as e:
        st.error(f"❌ OpenAI API Error: {str(e)}")
        with st.expander("Error Details"):
            st.write(f"Error type: {type(e).__name__}")
            st.write(f"Error message: {str(e)}")
        return None

def call_openai_standard(user_message):
    """Fallback to standard chat completion if prompt ID method fails"""
    try:
        client = get_openai_client()
        
        # Build messages array
        messages = [{"role": "system", "content": "You are a medical assistant. Generate summaries with delimiters ---BEGIN_PATIENT_SUMMARY--- and ---BEGIN_CLINICAL_SUMMARY_CONFIDENTIAL---"}]
        messages.extend(st.session_state.messages)
        messages.append({"role": "user", "content": user_message})
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.3,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Standard API also failed: {str(e)}")
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
        # Add user message to display
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("AI is thinking..."):
                # Call OpenAI with prompt ID
                full_response = call_openai_with_prompt_id(prompt)
                
                if full_response:
                    # Extract summaries if present
                    patient_sum, clinical_sum = extract_summaries(full_response)
                    if patient_sum and clinical_sum:
                        st.session_state.patient_summary = patient_sum
                        st.session_state.clinical_summary = clinical_sum
                    
                    # Clean response for display
                    display_response = clean_response_for_display(full_response)
                    
                    # Extract just the assistant's response
                    # Look for the last "Assistant:" in the response
                    if "Assistant:" in full_response:
                        parts = full_response.split("Assistant:")
                        if len(parts) > 1:
                            display_response = parts[-1].strip()
                            display_response = clean_response_for_display(display_response)
                    
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
                "conversation": st.session_state.messages,
                "prompt_id": PROMPT_ID
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
            - Using Prompt ID method for responses
            """)

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Controls")
    
    # Session info
    st.divider()
    st.subheader("📊 Session Info")
    st.info(f"Started: {datetime.now().strftime('%I:%M %p')}")
    
    # Show prompt info
    with st.expander("📝 Prompt Configuration"):
        st.code(f"ID: {PROMPT_ID[:20]}...")
        st.code(f"Version: {PROMPT_VERSION}")
        st.caption("Using responses.create API")
    
    # Status check
    st.divider()
    st.subheader("✅ Status Check")
    api_status = "✅ Found" if get_api_key() else "❌ Missing"
    st.write(f"API Key: {api_status}")
    st.write(f"Method: responses.create")
    
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
    st.caption("🏥 LinQMD Health Assistant")
    st.caption("⚡ Powered by AI")

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
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)
