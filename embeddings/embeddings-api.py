from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import numpy as np
from simple_embeddings import get_pretrained_embedding, get_finetuned_embedding

app = FastAPI(
    title="Embedding API",
    description="API for generating text embeddings using BAAI/bge-large-en-v1.5 model",
    version="1.0.0"
)

class TextRequest(BaseModel):
    text: str
    model_type: str = "pretrained"  # or "finetuned"

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model_type: str

@app.post("/embedding", response_model=EmbeddingResponse)
async def get_embedding(request: TextRequest):
    try:
        if request.model_type == "pretrained":
            embedding = get_pretrained_embedding(request.text)
        elif request.model_type == "finetuned":
            embedding = get_finetuned_embedding(request.text)
        else:
            raise HTTPException(status_code=400, detail="Invalid model_type. Use 'pretrained' or 'finetuned'")
        
        return EmbeddingResponse(
            embedding=embedding.tolist(),
            model_type=request.model_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)