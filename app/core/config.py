from pathlib import Path
from typing import Any, Optional

from dotenv import find_dotenv
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    BaseSettings,
    Field,
    parse_file_as,
    parse_obj_as,
    validator,
)


class ActionReport(BaseModel):
    status: str | None = None
    link: str | None = None
    summary: str | None = None
    external_run_id: str | None = Field(None, alias="externalRunId")


class Mapping(BaseModel):
    enabled: bool | str = True
    method: str | None = None
    url: str | None = None
    body: dict[str, Any] | str | None = None
    headers: dict[str, str] | str | None = None
    query: dict[str, str] | str | None = None
    report: ActionReport | None = None
    fieldsToDecryptPaths: list[str] = []


class Settings(BaseSettings):
    USING_LOCAL_PORT_INSTANCE: bool = False
    LOG_LEVEL: str = "INFO"

    STREAMER_NAME: str

    PORT_ORG_ID: str
    PORT_API_BASE_URL: AnyHttpUrl = parse_obj_as(AnyHttpUrl, "https://api.getport.io")
    PORT_CLIENT_ID: str
    PORT_CLIENT_SECRET: str
    KAFKA_CONSUMER_SECURITY_PROTOCOL: str = "plaintext"
    KAFKA_CONSUMER_AUTHENTICATION_MECHANISM: str = "none"
    KAFKA_CONSUMER_SESSION_TIMEOUT_MS: int = 45000
    KAFKA_CONSUMER_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_CONSUMER_GROUP_ID: str = ""

    KAFKA_RUNS_TOPIC: str = ""

    CONTROL_THE_PAYLOAD_CONFIG_PATH: Path = Path("./control_the_payload_config.json")

    @validator("KAFKA_RUNS_TOPIC", always=True)
    def set_kafka_runs_topic(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return f"{values.get('PORT_ORG_ID')}.runs"

    KAFKA_CHANGE_LOG_TOPIC: str = ""

    @validator("KAFKA_CHANGE_LOG_TOPIC", always=True)
    def set_kafka_change_log_topic(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return f"{values.get('PORT_ORG_ID')}.change.log"

    AGENT_ENVIRONMENTS: list[str] = Field(default_factory=list)

    @validator("AGENT_ENVIRONMENTS", pre=True)
    def parse_environments(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            # Handle empty string
            if not v:
                return []
            # Parse comma-separated string
            return [e.strip() for e in v.split(",") if e.strip()]
        if isinstance(v, list):
            return v
        # If it's any other type, return empty list
        return []

    class Config:
        case_sensitive = True
        env_file = find_dotenv()
        env_file_encoding = "utf-8"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            # Handle AGENT_ENVIRONMENTS as a plain string, not JSON
            if field_name == "AGENT_ENVIRONMENTS":
                return raw_val
            # For all other fields, use default parsing
            return cls.json_loads(raw_val)  # type: ignore

    WEBHOOK_INVOKER_TIMEOUT: float = 30


settings = Settings()

control_the_payload_config = parse_file_as(
    list[Mapping], settings.CONTROL_THE_PAYLOAD_CONFIG_PATH
)
