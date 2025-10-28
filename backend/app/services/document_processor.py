"""Document processing service - upload, extraction, chunking, embedding"""
import os
import uuid
from typing import List, Dict, Any, Optional, BinaryIO
from datetime import datetime
import PyPDF2
import docx
import pdfplumber
from pathlib import Path


class DocumentProcessor:
    """Handle document upload, text extraction, and chunking"""
    
    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_content: bytes, filename: str) -> str:
        """Save uploaded file and return file path"""
        doc_id = str(uuid.uuid4())
        doc_dir = self.upload_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = doc_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return doc_id, str(file_path)
    
    def extract_text(self, file_path: str, file_type: str) -> str:
        """Extract text from document based on file type"""
        if file_type == "pdf":
            return self._extract_text_pdf(file_path)
        elif file_type in ["docx", "doc"]:
            return self._extract_text_docx(file_path)
        elif file_type in ["txt", "md"]:
            return self._extract_text_plain(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _extract_text_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error with pdfplumber: {e}, trying PyPDF2")
            # Fallback to PyPDF2
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        
        return text.strip()
    
    def _extract_text_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    
    def _extract_text_plain(self, file_path: str) -> str:
        """Extract text from plain text files"""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        # Simple word-based chunking
        words = text.split()
        chunks = []
        
        if not words:
            return []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            chunks.append({
                "text": chunk_text,
                "chunk_index": len(chunks),
                "start_word": i,
                "end_word": i + len(chunk_words)
            })
        
        return chunks
    
    def extract_images_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract images from PDF"""
        images = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_images = page.images
                    for img_idx, img in enumerate(page_images):
                        images.append({
                            "page": page_num + 1,
                            "index": img_idx,
                            "bbox": (img.get("x0"), img.get("top"), img.get("x1"), img.get("bottom"))
                        })
        except Exception as e:
            print(f"Error extracting images: {e}")
        
        return images


class EmbeddingService:
    """Generate embeddings for text"""
    
    def __init__(
        self,
        text_model_name: str = "all-MiniLM-L6-v2"
    ):
        self.text_model_name = text_model_name
        self._text_model = None
    
    def _load_text_model(self):
        """Lazy load text embedding model"""
        if self._text_model is None:
            import time
            load_start = time.time()
            from sentence_transformers import SentenceTransformer
            print(f"[EMBEDDING] Loading SentenceTransformer model: {self.text_model_name}")
            self._text_model = SentenceTransformer(self.text_model_name)
            load_time = int((time.time() - load_start) * 1000)
            print(f"[EMBEDDING] Model loaded in: {load_time}ms")
        return self._text_model
    
    def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text"""
        import time
        model = self._load_text_model()
        encode_start = time.time()
        embeddings = model.encode(texts, convert_to_numpy=True)
        encode_time = int((time.time() - encode_start) * 1000)
        print(f"[EMBEDDING] Encoding {len(texts)} text(s) took: {encode_time}ms")
        return embeddings.tolist()
    
    def embed_text_query(self, query: str) -> List[float]:
        """Generate embedding for a single query"""
        return self.embed_text([query])[0]


