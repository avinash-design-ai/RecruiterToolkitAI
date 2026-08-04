from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from pydantic import BaseModel

from modules.PrevailingWageCalculator.flc_scraper import FLCScraper

router = APIRouter()

executor = ThreadPoolExecutor(max_workers=2)


class CityRequest(BaseModel):
    city: str


def scrape(city):

    scraper = FLCScraper()

    try:
        return scraper.get_wages(city)

    finally:
        scraper.close()


@router.post("/wage")
async def get_wage(request: CityRequest):

    future = executor.submit(
        scrape,
        request.city
    )

    return future.result()
