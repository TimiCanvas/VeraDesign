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

    for entry in chat_history:
        if entry["role"] == "user":
            messages.append({"role": "user", "content": entry["content"]})
        elif entry["role"] == "assistant":
            messages.append({"role": "assistant", "content": entry["content"]})

    messages.append({"role": "user", "content": user_prompt})

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

# Image generation
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
        return base64.b64decode(data["data"][0]["b64_json"])

    if "url" in data["data"][0]:
        return data["data"][0]["url"]

    st.error(f"Unexpected image format from API: {data}")
    return None

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_refined_prompt" not in st.session_state:
    st.session_state.pending_refined_prompt = None

# Set page
st.set_page_config(page_title="VeraDesign AI Fashion", page_icon="🧵")
st.title("🧵 VeraDesign AI Fashion Assistant")

# Display conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "image" in msg:
            st.image(msg["image"], caption="Generated Design")

# Input area
with st.chat_message("user"):
    user_input = st.text_area("Describe your fashion design:", height=100, key="user_prompt")
    size = st.selectbox("Select image size", ["1024x1024", "1024x1792", "1792x1024"], key="img_size")
    col1, col2 = st.columns([1, 1])
    send_clicked = col1.button("Refine Prompt")
    generate_clicked = col2.button("Generate Image")

# Step 1: Refine the prompt
if send_clicked and user_input.strip():
    with st.spinner("Refining your prompt..."):
        refined = refine_prompt_with_context(st.session_state.messages, user_input)
        st.session_state.pending_refined_prompt = refined
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": f"Here’s a refined version of your idea:\n\n```{refined}```\n\nEdit it if you like, then click **Generate Image**."})
        st.rerun()


# Step 2: Show editable prompt
if st.session_state.pending_refined_prompt:
    with st.chat_message("user"):
        edited_prompt = st.text_area("Edit the refined prompt:", value=st.session_state.pending_refined_prompt, key="edited_prompt")

# Step 3: Generate image
if generate_clicked and st.session_state.pending_refined_prompt:
    edited_prompt = st.session_state.get("edited_prompt", st.session_state.pending_refined_prompt)
    with st.spinner("Generating image..."):
        img = generate_image_with_dalle(edited_prompt, size=st.session_state.get("img_size", "1024x1024"))
        if img:
            st.session_state.messages.append({"role": "user", "content": f"Generate image for:\n\n```{edited_prompt}```"})
            st.session_state.messages.append({"role": "assistant", "content": "Here's your generated fashion design 👇", "image": img})
            st.session_state.pending_refined_prompt = None
            st.rerun()

