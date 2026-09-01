import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow():
    return datetime.now(UTC)


class ProjectStatus(str, enum.Enum):
    active = "active"
    on_hold = "on_hold"
    deprecated = "deprecated"


class TaskStatus(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    done = "done"


class Area(Base):
    __tablename__ = "areas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    projects = relationship("Project", back_populates="area")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_name = Column(String(255), nullable=False)
    final_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    goal = Column(Text, nullable=True)
    completion_criteria = Column(Text, nullable=True)
    abandonment_criteria = Column(Text, nullable=True)
    desired_end_date = Column(Date, nullable=True)
    github_repo = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)
    star_rating = Column(Integer, nullable=True)
    subjective_completion = Column(Integer, default=0)
    local_dir = Column(String(500), nullable=True)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id", ondelete="SET NULL"), nullable=True)
    archived = Column(Boolean, default=False)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.active)
    tags = Column(JSONB, default=list)
    collaborators = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    area = relationship("Area", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="project", cascade="all, delete-orphan")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.new)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    # When the task actually became done, as opposed to when the row last
    # changed. updated_at cannot answer this: editing the title of a finished
    # task moves it, and so does reopening and re-closing one, which is exactly
    # the case the throughput numbers care about.
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # True for the rows filled in by the backfill, whose completed_at is
    # updated_at standing in for a date nobody recorded. Kept so a chart can say
    # which part of itself is a guess instead of presenting all of it as fact.
    completed_at_estimated = Column(Boolean, default=False, nullable=False)

    project = relationship("Project", back_populates="tasks")
    notes = relationship("Note", back_populates="task", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="notes")
    task = relationship("Task", back_populates="notes")


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(1000), nullable=False)
    folder = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship("Project", back_populates="files")


class Snippet(Base):
    __tablename__ = "snippets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    snippet_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
