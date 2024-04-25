import unittest
from ..jobspyOtm import scrape_jobs
import pandas as pd

@unittest.skip('Reason for skipping')
def test_ziprecruiter():
    result = scrape_jobs(
        site_name="zip_recruiter",
        search_term="software engineer",
    )

    assert (
        isinstance(result, pd.DataFrame) and not result.empty
    ), "Result should be a non-empty DataFrame"
