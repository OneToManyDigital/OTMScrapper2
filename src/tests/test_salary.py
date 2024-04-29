import logging

from src.jobspyOtm import scrape_salary
from ..jobspyOtm.salary.glassdoor_salary import GlassdoorSalaryScraper
from ..jobspyOtm.salary import JobInput, Salary,SalaryResponse
from ..jobspyOtm.scrapers import Country
import pandas as pd

LOGGER = logging.getLogger(__name__)

def _test_salary():
    result = GlassdoorSalaryScraper().scrapeList(jobTitleList=["Fullstack Developer"], country= Country.FRANCE
    )
    assert result == SalaryResponse(salaryList=[Salary(name="Fullstack Developer", min=38321.849609375, max=50000, payPeriod='ANNUAL', currency='EUR', location='France')])



def test_multiple():
    # Load sub sector scrapper 
    jobs_list = pd.read_csv('./src/tests/jobs_list.csv', low_memory=False)
    filtered_df = jobs_list[jobs_list['max_amount'].notna()]
    sample=filtered_df.sample(50)
    inputs = []
    for index, row in sample.iterrows():
        job = JobInput(jobId= row['id'], name=row['title'])
        inputs.append(job)
    result = scrape_salary(jobInputList=inputs)
    #LOGGER.error(f'Job {sample['title'].item()} company {sample['company'].item()}  Min amount : {sample['min_amount'].item()} and max amount {sample['max_amount'].item()} result glassdoor {result}')
    LOGGER.error(result)
    assert len(result) == 2

