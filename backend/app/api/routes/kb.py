"""Knowledge base management routes"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, BackgroundTasks
from typing import List
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentMetadata
)
from app.core.auth import User
from app.core.deps import get_current_user
from app.services.document_processor import DocumentProcessor, EmbeddingService
from app.services.vector_store import QdrantVectorStore
from app.core.config import settings
import uuid
from datetime import datetime

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

# Initialize services
doc_processor = DocumentProcessor(settings.upload_dir)
embedding_service = EmbeddingService(settings.text_embedding_model)


async def get_vector_store() -> QdrantVectorStore:
    """Get vector store instance"""
    return QdrantVectorStore(
        settings.qdrant_url, 
        settings.qdrant_api_key,
        cloud_inference=settings.qdrant_cloud_inference
    )


async def process_document_background(
    doc_id: str,
    file_path: str,
    filename: str,
    file_type: str,
    uploader_id: str,
    tags: List[str],
    vector_store: QdrantVectorStore
):
    """Background task to process document"""
    try:
        # Update status to processing
        collection_name = "documents"
        
        # Extract text
        text = doc_processor.extract_text(file_path, file_type)
        
        # Chunk text
        chunks = doc_processor.chunk_text(
            text,
            settings.chunk_size,
            settings.chunk_overlap
        )
        
        if not chunks:
            # Update status to failed
            await vector_store.upsert_vectors(
                collection_name=collection_name,
                vectors=[[0.0] * 384],  # Dummy vector
                payloads=[{
                    "doc_id": doc_id,
                    "filename": filename,
                    "file_type": file_type,
                    "upload_date": datetime.utcnow().isoformat(),
                    "status": "failed",
                    "tags": tags,
                    "uploader_id": uploader_id,
                    "size_bytes": 0,
                    "error_message": "No text extracted from document"
                }],
                ids=[doc_id]
            )
            return
        
        # Prepare data for storage
        text_collection = f"{settings.org_id}_text"
        
        # If using cloud inference, Qdrant will generate embeddings server-side
        if vector_store.cloud_inference:
            # Just pass the raw text - Qdrant will embed it
            chunk_texts = [chunk["text"] for chunk in chunks]
            payloads = []
            ids = []
            for chunk in chunks:
                chunk_id = f"{doc_id}_chunk_{chunk['chunk_index']}"
                ids.append(chunk_id)
                payloads.append({
                    "doc_id": doc_id,
                    "filename": filename,
                    "content": chunk["text"],
                    "chunk_index": chunk["chunk_index"],
                    "tags": tags
                })
            
            await vector_store.create_collection(text_collection)
            await vector_store.upsert_vectors(
                collection_name=text_collection,
                vectors=[],  # Empty - using cloud inference
                payloads=payloads,
                ids=ids,
                texts=chunk_texts  # Pass text for cloud embedding
            )
        else:
            # Generate embeddings locally
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = embedding_service.embed_text(chunk_texts)
            
            await vector_store.create_collection(text_collection, len(embeddings[0]))
            
            # Prepare payloads
            payloads = []
            ids = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_id = f"{doc_id}_chunk_{chunk['chunk_index']}"
                ids.append(chunk_id)
                payloads.append({
                    "doc_id": doc_id,
                    "filename": filename,
                    "content": chunk["text"],
                    "chunk_index": chunk["chunk_index"],
                    "tags": tags
                })
            
            await vector_store.upsert_vectors(
                collection_name=text_collection,
                vectors=embeddings,
                payloads=payloads,
                ids=ids
            )
        
        # Update document status to completed
        await vector_store.upsert_vectors(
            collection_name=collection_name,
            vectors=[[0.0] * 384],  # Dummy vector
            payloads=[{
                "doc_id": doc_id,
                "filename": filename,
                "file_type": file_type,
                "upload_date": datetime.utcnow().isoformat(),
                "status": "completed",
                "tags": tags,
                "uploader_id": uploader_id,
                "size_bytes": len(text),
                "num_chunks": len(chunks)
            }],
            ids=[doc_id]
        )
        
    except Exception as e:
        # Update status to failed
        print(f"Error processing document: {e}")
        try:
            await vector_store.upsert_vectors(
                collection_name="documents",
                vectors=[[0.0] * 384],
                payloads=[{
                    "doc_id": doc_id,
                    "filename": filename,
                    "file_type": file_type,
                    "upload_date": datetime.utcnow().isoformat(),
                    "status": "failed",
                    "tags": tags,
                    "uploader_id": uploader_id,
                    "size_bytes": 0,
                    "error_message": str(e)
                }],
                ids=[doc_id]
            )
        except:
            pass


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tags: str = "",  # Comma-separated tags
    current_user: User = Depends(get_current_user),
    vector_store: QdrantVectorStore = Depends(get_vector_store)
):
    """Upload a document"""
    # Check permission
    if not current_user.permissions.can_upload_documents:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to upload documents"
        )
    
    # Validate file type
    filename = file.filename
    file_ext = filename.split(".")[-1].lower()
    
    supported_types = ["pdf", "txt", "docx", "md"]
    if file_ext not in supported_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Supported: {', '.join(supported_types)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.max_file_size / (1024*1024)}MB"
        )
    
    # Save file
    doc_id, file_path = doc_processor.save_file(content, filename)
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    # Store initial metadata in Qdrant
    collection_name = "documents"
    await vector_store.create_collection(collection_name, 384)
    
    await vector_store.upsert_vectors(
        collection_name=collection_name,
        vectors=[[0.0] * 384],  # Dummy vector for metadata
        payloads=[{
            "doc_id": doc_id,
            "filename": filename,
            "file_type": file_ext,
            "upload_date": datetime.utcnow().isoformat(),
            "status": "pending",
            "tags": tag_list,
            "uploader_id": current_user.user_id,
            "size_bytes": len(content)
        }],
        ids=[doc_id]
    )
    
    # Schedule background processing
    background_tasks.add_task(
        process_document_background,
        doc_id,
        file_path,
        filename,
        file_ext,
        current_user.user_id,
        tag_list,
        vector_store
    )
    
    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=filename,
        status="pending",
        message="Document uploaded successfully and is being processed"
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    vector_store: QdrantVectorStore = Depends(get_vector_store)
):
    """List all documents"""
    # This is simplified - in a real implementation, you'd paginate and filter
    # For now, return empty list (mock data would be here)
    return DocumentListResponse(
        documents=[],
        total=0
    )


@router.get("/documents/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    vector_store: QdrantVectorStore = Depends(get_vector_store)
):
    """Get document processing status"""
    collection_name = "documents"
    
    doc_data = await vector_store.get_by_id(collection_name, doc_id)
    
    if not doc_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    payload = doc_data["payload"]
    
    return DocumentStatusResponse(
        doc_id=doc_id,
        status=payload.get("status", "unknown"),
        progress=None,
        error_message=payload.get("error_message")
    )


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    vector_store: QdrantVectorStore = Depends(get_vector_store)
):
    """Delete a document"""
    if not current_user.permissions.can_upload_documents:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete documents"
        )
    
    # Delete from documents collection
    await vector_store.delete("documents", [doc_id])
    
    # Note: In a real implementation, you'd also delete all chunks
    # from the text collection that belong to this document
    
    return {"message": "Document deleted successfully"}


