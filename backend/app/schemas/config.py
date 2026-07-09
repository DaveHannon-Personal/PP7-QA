from pydantic import BaseModel


class ConfigRead(BaseModel):
    propresenter_url: str
    propresenter_port: int
    ollama_url: str
    ollama_model: str

    model_config = {"from_attributes": True}


class ConfigUpdate(BaseModel):
    propresenter_url: str | None = None
    propresenter_port: int | None = None
    ollama_url: str | None = None
    ollama_model: str | None = None


class ConnectionStatus(BaseModel):
    propresenter_connected: bool
    propresenter_version: str | None
    ollama_connected: bool
    ollama_models: list[str]
