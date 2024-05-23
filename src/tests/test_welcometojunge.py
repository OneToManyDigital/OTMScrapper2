import logging
from ..jobspyOtm import scrape_jobs
import pandas as pd
LOGGER = logging.getLogger(__name__)

def test_wtj():
    
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)
    result = scrape_jobs(
    site_name=["WelcomeToJungle"],
    search_term="Product manager",
    location="Lyon",
    results_wanted=5, 
    )

    assert (
        isinstance(result, pd.DataFrame) and not result.empty
    ), "Result should be a non-empty DataFrame"
