
from typing import Optional
from datetime import date
from enum import Enum
from pydantic import BaseModel

class CompanyDescr(BaseModel):
    name: str | None = None
    url: str | None = None
    company_url: str | None = None
    headquarters: str | None = None
    size: str | None = None
    founded: str | None = None
    type_of_ownership:  str | None = None

    sector: str | None = None
    revenue: str | None = None
    competitors: str | None = None

    socials: list[str] | None = None
    description: str | None =None
    manPercentage: int | None = None
    womanPercentage: int | None = None
    averageAge: int | None = None
    goodToKnow: str | None = None
    lookingFor: str | None = None
    benefits: list[str]| None = None
    turnover: int | None = None
    bestPlacesToWork: list[str] | None = None


class CompanyResponse(BaseModel):
    companyList: list[CompanyDescr] = []


class CompanySite(Enum):
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    WELCOMETOJUNGLE = "WelcomeToJungle"

class CompanyInput(BaseModel):
    id: str | None = None
    name: str 
    site: str