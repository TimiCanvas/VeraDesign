import streamlit as st
import requests
import os
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
GPT_DEPLOYMENT = os.getenv("GPT_DEPLOYMENT")
DALLE_DEPLOYMENT = os.getenv("DALLE_DEPLOYMENT")

# GPT-4o prompt refiner with context
def refine_prompt_with_context(chat_history: list, user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": "You are a fashion design assistant. Refine user descriptions into clear, vivid product photography prompts for DALL·E 3."}
    ]

    # Add previous conversation to context
    for role, content in chat_history:
        if role == "User":
            messages.append({"role": "user", "content": content})
        elif role == "Refined":
            messages.append({"role": "assistant", "content": content})

    # Add the current user prompt
    messages.append({"role": "user", "content": user_prompt})

    # API call to refine the prompt
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{GPT_DEPLOYMENT}/chat/completions?api-version=2024-02-01"
    headers = {
        "api-key": AZURE_OPENAI_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "messages": messages,
        "max_tokens": 200
    }
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

# DALL·E 3 image generator
def generate_image_with_dalle(prompt: str, size="1024x1024"):
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DALLE_DEPLOYMENT}/images/generations?api-version=2024-02-01"
    headers = {
        "api-key": AZURE_OPENAI_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "size": size,
        "n": 1
    }

    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()

    if "data" not in data or not data["data"]:
        st.error(f"Image generation failed. Full response: {data}")
        return None

    if "b64_json" in data["data"][0]:
        b64_img = data["data"][0]["b64_json"]
        return base64.b64decode(b64_img)

    if "url" in data["data"][0]:
        return data["data"][0]["url"]

    st.error(f"Unexpected image format from API: {data}")
    return None

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "refined_prompt" not in st.session_state:
    st.session_state.refined_prompt = ""

# Streamlit UI
st.set_page_config(page_title="VeraDesign AI Fashion", page_icon="🧵")
st.title("🧵 VeraDesign AI Fashion")
st.write("Describe any apparel design in natural language and see it instantly.")

user_input = st.text_area("Describe your apparel idea:", height=100)
size = st.selectbox(
    "Image size",
    ["1024x1024", "1024x1792", "1792x1024"]
)

# Step 1: Refine the user prompt
if st.button("Refine Prompt"):
    if not user_input.strip():
        st.error("Please enter a description.")
    else:
        with st.spinner("Refining your prompt..."):
            refined = refine_prompt_with_context(st.session_state.chat_history, user_input)
            st.session_state.refined_prompt = refined
            st.session_state.chat_history.append(("User", user_input))
            st.session_state.chat_history.append(("Refined", refined))

# Step 2: Review, Edit + Approve Refined Prompt
if st.session_state.refined_prompt:
    st.subheader("Review and Edit the Refined Prompt")
    edited_prompt = st.text_area("Refined Prompt", value=st.session_state.refined_prompt, height=100)
    
    # Step 3: Generate Image with approved/refined prompt
    if st.button("Generate Image"):
        with st.spinner("Generating image..."):
            img_data = generate_image_with_dalle(edited_prompt, size=size)
            st.session_state.chat_history.append(("Final Prompt", edited_prompt))
            st.session_state.chat_history.append(("Image Generated", "✅"))

            if img_data:
                if isinstance(img_data, bytes):
                    st.image(img_data, caption="Generated Apparel Design")
                elif isinstance(img_data, str):
                    st.image(img_data, caption="Generated Apparel Design (from URL)")

# Step 4: Edit Previous Prompts + Re-generate Image
if st.session_state.chat_history:
    st.subheader("Conversation History")
    for i, (role, content) in enumerate(st.session_state.chat_history):
        if role == "Final Prompt":
            st.markdown(f"**{role}:**")
            edited = st.text_area(f"Edit Prompt #{i}", value=content, key=f"edit_{i}")
            if st.button(f"Re-generate Image #{i}"):
                with st.spinner(f"Regenerating image #{i}..."):
                    img = generate_image_with_dalle(edited, size=size)
                    if img:
                        st.image(img, caption=f"Updated Design #{i}")
                    # Add edited prompt to history
                    st.session_state.chat_history.append(("Re-edited Prompt", edited))
                    st.session_state.chat_history.append(("Re-generated Image", "✅"))

# Display entire chat history for transparency
if st.session_state.chat_history:
    st.subheader("Full Chat History (this session)")
    for role, content in st.session_state.chat_history:
        st.markdown(f"**{role}:** {content}")
