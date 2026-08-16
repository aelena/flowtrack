from datetime import date, datetime
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
    final_name: str | None = None
    description: str | None = None
    vision: str | None = None
    goal: str | None = None
    completion_criteria: str | None = None
    abandonment_criteria: str | None = None
    desired_end_date: date | None = None
    github_repo: str | None = None
    website: str | None = None
    star_rating: int | None = Field(None, ge=1, le=5)
    subjective_completion: int = 0
    local_dir: str | None = None
    area_id: UUID | None = None
    status: ProjectStatus = ProjectStatus.active
    tags: list[str] = []
    collaborators: list = []


class ProjectUpdate(BaseModel):
    work_name: str | None = None
    final_name: str | None = None
    description: str | None = None
    vision: str | None = None
    goal: str | None = None
    completion_criteria: str | None = None
    abandonment_criteria: str | None = None
    desired_end_date: date | None = None
    github_repo: str | None = None
    website: str | None = None
    star_rating: int | None = Field(None, ge=1, le=5)
    subjective_completion: int | None = None
    local_dir: str | None = None
    area_id: UUID | None = None
    status: ProjectStatus | None = None
    tags: list[str] | None = None
    collaborators: list | None = None


class ProjectOut(BaseModel):
    id: UUID
    work_name: str
    final_name: str | None
    description: str | None
    vision: str | None
    goal: str | None
    completion_criteria: str | None
    abandonment_criteria: str | None
    desired_end_date: date | None
    github_repo: str | None
    website: str | None
    star_rating: int | None
    subjective_completion: int
    local_dir: str | None
    area_id: UUID | None
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
    final_name: str | None
    area_id: UUID | None
    archived: bool
    status: ProjectStatus
    tags: list[str]
    star_rating: int | None
    task_completion: float = 0.0
    subjective_completion: int
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Task ---
class TaskCreate(BaseModel):
    content: str
    description: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None


class TaskOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# --- Note ---
class NoteCreate(BaseModel):
    project_id: UUID | None = None
    task_id: UUID | None = None
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
    project_id: UUID | None
    task_id: UUID | None
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
    folder: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Collaborator ---
class CollaboratorCreate(BaseModel):
    name: str
    role: str | None = None


# --- Snippet ---
class SnippetCreate(BaseModel):
    project_id: UUID
    type: str
    content: str
    source_url: str | None = None


class SnippetOut(BaseModel):
    id: UUID
    project_id: UUID
    snippet_type: str
    content: str
    source_url: str | None
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
    format: str | None = "json"
