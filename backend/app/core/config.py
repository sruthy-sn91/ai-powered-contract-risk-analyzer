from pydantic_settings import BaseSettings, SettingsConfigDict
import json

class Settings(BaseSettings):
    ACORD_DIR: str = "./data/acord"
    CUAD_DIR: str = "./data/cuad"
    POLICIES_DIR: str = "./policies"
    INDEX_DIR: str = "./indices"
    EXPORTS_DIR: str = "./exports"
    MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    JWT_SECRET: str = "change-me-local-only"
    JWT_ALG: str = "HS256"

    # Risk weights (per Business Unit). JSON string of mapping BU -> lens weights
    # Example: {"default":{"legal":0.3,"operational":0.2,"regulatory":0.2,"counterparty":0.15,"financial":0.15}}
    RISK_WEIGHTS_JSON: str = json.dumps({
        "default": {"legal": 0.30, "operational": 0.20, "regulatory": 0.20, "counterparty": 0.15, "financial": 0.15}
    })

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    def risk_weights(self, bu: str | None = None) -> dict:
        try:
            obj = json.loads(self.RISK_WEIGHTS_JSON)
            if bu and bu in obj:
                return obj[bu]
            return obj.get("default", {})
        except Exception:
            return {"legal": 0.30, "operational": 0.20, "regulatory": 0.20, "counterparty": 0.15, "financial": 0.15}

settings = Settings()
