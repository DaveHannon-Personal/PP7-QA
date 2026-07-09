"""
Persisted configuration for ProPresenter and Ollama connections.
Only one row (id=1) is used — GET fetches it, PUT upserts it.
"""
from sqlalchemy import Column, Integer, String
from app.database import Base


class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, default=1)
    propresenter_url = Column(String, nullable=False, default="http://localhost")
    propresenter_port = Column(Integer, nullable=False, default=50001)
    ollama_url = Column(String, nullable=False, default="http://host.docker.internal:11434")
    ollama_model = Column(String, nullable=False, default="llama3.2:3b")
