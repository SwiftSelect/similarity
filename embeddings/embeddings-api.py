from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import numpy as np
from simple_embeddings import get_pretrained_embedding, get_finetuned_embedding, get_gemini_embedding, get_lora_embedding

app = FastAPI(
    title="Embedding API",
    description="API for generating text embeddings using BAAI/bge-large-en-v1.5 model",
    version="1.0.0"
)

class TextRequest(BaseModel):
    text: str
    model_type: str = "pretrained"  # or "finetuned" or "gemini" or "lora"

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
        elif request.model_type == "lora":
            embedding = get_lora_embedding(request.text)
        elif request.model_type == "gemini":
            embedding = get_gemini_embedding(request.text, output_dim=1024)
        else:
            raise HTTPException(status_code=400, detail="Invalid model_type. Use 'pretrained', 'finetuned', 'lora', or 'gemini'")
        
        return EmbeddingResponse(
            embedding=embedding.tolist(),
            model_type=request.model_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/info")
async def get_info():
    import os
    
    # Check which models are available
    available_models = ["pretrained"]  # Base model is always available
    
    # Check for fine-tuned model
    model_paths = ["best_model.pt", "../best_model.pt"]
    for path in model_paths:
        if os.path.exists(path):
            available_models.append("finetuned")
            break
    
    # Check for LoRA model
    lora_paths = [
        "lora_best_model",
        "lora_finetuned_model/lora_best_model",
        "../lora_finetuned_model/lora_best_model"
    ]
    for path in lora_paths:
        if os.path.exists(path):
            available_models.append("lora")
            break
    
    return {
        "available_models": available_models,
        "model_base": "BAAI/bge-large-en-v1.5",
        "api_version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)