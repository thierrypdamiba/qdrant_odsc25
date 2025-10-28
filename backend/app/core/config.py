from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings - all configuration from environment variables"""
    
    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_cloud_inference: bool = True  # Enable cloud inference
    
    # LLM Configuration
    groq_api_key: Optional[str] = None
    
    # Search Configuration
    perplexity_api_key: Optional[str] = None
    
    # Mock Configuration
    use_mock_vector_store: bool = True
    use_mock_llm: bool = True
    use_mock_search: bool = True
    
    # Application Configuration
    environment: str = "development"
    org_id: str = "default_org"
    
    # File Upload
    upload_dir: str = "./uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    
    # Embedding Configuration
    text_embedding_model: str = "all-MiniLM-L6-v2"
    image_embedding_model: str = "openai/clip-vit-base-patch32"
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment


settings = Settings()


