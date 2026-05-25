from datetime import datetime, timezone
from pydantic import BaseModel


class BiometricReading(BaseModel):
    user_id: str
    heart_rate: int | None = None
    hrv: float | None = None
    body_temp: float | None = None
    gsr: float | None = None
    steps: int | None = None
    recorded_at: datetime = datetime.now(timezone.utc)


class EnergyWindow(BaseModel):
    start_hour: int
    end_hour: int
    label: str


class EnergyProfile(BaseModel):
    user_id: str
    peak_windows: list[EnergyWindow]
    low_windows: list[EnergyWindow]
    updated_at: datetime = datetime.now(timezone.utc)
