
from pydantic import BaseModel

class Salary(BaseModel):
    jobId: str | None = None
    name: str 
    min_val: float | None = None
    max_val: float | None = None
    payPeriod: str | None = None
    currency: str | None = None
    location: str | None = None
    exp: int = -1

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name and self.min_val == other.min_val and self.max_val == other.max_val and self.payPeriod == other.payPeriod and self.currency == other.currency and self.location == other.location
        return False

class SalaryResponse(BaseModel):
    salaryList: list[Salary] = []

class JobInput(BaseModel):
    jobId: str
    name: str

