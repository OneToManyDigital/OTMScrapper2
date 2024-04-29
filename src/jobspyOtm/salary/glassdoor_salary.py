import json
import logging
import re
from typing import Optional
from pandas import DataFrame
import pandas as pd
import requests
from  ..jobs import Country
from . import JobInput, SalaryResponse,Salary
from ..scrapers.utils import create_session
    
LOGGER = logging.getLogger(__name__)

class GlassdoorSalaryScraper():
    def __init__(self, proxy: Optional[str] = None):
        """
        Initializes GlassdoorScraper with the Glassdoor job search url
        """
        self.proxy=proxy
        self.base_url=None

    def _scrape(self, jobTilte: str, country : Country) -> Salary:
        url = f"{self.base_url}/graph"
        body = [
            {
                "operationName": "SalarySearchFAQsQuery",
                "variables": {
                    "jobTitle": jobTilte,
                    "domain": country.get_glassdoor_url(),
                    "useUgcSearch2ForSalaries": "true",
                    "enableV3Estimates": False,
                    "stateId": None,
                    "cityId":None,
                    "countryId":None,
                    "metroId": None
                },
                "locale": "fr-FR",
                "query": """
                     query SalarySearchFAQsQuery(
                        $cityId: Int,
                        $countryId: Int, 
                        $metroId: Int, 
                        $stateId: Int, 
                        $jobTitle: String!) 
                        {  occSalaryEstimates(
                                    occSalaryEstimatesInput: {jobTitle: {text: $jobTitle}, location: {cityId: $cityId, metroId: $metroId, stateId: $stateId, countryId: $countryId}}
                                        ) {
                                                  additionalPayPercentiles {
                                                                value
                                                                percentile     
                                                                __typename
                                                                        }
                                                   basePayPercentiles {     
                                                            value
                                                            percentile
                                                            __typename
                                                                    }
                                                    currency {
                                                            code
                                                            __typename
                                                                    }
                                                    jobTitle {
                                                            id
                                                            text
                                                            sgocId
                                                            __typename
                                                                    }    
                                                    payPeriod
                                                          queryLocation {
                                                                        id
                                                                        name      
                                                                        type
                                                                        __typename
                                                                                }    
                                                           salariesCount
                                                           totalPayPercentiles {
                                                                        value
                                                                        percentile
                                                                        __typename
                                                                                }
                                                            __typename
                                                                }
                                                                }

                """,
            }
        ] 
        res = self.session.post(url,
                                 data=json.dumps(body), 
                                headers=self.headers,
                timeout_seconds=15)
        if res.status_code != 200:
            LOGGER.error(f'Error when call salary for {jobTilte} result : {res}')
            return None
        res_json = res.json()[0]
        if res_json == None or res_json["data"]== None or  res_json["data"]["occSalaryEstimates"] == None:
            return None
        salary_data = res_json["data"]["occSalaryEstimates"]["basePayPercentiles"]
        if salary_data == None:
            return None
        currency = res_json["data"]["occSalaryEstimates"]['currency']['code']
        payPeriod = res_json["data"]["occSalaryEstimates"]['payPeriod']
        location = res_json["data"]["occSalaryEstimates"]['queryLocation']['name']
        nameRes = res_json["data"]["occSalaryEstimates"]['jobTitle']['text']
        min_val= None
        max_val= None
        for salary in salary_data:
            if salary['percentile'] == 'P_25TH':
                min_val =salary['value']
            elif salary['percentile'] == 'P_75TH':
                max_val =salary['value']
        return Salary(name=nameRes,min_val=min_val,max_val=max_val, currency=currency,payPeriod=payPeriod,location=location)


    def scrapeList(self, jobTitleList:  list[JobInput], country: Country = Country.FRANCE) -> SalaryResponse:
        
        self.base_url=country.get_glassdoor_url()
        self.session = create_session(self.proxy, is_tls=True, has_retry=True)
        token = self._get_csrf_token()
        self.headers["gd-csrf-token"] = token if token else self.fallback_token

        salaryList=[]
        for job in jobTitleList:
            jobTitleFixed = job.name.replace("(H/F)", "")
            jobTitleFixed = jobTitleFixed.replace("(F/H)", "")
            jobTitleFixed = jobTitleFixed.replace("(se)", "")
            jobTitleFixed = jobTitleFixed.replace("(e)", "")
            jobTitleFixed = jobTitleFixed.replace("H/F", "")
            jobTitleFixed = jobTitleFixed.replace("F/H", "")
            jobTitleFixed = jobTitleFixed.replace("F/H/X", "")
            
            jobTitleFixed = jobTitleFixed.replace(".euse", "")
            jobTitleFixed = jobTitleFixed.replace("/Euse", "")
           
            
            jobTitleFixed = jobTitleFixed.strip()
            jobTitleFixed = jobTitleFixed.lower()
            tmpSalary= []
            
            if jobTitleFixed.__contains__(" - "):
                subJobTitle= jobTitleFixed.split(" - ")
                for subJob in subJobTitle:
                    subJob= subJob.strip()
                    subJob= subJob.replace("-", " ")
                    if subJob.__contains__("/"):
                        subSubJobTitle= jobTitleFixed.split("/")
                        for subSubJob in subSubJobTitle:
                            subSubJob= subSubJob.strip()
                            tmpSalary.append(self._scrape(jobTilte=subSubJob,country=country))
                    else:
                        tmpSalary.append(self._scrape(jobTilte=subJob,country=country))
            else:
                tmpSalary.append(self._scrape(jobTilte=jobTitleFixed,country=country))
            
            if all(x is None for x in tmpSalary):
                LOGGER.error(f'Cannot found salary for job {job.name}')
            else:
                tmpSalary=[obj for obj in tmpSalary if obj is not None]
                for salary in tmpSalary:
                    salary.jobId = job.jobId
                    salary.fullJobName = job.name
                salaryList.extend(tmpSalary)
             
        return SalaryResponse(salaryList=salaryList)
        


    def _get_csrf_token(self):
        """
        Fetches csrf token needed for API by visiting a generic page
        """
        res = self.session.get(
            f"{self.base_url}/Job/computer-science-jobs.htm", headers=self.headers
        )
        pattern = r'"token":\s*"([^"]+)"'
        matches = re.findall(pattern, res.text)
        token = None
        if matches:
            token = matches[0]
        return token

    headers = {
        "authority": "www.glassdoor.fr",
        "accept": "*/*",
        "accept-language": "fr-FR,fr;q=0.9",
        "apollographql-client-name": "salary-search",
        "apollographql-client-version": "10.27.8",
        "content-type": "application/json",
        "origin": "https://www.glassdoor.fr",
        "referer": "https://www.glassdoor.fr/",
        "sec-ch-ua": '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    }