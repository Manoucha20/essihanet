from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    file_url: str
    type: str
    patient_id: str