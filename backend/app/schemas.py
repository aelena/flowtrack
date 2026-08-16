from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .models import ProjectStatus, TaskStatus


# --- Area ---
class AreaCreate(BaseModel):
    name: str

class AreaUpdate(BaseModel):
    name: str

class AreaOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Project ---
class ProjectCreate(BaseModel):
    work_name: str
    final_name: Optional[str] = None
    description: Optional[str] = None
    vision: Optional[str] = None
    goal: Optional[str] = None
    completion_criteria: Optional[str] = None
    abandonment_criteria: Optional[str] = None
    desired_end_date: Optional[date] = None
    github_repo: Optional[str] = None
    website: Optional[str] = None
    star_rating: Optional[int] = Field(None, ge=1, le=5)
    subjective_completion: int = 0
    local_dir: Optional[str] = None
    area_id: Optional[UUID] = None
    status: ProjectStatus = ProjectStatus.active
    tags: list[str] = []
    collaborators: list = []

class ProjectUpdate(BaseModel):
    work_name: Optional[str] = None
    final_name: Optional[str] = None
    description: Optional[str] = None
    vision: Optional[str] = None
    goal: Optional[str] = None
    completion_criteria: Optional[str] = None
    abandonment_criteria: Optional[str] = None
    desired_end_date: Optional[date] = None
    github_repo: Optional[str] = None
    website: Optional[str] = None
    star_rating: Optional[int] = Field(None, ge=1, le=5)
    subjective_completion: Optional[int] = None
    local_dir: Optional[str] = None
    area_id: Optional[UUID] = None
    status: Optional[ProjectStatus] = None
    tags: Optional[list[str]] = None
    collaborators: Optional[list] = None

class ProjectOut(BaseModel):
    id: UUID
    work_name: str
    final_name: Optional[str]
    description: Optional[str]
    vision: Optional[str]
    goal: Optional[str]
    completion_criteria: Optional[str]
    abandonment_criteria: Optional[str]
    desired_end_date: Optional[date]
    github_repo: Optional[str]
    website: Optional[str]
    star_rating: Optional[int]
    subjective_completion: int
    local_dir: Optional[str]
    area_id: Optional[UUID]
    archived: bool
    status: ProjectStatus
    tags: list[str]
    collaborators: list
    task_completion: float = 0.0
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class ProjectListOut(BaseModel):
    id: UUID
    work_name: str
    final_name: Optional[str]
    area_id: Optional[UUID]
    archived: bool
    status: ProjectStatus
    tags: list[str]
    star_rating: Optional[int]
    task_completion: float = 0.0
    subjective_completion: int
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Task ---
class TaskCreate(BaseModel):
    content: str
    description: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class TaskOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# --- Note ---
class NoteCreate(BaseModel):
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    content: str

    @model_validator(mode="after")
    def require_parent(self):
        if not self.project_id and not self.task_id:
            raise ValueError("A note must belong to a project or a task (provide project_id or task_id)")
        return self

class NoteUpdate(BaseModel):
    content: str

class NoteOut(BaseModel):
    id: UUID
    project_id: Optional[UUID]
    task_id: Optional[UUID]
    content: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# --- File ---
class FileOut(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    file_type: str
    folder: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Collaborator ---
class CollaboratorCreate(BaseModel):
    name: str
    role: Optional[str] = None


# --- Snippet ---
class SnippetCreate(BaseModel):
    project_id: UUID
    type: str
    content: str
    source_url: Optional[str] = None

class SnippetOut(BaseModel):
    id: UUID
    project_id: UUID
    snippet_type: str
    content: str
    source_url: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# --- LLM ---
class LLMProviderCreate(BaseModel):
    name: str
    provider_type: str
    config: dict = {}

class LLMProviderOut(BaseModel):
    id: UUID
    name: str
    provider_type: str
    config: dict
    created_at: datetime
    model_config = {"from_attributes": True}

class ChatMessage(BaseModel):
    message: str

class GenerateRequest(BaseModel):
    format: Optional[str] = "json"
