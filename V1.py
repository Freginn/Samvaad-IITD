# SamvaadGPT Minimal Upload Version - IIT Delhi Memory Bot

import os
import io
import fitz  # PyMuPDF
import streamlit as st
import pytesseract
import openai
from PIL import Image
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

# Set OpenAI Key
openai.api_key = st.sidebar.text_input("🔑 Enter OpenAI API Key", type="password")

# Page Title
st.set_page_config(page_title="SamvaadGPT - Institutional Memory")
st.title("🧠 SamvaadGPT | Institutional Memory Bot")

# Upload Interface
uploaded_files = st.file_uploader("📂 Upload PDFs related to IIT Delhi Committees or CSR", type="pdf", accept_multiple_files=True)

# Store all text and metadata
document_chunks = []
metadata = []

# Extract text from PDFs
def extract_text_with_source(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    combined_text = ""
    for i, page in enumerate(doc):
        try:
            text = page.get_text().strip()
            if not text:
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img, config='--psm 6')
        except:
            text = ""
        combined_text += f"[Page {i+1}]: {text}\n"
    return combined_text

# Process uploaded files
if uploaded_files and openai.api_key:
    with st.spinner("🔍 Reading and indexing your documents..."):
        for file in uploaded_files:
            text = extract_text_with_source(file)
            for i in range(0, len(text), 800):
                chunk = text[i:i+800]
                document_chunks.append(chunk)
                metadata.append(file.name)

        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(document_chunks)
        model = NearestNeighbors(n_neighbors=3, metric="cosine").fit(X)

        st.success("✅ Files indexed. Ask your question below.")
        query = st.text_input("💬 Ask a question")

        if query:
            with st.spinner("🤖 Thinking..."):
                q_vec = vectorizer.transform([query])
                distances, indices = model.kneighbors(q_vec)
                sources = []
                context = ""
                for idx in indices[0]:
                    context += f"\n--- From {metadata[idx]} ---\n{document_chunks[idx]}"
                    sources.append(metadata[idx])

                prompt = f"Answer the following question using only the provided context:\n{context}\n\nQuestion: {query}\nAnswer:"
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                answer = response["choices"][0]["message"]["content"]
                st.markdown(f"**🧾 Answer:** {answer}")
                st.markdown(f"📌 **Sources Cited:** `{', '.join(set(sources))}`")

elif not openai.api_key:
    st.warning("🔐 Please enter your OpenAI API Key in the sidebar.")

