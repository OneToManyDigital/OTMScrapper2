import logging

from ..jobspyOtm.company import CompanyInput

from ..jobspyOtm import scrape_company
from ..jobspyOtm.scrapers import Country
import pandas as pd

LOGGER = logging.getLogger(__name__)

def test_company():

    result = scrape_company(companyList=[CompanyInput(id="327894", name="Urbanlinker"),CompanyInput( name="Sopra Steria")]
    )
    LOGGER.error(result)
    assert 1 ==2
    assert (
        isinstance(result, pd.DataFrame) and not result.empty
    ), "Result should be a non-empty DataFrame"
