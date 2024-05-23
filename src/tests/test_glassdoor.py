import logging
from ..jobspyOtm import scrape_jobs
import pandas as pd


LOGGER = logging.getLogger(__name__)
def test_glassdoor():
    result = scrape_jobs(
        site_name="glassdoor", search_term="software engineer", country_indeed="USA"
    )
    LOGGER.error(result)
    assert (
        isinstance(result, pd.DataFrame) and not result.empty
    ), "Result should be a non-empty DataFrame"
