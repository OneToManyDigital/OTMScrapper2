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
from urllib.parse import quote_plus, urlparse, urlunparse

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
from urllib.parse import urlencode
from time import sleep
from lxml import html


class WTJScraper(Scraper):
    base_url = "https://csekhvms53-dsn.algolia.net"
    delay = 3
    band_delay = 4
    jobs_per_page = 30

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
        self.session = create_session(self.proxy, has_retry=True)
        range_start = 0 + (scraper_input.offset // self.jobs_per_page)
        tot_pages = (scraper_input.results_wanted // self.jobs_per_page) 
        range_end = tot_pages + 1
        all_jobs: list[JobPost] = []

        location_lat = location_long= None
        if scraper_input.location:
            location_lat,location_long = self._get_location(scraper_input.location)

        logger.info(f"WTJ start to scrappe from {range_start} to {range_end} ")
        for page in range(range_start, range_end):
            logger.info(f"WTJ search page: {page}")
            try:
                jobs = self._fetch_jobs_page(
                    scraper_input, page,location_long,location_lat
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
        page_num: int,
        location_long: float | None,
        location_lat: float | None
    ) -> list[JobPost] :
        """
        Scrapes a page of Wtj for jobs with scraper_input criteria
        """
        job_list = []
        self.scraper_input = scraper_input
        params = {
                "x-algolia-agent": "Algolia%20for%20JavaScript%20(4.20.0)%3B%20Browser" ,
                "search_origin": "job_search_client"
            }
        serializableInput=quote_plus(scraper_input.search_term)
        payload = '''{"requests":[{"indexName":"wttj_jobs_production_fr","params":"attributesToHighlight=%5B%22name%22%5D&attributesToRetrieve=%5B%22*%22%5D&clickAnalytics=true&hitsPerPage=30&maxValuesPerFacet=999&analytics=true&enableABTest=true&userToken=e8729a0e-7ad4-46ad-896d-c8dab5fe3353&analyticsTags=%5B%22page%3Ajobs_index%22%2C%22language%3Afr%22%5D&facets=%5B%22benefits%22%2C%22contract_type%22%2C%22contract_duration_minimum%22%2C%22contract_duration_maximum%22%2C%22has_contract_duration%22%2C%22education_level%22%2C%22has_education_level%22%2C%22experience_level_minimum%22%2C%22has_experience_level_minimum%22%2C%22organization.nb_employees%22%2C%22organization.labels%22%2C%22salary_yearly_minimum%22%2C%22has_salary_yearly_minimum%22%2C%22salary_currency%22%2C%22followedCompanies%22%2C%22language%22%2C%22new_profession.category_reference%22%2C%22new_profession.sub_category_reference%22%2C%22remote%22%2C%22sectors.parent_reference%22%2C%22sectors.reference%22%5D&filters=(%22offices.country_code%22%3A%22FR%22)&page='''+str(page_num)+ '''&query='''+ serializableInput

        if location_long and location_lat:
            payload = payload + f'&aroundLatLng={location_lat}%2C{location_long}&aroundRadius=20000&aroundPrecision=20000'
  
        payload = payload +'''"}]}'''
        params = {k: v for k, v in params.items() if v is not None}
        try:
            
            queries= urlencode(dict(params))   
            response = self.session.post(
                f"{self.base_url}/1/indexes/*/queries?{queries}",
                timeout_seconds=15,
                headers=self.headers,
                data=payload,
            )
            if response.status_code != 200:
                exc_msg = f"bad response status code: {response.status_code}"
                raise WTJInException(exc_msg)
            res_json = response.json()['results'][0]['hits']
            if "errors" in res_json:
                raise ValueError("Error encountered in API response")
        
        except Exception as e:
            if "Proxy responded with" in str(e):
                logger.error(f"Welcome to jungle: Bad proxy")
            else:
                logger.error(f"Welcome to jungle: {str(e)}")
            return job_list
        for job in res_json:
            try:
                job_post = self.process_job( job)
                if job_post:
                    job_list.append(job_post)
            except Exception as e:
                raise WTJInException(str(e))

      
        return job_list

    def process_job( self,data) -> JobPost | None:
        
        compensation = None

        if data['has_salary_yearly_minimum']:
            salary_min=int(data['salary_yearly_minimum']) if data['salary_yearly_minimum'] else None 
            salary_max=int(data['salary_maximum']) if data['salary_maximum'] else None
            currency = data['salary_currency']
            compensation = Compensation(
                min_amount=salary_min,
                max_amount=salary_max,
                currency=currency,
                interval=CompensationInterval.YEARLY
            )

        title = data['name']
        company = data['organization']
        company_name=""
        company_slug=""
        company_url=""
        if company:
            company_name=company['name']
            company_slug=company['slug']
            company_url=f'https://www.welcometothejungle.com/fr/companies/{company_slug}'

        offices= data['offices']
        location= None
        if offices and len(offices) > 0:
            office = offices[0]
            location = Location(
                            city=office['city'],
                            country=Country.from_string(office['country']),
                            state=office['state']
                        )
        
        

        date_posted = description = job_type = None
        if data['published_at']:
            try:
                subStr=data['published_at'].split("T")[0]
                date_posted = datetime.strptime(subStr, "%Y-%m-%d")
            except:
                date_posted = None
                
        job_type=[]
        if data['contract_type']:
            try:
                employment_type = data['contract_type'].strip()
                employment_type= employment_type.split("\n")[0]
                employment_type = employment_type.lower()
                employment_type = employment_type.replace("-", "")
                employment_type = employment_type.replace("_", "")
                decoded_type = get_enum_from_job_type(employment_type)
                if decoded_type:
                    job_type = [decoded_type] 
            except Exception as e:
                logger.error(f'Cannot found job type for value {data["contract_type"]}')


        is_remote=False
        remote_details=None
        if data['remote']  :
            remote_tag_txt=data['remote']
            if remote_tag_txt == "fulltime":
                is_remote=True
                remote_details="full"
            elif remote_tag_txt == "punctual":
                is_remote=True
                remote_details="occasionnel"
            elif remote_tag_txt == "partial":
                is_remote=True
                remote_details="frequent"
            else:
                is_remote=False
        
        education_level=None
        if data['education_level']:
            txt = data['education_level']
            if txt == "no_diploma":
                education_level=0
            elif txt == "phd":
                education_level= 7
            else:
                value=re.sub("[^-0-9]", "",txt)
                if value != '':
                    education_level= int(value)
        else:
            education_level=0

        job_url=f'https://www.welcometothejungle.com/fr/companies/{company_slug}/jobs/{data["slug"]}?q=8179957587f8d086bec137c526e09a0c&o={data["reference"]}'
        description =self._fetch_job_description(job_url)

        year_exp=None
        if data['experience_level_minimum']:
            year_exp= Exp(type= ExpType.YEAR, count=float( data['experience_level_minimum']))
        
        benefits=None
        if data['benefits'] and len(data['benefits']) > 0:
            benefits = data['benefits']
        
        duration_max=data['contract_duration_minimum']
        duration_min=data['contract_duration_maximum']

        return JobPost(
            title=title,
            company_name=company_name,
            company_url=company_url,
            location=location,
            date_posted=date_posted,
            job_url=job_url,
            compensation=compensation,
            job_type=job_type,
            description=description,
            is_remote=is_remote,
            emails=extract_emails_from_text(description) if description else None,
            exp=year_exp,
            education_level=education_level,
            remote_details=remote_details,
            company_id=company_slug,
            benefits=benefits,
            minDuration=duration_min,
            maxDuration=duration_max
        )
    
    def _fetch_job_description(self, job_url):

        try:
            response = self.session.get(
                job_url,
                timeout_seconds=15,
                headers=self.headers
            )
            if response.status_code != 200:
                exc_msg = f"bad response status code: {response.status_code}"
                raise WTJInException(exc_msg)
            
            tree = html.fromstring(response.content)
        except Exception as e:
            if "Proxy responded with" in str(e):
                logger.error(f"Welcome to jungle Description: Bad proxy")
            else:
                logger.error(f"Welcome to jungle Description: {str(e)}")
            return ""

        tag=tree.xpath('*//div[@id="the-position-section"]/div/div[2]')
        if tag and len(tag) >0 :
            innerHtml=  html.tostring(tag[0])
            return markdown_converter(innerHtml)
        else:
            return ''

    def _get_location(self,locationSearch: str) :
        API_KEK="3YHjVgEYjuwUatQAtD-wTX8lmNXEsULPzC8m59VMGDw"
        try:
            queryEncode=quote_plus(locationSearch)
            response = self.session.get(
                f'https://autocomplete.search.hereapi.com/v1/autocomplete?apiKey={API_KEK}&q={queryEncode}&lang=fr&limit=1',
                timeout_seconds=15,
                headers=self.headers
            )
            if response.status_code != 200:
                exc_msg = f"bad response status code: {response.status_code}"
                raise WTJInException(exc_msg)
            
            placeId = response.json()['items'][0]['id']

            response = self.session.get(
                f'https://lookup.search.hereapi.com/v1/lookup?apiKey={API_KEK}&lang=en&id={placeId}',
                timeout_seconds=15,
                headers=self.headers
            )
            if response.status_code != 200:
                exc_msg = f"bad response status code: {response.status_code}"
                raise WTJInException(exc_msg)
            re_json=response.json()
            return re_json['position']['lat'],re_json['position']['lng']

        except Exception as e:
            if "Proxy responded with" in str(e):
                logger.error(f"Welcome to jungle location: Bad proxy")
            else:
                logger.error(f"Welcome to jungle location: {str(e)}")
            return None,None
        
    headers = {
        "authority": "www.glassdoor.com",
        "accept": "*/*",
        "accept-language": "fr-FR,fr;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.welcometothejungle.com",
        "referer": "https://www.welcometothejungle.com/",
        "sec-ch-ua": '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "X-Algolia-Api-Key": "4bd8f6215d0cc52b26430765769e65a0",
        "X-Algolia-Application-Id": "CSEKHVMS53",
    }