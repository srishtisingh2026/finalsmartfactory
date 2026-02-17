"""
Prompt API Routes
All prompt data is fetched from MLflow Prompt Registry.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from services.prompts import prompt_service

router = APIRouter(tags=["prompts"])


class PromptCreateRequest(BaseModel):
    name: str
    content: str
    variables: List[str] = []
    tags: Optional[List[str]] = []
    description: Optional[str] = ""
    model_parameters: Optional[Dict[str, Any]] = {}


class PromoteRequest(BaseModel):
    version: int
    environment: str


@router.get("/prompts")
def get_prompts():
    """
    Get all prompts (latest version of each).
    Data is fetched from MLflow Prompt Registry.
    """
    return prompt_service.list_prompts()


@router.post("/prompts")
def create_prompt(request: PromptCreateRequest):
    """
    Create a new prompt version.
    If prompt name already exists, creates a new version.
    Stored in MLflow Prompt Registry.
    """
    try:
        return prompt_service.create_prompt_version(
            request.name,
            request.content,
            request.variables,
            request.tags,
            request.description,
            request.model_parameters
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{name}")
def get_prompt_by_name(name: str, version: Optional[int] = None):
    """
    Get a specific prompt by name.
    Optionally specify version (defaults to latest).
    """
    prompt = prompt_service.get_prompt_by_name(name, version)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
    return prompt


@router.get("/prompts/{name}/history")
def get_history(name: str):
    """
    Get version history for a prompt.
    Returns all versions from MLflow.
    """
    history = prompt_service.get_history(name)
    if not history:
        raise HTTPException(status_code=404, detail=f"No history found for prompt '{name}'")
    return history


@router.post("/prompts/{name}/promote")
def promote_prompt(name: str, request: PromoteRequest):
    """
    Promote a prompt version to an environment.
    Uses MLflow aliases (e.g., 'production', 'staging').
    """
    try:
        success = prompt_service.promote_version(name, request.version, request.environment)
        return {"status": "success", "environment": request.environment, "version": request.version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
