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

# GPT-4o prompt refiner
def refine_prompt(user_prompt: str) -> str:
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{GPT_DEPLOYMENT}/chat/completions?api-version=2024-02-01"
    headers = {
        "api-key": AZURE_OPENAI_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You are a fashion design assistant. Refine user descriptions into clear, vivid product photography prompts for DALL·E 3."},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 200
    }
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

# DALL·E 3 image generator (Azure version)
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

    # Case 1: Base64 image
    if "b64_json" in data["data"][0]:
        b64_img = data["data"][0]["b64_json"]
        return base64.b64decode(b64_img)

    # Case 2: Image URL
    if "url" in data["data"][0]:
        return data["data"][0]["url"]

    st.error(f"Unexpected image format from API: {data}")
    return None

# Streamlit UI
st.set_page_config(page_title="VeraDesign AI Fashion", page_icon="🧵")
st.title("🧵 VeraDesign AI Fashion")
st.write("Describe any apparel design in natural language and see it instantly.")

user_input = st.text_area("Describe your apparel idea:", height=100)
size = st.selectbox(
    "Image size",
    ["1024x1024", "1024x1792", "1792x1024"]
)

if st.button("Generate Design"):
    if not user_input.strip():
        st.error("Please enter a description.")
    else:
        with st.spinner("Refining your prompt..."):
            refined = refine_prompt(user_input)
        st.success(f"Refined Prompt: {refined}")

        with st.spinner("Generating image..."):
            img_data = generate_image_with_dalle(refined, size=size)

            if img_data:
                if isinstance(img_data, bytes):
                    st.image(img_data, caption="Generated Apparel Design")
                elif isinstance(img_data, str):
                    st.image(img_data, caption="Generated Apparel Design (from URL)")