from ..jobspy import scrape_jobs
import pandas as pd


def test_ziprecruiter():
    result = scrape_jobs(
    site_name=["WelcomeToJungle"],
    search_term="développeur",
    location="Paris, France",
    results_wanted=5, 
    )

    assert (
        isinstance(result, pd.DataFrame) and not result.empty
    ), "Result should be a non-empty DataFrame"
