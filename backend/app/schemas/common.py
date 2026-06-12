from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
