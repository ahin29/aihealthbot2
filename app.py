import streamlit as st
import os

st.title("🔍 Debug API Key Configuration")

st.header("1. Checking Streamlit Secrets")
try:
    # Check if secrets exist
    if hasattr(st, 'secrets'):
        st.success("✅ Streamlit secrets object exists")
        
        # List all secret keys (not values)
        st.write("Available secret keys:")
        for key in st.secrets:
            st.write(f"- {key}")
        
        # Check specific key
        if "OPENAI_API_KEY" in st.secrets:
            st.success("✅ OPENAI_API_KEY found in secrets")
            key_value = st.secrets["OPENAI_API_KEY"]
            st.write(f"Key starts with: {key_value[:7]}...")
            st.write(f"Key length: {len(key_value)} characters")
        else:
            st.error("❌ OPENAI_API_KEY not found in secrets")
            st.write("Available keys:", list(st.secrets.keys()) if st.secrets else "None")
    else:
        st.error("❌ No secrets object found")
except Exception as e:
    st.error(f"Error accessing secrets: {str(e)}")

st.header("2. Checking Environment Variables")
env_key = os.environ.get("OPENAI_API_KEY")
if env_key:
    st.success(f"✅ Found in environment: {env_key[:7]}...")
else:
    st.warning("❌ Not found in environment variables")

st.header("3. Common Issues")
st.markdown("""
**Check these common problems:**
1. **Case sensitivity**: Must be `OPENAI_API_KEY` (all caps)
2. **Extra quotes**: Use only one set of double quotes
3. **Spaces**: No spaces before/after the key
4. **App restart**: Restart app after adding secrets
5. **Save secrets**: Make sure to click Save after adding

**Correct format:**
```toml
OPENAI_API_KEY = "sk-..."
```
""")

st.header("4. Next Steps")
st.markdown("""
1. Go to **App settings** → **Secrets**
2. Verify the format matches exactly
3. Click **Save**
4. **Reboot app** from the menu (⋮)
5. Return to the main app
""")
