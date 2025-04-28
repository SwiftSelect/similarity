"""
Simple Embeddings Generator

Minimal code to generate embeddings from text using either pre-trained or fine-tuned models.
This file contains just the essential functions for embedding generation.
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from transformers import AutoTokenizer, AutoModel
import google.generativeai as genai

# Configure Gemini API key
genai.configure(api_key="AIzaSyCeVioNrfeI8536vq0avWVwpbStVmHNFuU")

# Model class needed for fine-tuned model loading
class SentenceTransformerFineTuner(nn.Module):
    def __init__(self, model_name):
        super(SentenceTransformerFineTuner, self).__init__()
        self.model = AutoModel.from_pretrained(model_name)
        
    def forward(self, input_ids, attention_mask):
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
        embeddings = self.mean_pooling(outputs, attention_mask)
        return F.normalize(embeddings, p=2, dim=1)
    
    def mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


# ---- SIMPLE EMBEDDING FUNCTIONS ----

def get_pretrained_embedding(text, model_name="BAAI/bge-large-en-v1.5"):
    """Get embedding from pre-trained model in just 3 lines."""
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    
    # Tokenize and generate embedding
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Mean pooling
    attention_mask = inputs["attention_mask"]
    token_embeddings = outputs.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    # Normalize
    embeddings = F.normalize(embeddings, p=2, dim=1)
    
    return embeddings.squeeze().cpu().numpy()


def get_finetuned_embedding(text, model_name="BAAI/bge-large-en-v1.5", model_path="best_model.pt"):
    """Get embedding from fine-tuned model in just a few lines."""
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = SentenceTransformerFineTuner(model_name)
    model.load_state_dict(torch.load(model_path, map_location="cpu"), strict=False)
    model.eval()
    
    # Tokenize and generate embedding
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        embeddings = model(inputs["input_ids"], inputs["attention_mask"])
    
    return embeddings.squeeze().cpu().numpy()


def get_gemini_embedding(text, output_dim=1024):
    """Get embedding using the Gemini embedding model."""
    try:
        embedding_response = genai.embed_content(
            model="models/gemini-embedding-exp-03-07",
            content=text,
            output_dimensionality=output_dim
        )
        return np.array(embedding_response["embedding"])
    except Exception as e:
        print(f"Error generating Gemini embedding: {str(e)}")
        # Return a default embedding filled with zeros as fallback
        return np.zeros(output_dim)


def calculate_similarity(embedding1, embedding2):
    """Calculate cosine similarity between two embeddings."""
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))


# ---- EXAMPLE USAGE ----

if __name__ == "__main__":
    # Sample texts
    resume = "Experienced ML Engineer with 5 years of Python development. Built transformer models."
    job = "Looking for a Python developer with ML experience to build NLP systems."
    
    print("Generating pre-trained embeddings...")
    resume_emb = get_pretrained_embedding(resume)
    job_emb = get_pretrained_embedding(job)
    
    similarity = calculate_similarity(resume_emb, job_emb)
    print(f"Pre-trained similarity: {similarity:.4f}")
    
    # Try fine-tuned if model exists
    model_path = "best_model.pt"
    if os.path.exists(model_path):
        print("\nGenerating fine-tuned embeddings...")
        resume_emb_ft = get_finetuned_embedding(resume, model_path=model_path)
        job_emb_ft = get_finetuned_embedding(job, model_path=model_path)
        
        similarity_ft = calculate_similarity(resume_emb_ft, job_emb_ft)
        print(f"Fine-tuned similarity: {similarity_ft:.4f}") 