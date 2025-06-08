# app.py
import os, io, gdown, fitz, streamlit as st, pytesseract, mimetypes, openai
from PIL import Image
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

# Hardcoded Google Drive folder
GDRIVE_FOLDER = "https://drive.google.com/drive/folders/1cAy-I4nOzFQtw_KuudeB4Xe8AxIHlzjg"

st.set_page_config(page_title="SamvaadGPT - IIT Delhi", layout="wide")
st.title("🧠 SamvaadGPT | IIT Delhi Institutional Memory Assistant")

openai.api_key = st.sidebar.text_input("🔑 OpenAI API Key", type="password")
if openai.api_key:
    with st.spinner("📥 Downloading and Processing Files..."):
        def extract_file_id(url):
            if "id=" in url: return url.split("id=")[1].split("&")[0]
            if "/d/" in url: return url.split("/d/")[1].split("/")[0]
            if "folders/" in url: return url.split("folders/")[1].split("/")[0]
        fid = extract_file_id(GDRIVE_FOLDER)
        files = gdown.download_folder(id=fid, quiet=True, use_cookies=False)
        if not files:
            st.error("❌ No PDF files downloaded.")
        else:
            all_text = ""
            for f in files:
                if mimetypes.guess_type(f)[0] == 'application/pdf':
                    doc = fitz.open(f)
                    for p in doc:
                        pix = p.get_pixmap()
                        img = Image.open(io.BytesIO(pix.tobytes("png")))
                        all_text += pytesseract.image_to_string(img, config='--psm 6') + "\n"
            if not all_text:
                st.warning("⚠️ No text extracted.")
            else:
                vec = TfidfVectorizer().fit_transform([all_text[i:i+500] for i in range(0, len(all_text), 500)])
                model = NearestNeighbors(n_neighbors=3, metric="cosine").fit(vec)
                query = st.text_input("💬 Ask a question about these documents")
                if query:
                    qv = TfidfVectorizer().fit([all_text]).transform([query])
                    d, idx = model.kneighbors(qv)
                    context = all_text[idx[0][0]*500:(idx[0][0]+1)*500]
                    resp = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role":"user", "content":
                            f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"}]
                    )
                    st.markdown("**🧾 Answer:** " + resp['choices'][0]['message']['content'])
else:
    st.info("🔑 Please enter your OpenAI API Key above.")
