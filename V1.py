# 📦 SamvaadGPT Prototype Guide (Streamlit Web App + Google Drive Integration)
# 🏛️ Institution: Indian Institute of Technology Delhi
# 🧠 Project: SamvaadGPT - Institutional Memory Assistant (Web App)

# 1. Install Required Packages (Run this locally)
# pip install streamlit pymupdf==1.22.5 pytesseract openai pillow scikit-learn gdown

import os
import io
import gdown
import fitz  # PyMuPDF
import streamlit as st
import pytesseract
import mimetypes
import openai
from PIL import Image
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

# --- Helper Functions ---
def extract_file_id(gdrive_url):
    if "id=" in gdrive_url:
        return gdrive_url.split("id=")[1].split("&")[0]
    elif "/d/" in gdrive_url:
        return gdrive_url.split("/d/")[1].split("/")[0]
    elif "folders/" in gdrive_url:
        return gdrive_url.split("folders/")[1].split("/")[0]
    else:
        st.error("❌ Invalid Google Drive link format")
        return None

def download_from_gdrive(url_or_folder):
    file_id = extract_file_id(url_or_folder)
    if not file_id:
        return []
    try:
        if "file" in url_or_folder or "/d/" in url_or_folder or "id=" in url_or_folder:
            output_path = "downloaded_file.pdf"
            gdown.download(f"https://drive.google.com/uc?id={file_id}", output_path, quiet=False)
            return [output_path]
        else:
            return gdown.download_folder(id=file_id, quiet=False, use_cookies=False)
    except Exception as e:
        st.error(f"❌ Error downloading: {e}")
        return []

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img, config='--psm 6')
        full_text += text + "\n"
    return full_text

def create_vector_db(text):
    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(chunks)
    nn_model = NearestNeighbors(n_neighbors=5, metric='cosine')
    nn_model.fit(vectors)
    return nn_model, chunks, vectorizer

def answer_query(nn_model, chunks, vectorizer, query):
    query_vec = vectorizer.transform([query])
    distances, indices = nn_model.kneighbors(query_vec)
    context = "\n".join([chunks[i] for i in indices[0]])
    prompt = f"Use the following context to answer the question:\n{context}\n\nQuestion: {query}\nAnswer:"
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"].strip()

# --- Streamlit Web Interface ---
st.set_page_config(page_title="SamvaadGPT - IIT Delhi", layout="wide")
st.title("🧠 SamvaadGPT | IIT Delhi Institutional Memory Assistant")

with st.sidebar:
    st.header("📂 Upload Source")
    gdrive_url = st.text_input("🔗 Google Drive Link (file or folder)")
    openai.api_key = st.text_input("🔑 OpenAI API Key", type="password")

if gdrive_url and openai.api_key:
    with st.spinner("📥 Downloading and Processing Files..."):
        files = download_from_gdrive(gdrive_url)
        if not files:
            st.error("❌ No files downloaded.")
        else:
            all_text = ""
            for f in files:
                if mimetypes.guess_type(f)[0] == 'application/pdf':
                    all_text += extract_text_from_pdf(f) + "\n"
            if not all_text:
                st.warning("⚠️ No text extracted from PDFs.")
            else:
                nn_model, chunks, vectorizer = create_vector_db(all_text)
                st.success("✅ Ready to take your questions!")
                query = st.text_input("💬 Ask a question about the documents")
                if query:
                    with st.spinner("🔍 Generating answer..."):
                        response = answer_query(nn_model, chunks, vectorizer, query)
                        st.markdown(f"**🧾 Answer:** {response}")
else:
    st.info("Please provide a valid Google Drive link and OpenAI key to continue.")
