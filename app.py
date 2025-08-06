import streamlit as st
import openai
from openai import OpenAI

# Set up the page
st.set_page_config(page_title="My ChatBot", page_icon="🤖")
st.title("LinqMD Health Assistant")

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                client = get_openai_client()
                
                # Build conversation history for the prompt
                # Convert our chat history to the format the API expects
                conversation_context = ""
                for msg in st.session_state.messages:
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
                st.markdown(bot_response)
                
                # Add bot response to chat history
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Please check your API key and try again.")

# Sidebar with instructions
with st.sidebar:
    st.header("Instructions")
    st.write("1. Type your message in the chat box")
    st.write("2. Press Enter to send")
    st.write("3. Wait for the bot to respond")
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
