"""
jobspy.scrapers.Wtj
~~~~~~~~~~~~~~~~~~~

This module contains routines to scrape Welcome to jungle.
"""

from __future__ import annotations

import re
import time
import random
from typing import Optional
from datetime import datetime

from threading import Lock
from bs4.element import Tag
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse

from .. import Scraper, ScraperInput, Site
from ..exceptions import WTJInException
from ..utils import create_session, getElements,getElement,getElementText
from ...jobs import (
    Exp,
    ExpType,
    JobPost,
    Location,
    JobResponse,
    JobType,
    Country,
    Compensation,
    DescriptionFormat,
    CompensationInterval
)
from ..utils import (
    logger,
    extract_emails_from_text,
    get_enum_from_job_type,
    currency_parser,
    markdown_converter,
)
from botasaurus import *
from botasaurus.wait import *
from urllib.parse import urlencode
from time import sleep

@browser(block_images=True,
        block_resources=True,
        parallel=bt.calc_max_parallel_browsers,
        output=None,
        reuse_driver=True,
        close_on_crash=True,
        cache=False,
        keep_drivers_alive=True, 
        headless=True
        )
def search_list(driver: AntiDetectDriver, data):

    # driver.organic_get(BASE_GLASSDOOR_URL+ "Overview/Working-at-" +data, accept_cookies=True)
    #driver.organic_get("https://www.glassdoor.fr/Pr%C3%A9sentation/Travailler-chez-Sopra-Steria-EI_IE466295.16,28.htm", accept_cookies=True)
    driver.organic_get(data, accept_cookies=True)
    sleep(3)
    eltList= driver.get_elements_or_none_by_xpath('*//li[@data-testid="search-results-list-item-wrapper"]')
    return eltList

@browser(block_images=True,
        block_resources=True,
        parallel=5,
        output=None,
        reuse_driver=True,
        close_on_crash=True,
        cache=False,
        keep_drivers_alive=True, 
        headless=True
        )
def process_job(
    driver: AntiDetectDriver, data
) -> Optional[JobPost]:
    driver.organic_get(data, accept_cookies=True)
    
    metadata_card=driver.get_element_or_none_by_selector('[data-testid="job-metadata-block"]')
    salary_tag = getElement(metadata_card, "*//i[@name='salary']/parent::*").text
    compensation = None
    salary_tag=salary_tag.split('\n')[1]
    if salary_tag and salary_tag != "Non spécifié":
        salary_text = salary_tag.strip()
        salary_values = [currency_parser(value) for value in salary_text.split(" à ")]
        salary_min = salary_values[0]
        salary_max = salary_values[1]
        currency = "€"
        compensation = Compensation(
            min_amount=int(salary_min),
            max_amount=int(salary_max),
            currency=currency,
            interval=CompensationInterval.YEARLY
        )

    title = getElementText(metadata_card , "//h2")

    company_a_tag = getElement(metadata_card, "*//a")
    company_url = company_a_tag.get_attribute("href")
    company_tag=getElement(company_a_tag, "//div/span")
    if company_tag:
        company = company_tag.text
    
    location = Location(
                    city=getElement(metadata_card, "*//i[@name='location']/following-sibling::span[1]").text,
                    country=Country.FRANCE,
                )
    
    

    datetime_tag= getElement(metadata_card, "*//time")
    date_posted = description = job_type = None
    if datetime_tag:
        datetime_str = datetime_tag.get_attribute("datetime")
        try:
            subStr=datetime_str.split("T")[0]
            date_posted = datetime.strptime(subStr, "%Y-%m-%d")
        except:
            date_posted = None
    benefits_tag ="" 
    contract_tag = getElement(metadata_card, "*//i[@name='contract']/parent::*")
    job_type=[]
    if contract_tag:
        employment_type = contract_tag.text.strip()
        employment_type=employment_type.split("\n")[0]
        employment_type = employment_type.lower()
        employment_type = employment_type.replace("-", "")
        job_type = [get_enum_from_job_type(employment_type)] 
    remote_tag= getElement(metadata_card, "*//i[@name='remote']/parent::*")
    is_remote=False
    remote_details=None
    if remote_tag  :
        remote_tag_txt=remote_tag.text
        if remote_tag_txt == "Télétravail total":
            is_remote=True
            remote_details="full"
        elif remote_tag_txt == "Télétravail occasionnel":
            is_remote=True
            remote_details="occasionnel"
        elif remote_tag_txt == "Télétravail fréquent":
            is_remote=True
            remote_details="frequent"
        else:
            is_remote=False
    
    education_level_tag= getElement(metadata_card, "*//i[@name='education_level']/parent::*")
    education_level=None
    if education_level_tag:
       value=re.sub("[^-0-9]", "", education_level_tag.text)
       if value == '' and  education_level_tag.text.__contains__("Sans diplôme"):
           education_level=0
       elif value == '':
           print(education_level_tag.text)
       else:
        education_level= int(value)

    description_tag= driver.get_elements_or_none_by_xpath('*//div[@id="the-position-section"]/div/div[2]')
    if len(description_tag) > 0:
        description = markdown_converter(description_tag[0].get_attribute('innerHTML'))


    suitcase_tag= getElement(metadata_card, "*//i[@name='suitcase']/parent::*")
    year_exp=None
    if suitcase_tag:
       splited=suitcase_tag.text.split(" ")
       year_exp= Exp(type= ExpType.get_ExpType(splited[3]), count=int(splited[2]))
    
    return JobPost(
        title=title,
        company_name=company,
        company_url=company_url,
        location=location,
        date_posted=date_posted,
        job_url=data,
        compensation=compensation,
        job_type=job_type,
        description=description,
        is_remote=is_remote,
        emails=extract_emails_from_text(description) if description else None,
        exp=year_exp,
        education_level=education_level,
        remote_details=remote_details
    )

class WTJScraper(Scraper):
    base_url = "https://www.welcometothejungle.com"
    delay = 3
    band_delay = 4
    jobs_per_page = 31

    def __init__(self, proxy: Optional[str] = None):
        """
        Initializes WTJScraper with the WTJ job search url
        """
        super().__init__(Site(Site.WELCOMETOJUNGLE), proxy=proxy)
        self.scraper_input = None
        self.country = "worldwide"

    

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        """
        Scrapes WTJ for jobs with scraper_input criteria
        :param scraper_input:
        :return: job_response
        """
        self.scraper_input = scraper_input
        page = scraper_input.offset // 25 + 25 if scraper_input.offset else 1
        
        range_start = 1 + (scraper_input.offset // self.jobs_per_page)
        tot_pages = (scraper_input.results_wanted // self.jobs_per_page) + 2
        range_end = tot_pages
        all_jobs=[]
        logger.info(f"WTJ start to scrappe from {range_start} to {range_end} ")
        for page in range(range_start, range_end):
            logger.info(f"WTJ search page: {page}")
            try:
                jobs = self._fetch_jobs_page(
                    scraper_input, page
                )
                if jobs:
                    all_jobs.extend(jobs)
                if not jobs or len(all_jobs) >= scraper_input.results_wanted:
                    logger.info(f"WTJ no more jobs")
                    all_jobs = all_jobs[: scraper_input.results_wanted]
                    break
            except Exception as e:
                logger.error(f"WTJ: {str(e)}")
                break
        return JobResponse(jobs=all_jobs)
    
    def _fetch_jobs_page(
        self,
        scraper_input: ScraperInput,
        page_num: int
    ) -> list[JobPost]:
        """
        Scrapes a page of Wtj for jobs with scraper_input criteria
        """
        job_list = []
        self.scraper_input = scraper_input
        params = {
                "refinementList[offices.country_code][]": "FR" ,
                "query": scraper_input.search_term,
                "aroundQuery": scraper_input.location,
                "page":page_num,
            }

        params = {k: v for k, v in params.items() if v is not None}
        try:
            queries= urlencode(dict(params))   
            response= search_list(f"{self.base_url}/fr/jobs?{queries}" )
        except Exception as e:
            if "Proxy responded with" in str(e):
                logger.error(f"Welcome to jungle: Bad proxy")
            else:
                logger.error(f"Welcome to jungle: {str(e)}")
            return JobResponse(jobs=job_list)
            
        if len(response) == 0:
            return JobResponse(jobs=job_list)
        job_in_page=[]
        for job_card in response:
            job_url = None

            href_tag = getElement(job_card, "(*//a)[2]")
            if href_tag and href_tag.get_attribute("href"):
                job_url = href_tag.get_attribute("href")
                job_in_page.append(job_url)

        try:
            job_post = process_job( job_in_page)
            if job_post:
                job_list.extend(job_post)
        except Exception as e:
            raise WTJInException(str(e))

        return job_list

