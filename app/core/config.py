"""Central settings object. Loads config.yaml, then applies env var overrides.

Env overrides use double-underscore nesting, e.g. GATEWAY__LOCAL_URL=http://localhost:8081
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"


class Thresholds(BaseModel):
    local_min_ram_mb: int = 1500
    local_max_cpu_pct: int = 90
    local_max_queue: int = 4
    remote_min_bw_kbps: int = 64


class Weights(BaseModel):
    cost: float = 1.0
    latency: float = 0.15
    quality: float = 5.0


class QualityByComplexity(BaseModel):
    low: int
    medium: int
    high: int


class Quality(BaseModel):
    local: QualityByComplexity = QualityByComplexity(low=3, medium=2, high=1)
    remote: QualityByComplexity = QualityByComplexity(low=3, medium=3, high=3)


class Required(BaseModel):
    low: int = 1
    medium: int = 2
    high: int = 3


class Hysteresis(BaseModel):
    margin_pct: int = 10
    samples: int = 3


class Concurrency(BaseModel):
    local: int = 2


class RouterConfig(BaseModel):
    thresholds: Thresholds = Thresholds()
    weights: Weights = Weights()
    quality: Quality = Quality()
    required: Required = Required()
    hysteresis: Hysteresis = Hysteresis()
    scarcity_k: float = 2.0
    concurrency: Concurrency = Concurrency()
    quota_unit: str = "requests"


class CacheConfig(BaseModel):
    semantic_threshold: float = 0.92
    ttl_hours: int = 24
    max_entries: int = 5000


class RetrievalConfig(BaseModel):
    bm25_k: int = 20
    vec_k: int = 20
    rrf_k: int = 60
    context_k: int = 4
    context_max_tokens: int = 1400
    rerank: bool = False


class ChunkingConfig(BaseModel):
    size_tokens: int = 350
    overlap_tokens: int = 60


class GroundingConfig(BaseModel):
    support_cosine: float = 0.55
    overlap_min: float = 0.6
    abstain_below: float = 0.35


class QAConfig(BaseModel):
    retrieval: RetrievalConfig = RetrievalConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    grounding: GroundingConfig = GroundingConfig()


class PlacementWeights(BaseModel):
    skills: float = 40
    cgpa: float = 25
    coding: float = 20
    projects: float = 15


class PlacementConfig(BaseModel):
    weights: PlacementWeights = PlacementWeights()


class SimulatorConfig(BaseModel):
    mode: str = "scenario"
    scenario_file: str = "data/synthetic/scenarios/steady.csv"


class GatewayConfig(BaseModel):
    local_url: str = "http://inference:8081"
    remote_url: str = "http://remote-tier:8082"
    pricing_file: str = "data/synthetic/pricing.yaml"
    use_mock: bool = True


class DataConfig(BaseModel):
    adapter: str = "synthetic"


class DBConfig(BaseModel):
    ops_db_path: str = "data/ops.db"
    amypo_db_path: str = "data/amypo.db"


class ServicesConfig(BaseModel):
    router_url: str = "http://router:8000"


def _yaml_config_source(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="ignore")

    router: RouterConfig = RouterConfig()
    cache: CacheConfig = CacheConfig()
    qa: QAConfig = QAConfig()
    placement: PlacementConfig = PlacementConfig()
    simulator: SimulatorConfig = SimulatorConfig()
    gateway: GatewayConfig = GatewayConfig()
    data: DataConfig = DataConfig()
    db: DBConfig = DBConfig()
    services: ServicesConfig = ServicesConfig()
    strict_contract: bool = False
    version: str = "1.0.0"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Precedence: init args > env vars > config.yaml > field defaults.
        return (init_settings, env_settings, _YamlSource(settings_cls), file_secret_settings)


class _YamlSource(PydanticBaseSettingsSource):
    def get_field_value(self, field, field_name):  # pragma: no cover - unused, we override __call__
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        return _yaml_config_source(DEFAULT_CONFIG_PATH)


_settings: Settings | None = None


def get_settings(reload: bool = False) -> Settings:
    global _settings
    if _settings is None or reload:
        _settings = Settings()
    return _settings
