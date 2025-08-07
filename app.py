import streamlit as st
import openai
from openai import OpenAI
import re

# Set up the page with wide layout for two columns
st.set_page_config(page_title="Medical Intake Assistant", page_icon="🏥", layout="wide")
st.title("🏥 Medical Intake Assistant")

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "patient_summary" not in st.session_state:
    st.session_state.patient_summary = ""
if "clinical_summary" not in st.session_state:
    st.session_state.clinical_summary = ""

# Function to extract summaries from text
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

# Create two columns
col1, col2 = st.columns([1.2, 1])

# Left Column - Patient Chat
with col1:
    st.subheader("💬 Patient Consultation")
    
    # Create a container for chat messages
    chat_container = st.container(height=500)
    
    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                # For assistant messages, only show the display text (not summaries)
                if message["role"] == "assistant":
                    display_text, _, _ = extract_summaries(message["content"])
                    st.markdown(display_text)
                else:
                    st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Describe your symptoms (type 'done' when finished)..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # Generate bot response
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    try:
                        client = get_openai_client()
                        
                        # Build conversation history for the prompt
                        conversation_context = ""
                        for msg in st.session_state.messages[:-1]:  # Exclude the last message we just added
                            if msg["role"] == "user":
                                conversation_context += f"Patient: {msg['content']}\n"
                            else:
                                conversation_context += f"Assistant: {msg['content']}\n"
                        
                        # Add the current message
                        conversation_context += f"Patient: {prompt}\n"
                        
                        # Using your OpenAI Playground prompt with full conversation context
                        response = client.responses.create(
                            prompt={
                                "id": "pmpt_6890c2093c388190a66ef880c473a00203ff24f87032e5f6",
                                "version": "4"
                            },
                            # Pass the full conversation context
                            input=conversation_context
                        )
                        
                        # Extract the bot response from the output array
                        if hasattr(response, 'output') and len(response.output) > 0:
                            output_message = response.output[0]
                            if hasattr(output_message, 'content') and len(output_message.content) > 0:
                                content_item = output_message.content[0]
                                if hasattr(content_item, 'text'):
                                    bot_response = content_item.text
                                else:
                                    bot_response = str(content_item)
                            else:
                                bot_response = "No content in output message"
                        else:
                            bot_response = "No output in response"
                        
                        # Extract summaries if present
                        display_text, patient_sum, clinical_sum = extract_summaries(bot_response)
                        
                        # Display only the conversation part (not summaries)
                        st.markdown(display_text)
                        
                        # Update summaries in session state if found
                        if patient_sum:
                            st.session_state.patient_summary = patient_sum
                        if clinical_sum:
                            st.session_state.clinical_summary = clinical_sum
                        
                        # Add full bot response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": bot_response})
                        
                        # Rerun to update the right column
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.info("Please check your API key and try again.")
    
    # Show patient summary if available
    if st.session_state.patient_summary:
        st.markdown("---")
        st.subheader("📋 Your Summary")
        with st.container():
            st.info(st.session_state.patient_summary)

# Right Column - Clinical Summary
with col2:
    st.subheader("👨‍⚕️ Clinical Summary (Doctor's View)")
    
    if st.session_state.clinical_summary:
        # Add styling for clinical summary
        st.markdown("""
        <style>
        .clinical-summary {
            background-color: #0000ff;
            border: 2px solid #ffc9c9;
            border-radius: 10px;
            padding: 20px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="clinical-summary">', unsafe_allow_html=True)
        st.markdown(st.session_state.clinical_summary)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Clinical summary will appear here after the consultation is complete.")
        
        with st.expander("ℹ️ What will be included"):
            st.markdown("""
            - **Patient Demographics** and chief complaint
            - **Detailed Symptom Analysis** with timeline
            - **Medical History** and current medications
            - **Red Flags** and emergency indicators
            - **Pattern Recognition** insights
            - **Examination Recommendations**
            - **Key Differentials** to consider
            """)

# Sidebar with controls
with st.sidebar:
    st.header("⚙️ Controls")
    
    if st.button("🔄 Start New Consultation", type="primary"):
        st.session_state.messages = []
        st.session_state.patient_summary = ""
        st.session_state.clinical_summary = ""
        st.rerun()
    
    st.markdown("---")
    
    st.header("📖 Instructions")
    st.write("1. Patient describes symptoms in the chat")
    st.write("2. Assistant asks follow-up questions")
    st.write("3. Patient types 'done' when finished")
    st.write("4. Summaries appear automatically")
    
    st.markdown("---")
    
    # Show consultation status
    if st.session_state.clinical_summary:
        st.success("✅ Consultation Complete")
    else:
        st.info("🔄 Consultation in Progress")

