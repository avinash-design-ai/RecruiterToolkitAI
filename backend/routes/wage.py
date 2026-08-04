from fastapi import APIRouter
from pydantic import BaseModel

from modules.PrevailingWageCalculator.flc_scraper import FLCScraper

router = APIRouter()


class CityRequest(BaseModel):
    city: str


@router.post("/wage")
def get_wage(request: CityRequest):

    scraper = FLCScraper()

    try:
        result = scraper.get_wages(request.city)
        return result

    finally:
        scraper.close()
