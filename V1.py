# 📦 SamvaadGPT - Streamlit Cloud Compatible Version
# 🏩 Institution: Indian Institute of Technology Delhi
# 🧠 Project: Stream-based Document Processing from Google Drive

import os
import io
import requests
import streamlit as st
from openai import OpenAI  # Updated import for OpenAI v1.x+
import hashlib
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import logging
from datetime import datetime
import json
import re

# Try to import PDF processing libraries (fallback if not available)
try:
    import pypdf2 as PyPDF2
    PDF_READER = "pypdf2"
except ImportError:
    try:
        import PyPDF2
        PDF_READER = "PyPDF2"
    except ImportError:
        try:
            import pdfplumber
            PDF_READER = "pdfplumber"
        except ImportError:
            PDF_READER = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
class Config:
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    MAX_CONTEXT_LENGTH = 3000
    CACHE_DIR = "cache"
    GOOGLE_DRIVE_API_BASE = "https://drive.google.com/uc?export=download&id="
    GOOGLE_DRIVE_VIEWER_BASE = "https://drive.google.com/file/d/{}/view"

# --- Direct Online Processing Functions ---
def extract_file_id(gdrive_url):
    """Extract file ID from Google Drive URL"""
    try:
        if not gdrive_url or not isinstance(gdrive_url, str):
            return None
            
        gdrive_url = gdrive_url.strip()
        
        # Different Google Drive URL formats
        patterns = [
            r'/d/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
            r'folders/([a-zA-Z0-9-_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, gdrive_url)
            if match:
                return match.group(1)
        
        logger.error(f"Could not extract file ID from: {gdrive_url}")
        return None
    except Exception as e:
        logger.error(f"Error extracting file ID: {e}")
        return None

def get_direct_download_url(file_id):
    """Convert file ID to direct download URL"""
    return f"https://drive.google.com/uc?export=download&id={file_id}"

def extract_text_from_pdf_pypdf2(pdf_content):
    """Extract text using PyPDF2"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_content)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {e}")
        return ""

def extract_text_from_pdf_pdfplumber(pdf_content):
    """Extract text using pdfplumber"""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_content) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"pdfplumber extraction failed: {e}")
        return ""

def stream_pdf_from_url(url, progress_callback=None):
    """Stream PDF directly from URL and extract text without downloading"""
    try:
        if progress_callback:
            progress_callback("🌐 Connecting to Google Drive...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Stream the file
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        # Check if it's actually a PDF
        content_type = response.headers.get('content-type', '')
        if 'application/pdf' not in content_type and 'application/octet-stream' not in content_type:
            # Sometimes Google Drive returns HTML for large files, try the confirmation link
            if 'text/html' in content_type:
                return handle_large_file_download(url, headers, progress_callback)
        
        if progress_callback:
            progress_callback("📄 Streaming PDF content...")
        
        # Read the PDF content into memory
        pdf_content = io.BytesIO()
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                pdf_content.write(chunk)
                downloaded += len(chunk)
                if total_size > 0 and progress_callback:
                    progress = min(50 + (downloaded / total_size) * 30, 80)
                    progress_callback(f"📥 Streaming: {downloaded}/{total_size} bytes")
        
        pdf_content.seek(0)
        return extract_text_from_pdf_stream(pdf_content, progress_callback)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error streaming PDF: {e}")
        raise Exception(f"Failed to access file online: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing PDF stream: {e}")
        raise Exception(f"Failed to process PDF: {str(e)}")

def handle_large_file_download(url, headers, progress_callback):
    """Handle large files that require confirmation"""
    try:
        if progress_callback:
            progress_callback("🔄 Handling large file access...")
        
        # Get the initial response to find the confirmation link
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Look for confirmation link in the HTML
        import re
        confirm_pattern = r'href="([^"]*&confirm=[^"]*)"'
        match = re.search(confirm_pattern, response.text)
        
        if match:
            confirm_url = match.group(1)
            confirm_url = confirm_url.replace('&amp;', '&')
            
            # Try the confirmation URL
            confirm_response = requests.get(f"https://drive.google.com{confirm_url}", headers=headers, stream=True)
            confirm_response.raise_for_status()
            
            pdf_content = io.BytesIO()
            for chunk in confirm_response.iter_content(chunk_size=8192):
                if chunk:
                    pdf_content.write(chunk)
            
            pdf_content.seek(0)
            return extract_text_from_pdf_stream(pdf_content, progress_callback)
        else:
            raise Exception("Could not find confirmation link for large file")
            
    except Exception as e:
        logger.error(f"Error handling large file: {e}")
        raise Exception(f"Failed to access large file: {str(e)}")

def extract_text_from_pdf_stream(pdf_stream, progress_callback=None):
    """Extract text from PDF stream using available PDF library"""
    try:
        if progress_callback:
            progress_callback("📖 Opening PDF document...")
        
        if not PDF_READER:
            raise Exception("No PDF processing library available. Please install PyPDF2 or pdfplumber.")
        
        if progress_callback:
            progress_callback(f"📄 Processing PDF with {PDF_READER}...")
        
        # Try different PDF readers
        if PDF_READER in ["pypdf2", "PyPDF2"]:
            text = extract_text_from_pdf_pypdf2(pdf_stream)
        elif PDF_READER == "pdfplumber":
            text = extract_text_from_pdf_pdfplumber(pdf_stream)
        else:
            raise Exception("No supported PDF reader available")
        
        if progress_callback:
            progress_callback("✅ Text extraction completed!")
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF stream: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def process_multiple_files(file_urls, progress_callback=None):
    """Process multiple files from URLs"""
    all_text = ""
    successful_files = 0
    
    for i, url in enumerate(file_urls):
        try:
            if progress_callback:
                progress_callback(f"📁 Processing file {i+1}/{len(file_urls)}")
            
            text = stream_pdf_from_url(url, progress_callback)
            if text.strip():
                all_text += text + "\n\n" + "="*50 + "\n\n"
                successful_files += 1
                
        except Exception as e:
            logger.warning(f"Failed to process file {i+1}: {e}")
            continue
    
    if progress_callback:
        progress_callback(f"✅ Successfully processed {successful_files}/{len(file_urls)} files")
    
    return all_text, successful_files

# --- Caching and Vector DB Functions ---
def setup_cache_dir():
    """Create cache directory if it doesn't exist"""
    if not os.path.exists(Config.CACHE_DIR):
        os.makedirs(Config.CACHE_DIR)

def get_content_hash(content):
    """Generate hash for content caching"""
    return hashlib.md5(content.encode() if isinstance(content, str) else content).hexdigest()

def create_smart_chunks(text, chunk_size=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP):
    """Create overlapping text chunks with sentence boundary awareness"""
    if not text or len(text) < chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunks.append(text[start:])
            break
        
        # Try to break at sentence boundary
        chunk = text[start:end]
        last_period = chunk.rfind('.')
        last_newline = chunk.rfind('\n')
        
        break_point = max(last_period, last_newline)
        if break_point > start + chunk_size // 2:
            end = start + break_point + 1
        
        chunks.append(text[start:end])
        start = end - overlap
    
    return [chunk.strip() for chunk in chunks if chunk.strip()]

def create_vector_db(text, progress_callback=None):
    """Create vector database with caching"""
    setup_cache_dir()
    
    # Check cache
    text_hash = get_content_hash(text)
    cache_file = os.path.join(Config.CACHE_DIR, f"vectors_{text_hash}.pkl")
    
    if os.path.exists(cache_file):
        if progress_callback:
            progress_callback("📦 Loading from cache...")
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Cache loading failed: {e}")
    
    if progress_callback:
        progress_callback("🔧 Creating text chunks...")
    chunks = create_smart_chunks(text)
    
    if not chunks:
        raise ValueError("No valid chunks created from text")
    
    if progress_callback:
        progress_callback("🔍 Building vector index...")
    
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.8
    )
    
    try:
        vectors = vectorizer.fit_transform(chunks)
        nn_model = NearestNeighbors(n_neighbors=min(10, len(chunks)), metric='cosine')
        nn_model.fit(vectors)
        
        # Cache the results
        cache_data = (nn_model, chunks, vectorizer)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            if progress_callback:
                progress_callback("💾 Saved to cache for future use")
        except Exception as e:
            logger.warning(f"Cache saving failed: {e}")
        
        return cache_data
    except Exception as e:
        logger.error(f"Error creating vector database: {e}")
        raise

def get_relevant_context(nn_model, chunks, vectorizer, query, max_chunks=5):
    """Get relevant context with similarity scoring"""
    try:
        query_vec = vectorizer.transform([query])
        distances, indices = nn_model.kneighbors(query_vec)
        
        # Get chunks and their similarity scores
        relevant_chunks = []
        for i, idx in enumerate(indices[0]):
            chunk = chunks[idx]
            similarity = 1 - distances[0][i]
            relevant_chunks.append((chunk, similarity))
        
        # Sort by similarity and filter
        relevant_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Build context within length limit
        context_parts = []
        total_length = 0
        
        for chunk, similarity in relevant_chunks:
            if total_length + len(chunk) > Config.MAX_CONTEXT_LENGTH:
                break
            context_parts.append(chunk)
            total_length += len(chunk)
        
        return "\n\n".join(context_parts)
    except Exception as e:
        logger.error(f"Error getting relevant context: {e}")
        return ""

def generate_answer(context, query, api_key):
    """Generate answer using OpenAI API (Updated for v1.x+)"""
    try:
        # Initialize OpenAI client with API key
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Based on the provided context from IIT Delhi documents, please answer the question accurately and concisely.

Context:
{context}

Question: {query}

Instructions:
- Provide a clear, direct answer based on the context
- If the context doesn't contain enough information, clearly state this
- Include specific details when available
- Keep the response focused and relevant

Answer:"""

        # Updated API call for OpenAI v1.x+
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in answering questions about IIT Delhi institutional documents. Provide accurate, helpful responses based on the given context."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return f"Error generating response: {str(e)}"

# --- Streamlit Interface ---
def main():
    st.set_page_config(
        page_title="SamvaadGPT - IIT Delhi (Streamlit Cloud)",
        page_icon="🌐",
        layout="wide"
    )
    
    st.markdown("""
    <style>
    .main-header { text-align: center; color: #1f77b4; margin-bottom: 30px; }
    .online-badge { 
        background: linear-gradient(45deg, #28a745, #20c997);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">🌐 SamvaadGPT | Streamlit Cloud Edition</h1>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center;"><span class="online-badge">📡 STREAMLIT CLOUD COMPATIBLE • NO DOWNLOADS</span></div>', unsafe_allow_html=True)
    
    # Show PDF reader status
    if PDF_READER:
        st.success(f"✅ PDF Reader: {PDF_READER} available")
    else:
        st.error("❌ No PDF reader available. Please add PyPDF2 or pdfplumber to requirements.txt")
        return
    
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("🌐 Configuration")
        
        # Input methods
        input_method = st.radio(
            "📁 Input Method:",
            ["Single File URL", "Multiple File URLs", "File ID List"]
        )
        
        if input_method == "Single File URL":
            gdrive_url = st.text_input(
                "📄 Google Drive File URL:",
                value="https://drive.google.com/file/d/1abcd1234_example/view",
                help="Paste a single Google Drive file URL"
            )
            file_urls = [gdrive_url] if gdrive_url else []
            
        elif input_method == "Multiple File URLs":
            urls_text = st.text_area(
                "📄 Google Drive URLs (one per line):",
                height=150,
                help="Enter multiple Google Drive URLs, one per line"
            )
            file_urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
            
        else:  # File ID List
            ids_text = st.text_area(
                "🆔 File IDs (one per line):",
                height=150,
                help="Enter Google Drive file IDs, one per line"
            )
            file_ids = [id.strip() for id in ids_text.split('\n') if id.strip()]
            file_urls = [get_direct_download_url(id) for id in file_ids]
        
        st.divider()
        
        # OpenAI API Key
        api_key = st.text_input("🔑 OpenAI API Key", type="password")
        
        st.divider()
        
        # Statistics
        st.header("📊 Session Stats")
        if 'stats' not in st.session_state:
            st.session_state.stats = {
                'files_processed': 0,
                'questions_answered': 0,
            }
        
        stats = st.session_state.stats
        st.metric("Files Processed", stats['files_processed'])
        st.metric("Questions Answered", stats['questions_answered'])
        
        if st.button("🗑️ Clear Cache & Reset"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main interface
    if not api_key:
        st.info("🔑 Please provide your OpenAI API key in the sidebar to continue.")
        return
    
    if not file_urls:
        st.warning("📄 Please provide at least one Google Drive file URL or ID in the sidebar.")
        return
    
    # Process files if not already done
    if 'vector_db' not in st.session_state or st.session_state.get('processed_urls') != file_urls:
        st.info("🌐 Processing documents directly from Google Drive...")
        
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(message, progress=None):
                status_text.text(message)
                if progress is not None:
                    progress_bar.progress(progress / 100)
            
            try:
                # Convert URLs to direct download URLs
                download_urls = []
                for url in file_urls:
                    file_id = extract_file_id(url)
                    if file_id:
                        download_urls.append(get_direct_download_url(file_id))
                
                if not download_urls:
                    st.error("❌ Could not extract valid file IDs from the provided URLs.")
                    return
                
                # Process files online
                all_text, successful_files = process_multiple_files(
                    download_urls, 
                    lambda msg: update_progress(msg, 50)
                )
                
                if not all_text.strip():
                    st.error("❌ No text could be extracted from any of the files.")
                    return
                
                # Create vector database
                update_progress("🔍 Building search index...", 75)
                vector_db = create_vector_db(
                    all_text, 
                    lambda msg: update_progress(msg, 90)
                )
                
                st.session_state.vector_db = vector_db
                st.session_state.processed_urls = file_urls
                st.session_state.stats['files_processed'] = successful_files
                
                update_progress("✅ Ready to answer questions!", 100)
                progress_container.empty()
                
                st.success(f"🌐 Successfully processed {successful_files} files!")
                
            except Exception as e:
                st.error(f"❌ Error processing files: {str(e)}")
                return
    
    # Q&A Interface
    st.markdown("### 💬 Ask Questions About Your Documents")
    
    query = st.text_input(
        "Enter your question:",
        placeholder="e.g., What are the key terms mentioned in the MoU?",
        help="Ask any question about the content in your documents"
    )
    
    if query:
        with st.spinner("🧠 Generating answer..."):
            try:
                nn_model, chunks, vectorizer = st.session_state.vector_db
                context = get_relevant_context(nn_model, chunks, vectorizer, query)
                
                if not context:
                    st.warning("⚠️ No relevant information found for your question.")
                    return
                
                answer = generate_answer(context, query, api_key)
                
                # Display results
                st.markdown("### 🧾 Answer")
                st.markdown(answer)
                
                with st.expander("📚 View Source Context"):
                    st.text_area("Relevant context:", context, height=200)
                
                st.session_state.stats['questions_answered'] += 1
                
            except Exception as e:
                st.error(f"❌ Error generating answer: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**🌐 SamvaadGPT Streamlit Cloud Edition** | "
        f"PDF Reader: {PDF_READER} | Developed for IIT Delhi"
    )

if __name__ == "__main__":
    main()
