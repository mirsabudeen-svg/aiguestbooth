from pydantic import BaseModel


class HourlyBucket(BaseModel):
    hour: int
    count: int


class BoothBucket(BaseModel):
    booth_id: str
    booth_name: str
    count: int


class TagBucket(BaseModel):
    tag: str
    count: int


class AnalyticsOverview(BaseModel):
    event_id: str
    event_name: str
    total_messages: int
    starred_count: int
    with_snapshot_count: int
    by_hour: list[HourlyBucket]
    by_booth: list[BoothBucket]
    top_tags: list[TagBucket]
