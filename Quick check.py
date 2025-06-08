import streamlit as st
import fitz
import pytesseract
import openai
from PIL import Image
from sklearn.feature_extraction.text import TfidfVectorizer
import requests

print("✅ All imports successful!")
print(f"Streamlit version: {st.__version__}")
print(f"PyMuPDF version: {fitz.__version__}")
print("Ready to run the app!")
