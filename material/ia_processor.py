# from transformers import pipeline
import PyPDF2
from docx import Document
from pptx import Presentation
import os
import re

def extract_text_from_file(file_path):
    _, file_extension = os.path.splitext(file_path)
    text = ""

    if file_extension == '.pdf':
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for i, page in enumerate(reader.pages):
                text += f"\n[Página {i+1}]\n" + (page.extract_text() or "")
    elif file_extension == '.docx':
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    elif file_extension == '.pptx':
        ppt = Presentation(file_path)
        for slide in ppt.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
    elif file_extension == '.txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
    else:
        raise ValueError(f"Formato de archivo no soportado: {file_extension}")
    
    return text.strip()

def split_text_into_chapters(text):
    """Divide el texto en capítulos basados en títulos detectados."""
    chapters = re.split(r'(?i)(cap[ií]tulo \d+|secci[oó]n \d+)', text)
    return [c.strip() for c in chapters if c.strip()]

def generate_questions_from_text(text,num_questions):
    if not text.strip():
        return "No se encontró texto para analizar."
    
    generator = pipeline("summarization", model="facebook/bart-large-cnn")
    chapters = split_text_into_chapters(text)
    
    questions_output = []
    for i, chapter in enumerate(chapters):
        summary = generator(chapter[:1024], max_length=150, min_length=30, truncation=True)[0]['summary_text']
        question = f"¿De qué trata este capítulo?\nRespuesta: {summary}\nReferencia: Capítulo {i+1}"
        questions_output.append(question)
    
    return "\n\n".join(questions_output)
