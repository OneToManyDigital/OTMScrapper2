
import json
import logging
import re
from typing import Optional

from ..scrapers.utils import create_session

from ..jobs import Country
from ..company import CompanyResponse, CompanyDescr, CompanySite

LOGGER = logging.getLogger(__name__)


class GlassdoorCpyScraper():

    def __init__(self, proxy: Optional[str] = None):
        """
        Initializes GlassdoorScraper with the Glassdoor job search url
        """
        self.proxy=proxy
        self.base_url=None
        
    def scrape(self, companyIdList:  list[str], country: Country) -> CompanyResponse:
        self.base_url=country.get_glassdoor_url()
        self.session = create_session(self.proxy, is_tls=True, has_retry=True)
        token = self._get_csrf_token()
        self.headers["gd-csrf-token"] = token if token else self.fallback_token

        all_company: list[CompanyDescr] = []
        for company in companyIdList:
            if company is None or company == "":
                continue
            result = self._search_company(company)
            if result:
                all_company.append(result)
        return CompanyResponse(companyList=all_company)
    
        
    def _scrape_details_task(self, data):
        mainData = data[0]['data']['employer']
        if mainData is None:
            return None
        headquarters =  mainData['headquarters']
        size = mainData['size']
        name = mainData['shortName']
        type_of_ownership= mainData['type']
        founded= str(mainData['yearFounded']) if mainData['yearFounded'] else None
        revenue=mainData['type']
        sector=mainData['primaryIndustry']['industryName'] if mainData['primaryIndustry']  else None
        competitors = []
        dataInJson =mainData['competitors']
        if dataInJson:
            for data in dataInJson:
                competitors.append(data['shortName'])
        bestPlacesToWork = []
        dataInJson=mainData['bestPlacesToWorkAwards']
        if dataInJson:
            for data in dataInJson:
                bestPlacesToWork.append(f'{data["rank"]}__{data["timePeriod"]}')

        return CompanyDescr (
            name= name,
            headquarters= headquarters,
            size=size,
            founded=founded,
            type_of_ownership= type_of_ownership,
            sector= sector,
            revenue=revenue,
            competitors=", ".join(competitors) if competitors and len(competitors) > 0 else None,
            bestPlacesToWork= bestPlacesToWork
        )

    def _search_company(self, companyId : str):

        url = f"{self.base_url}/graph"
        body = [
            {
                "operationName": "EmployerBaseDataQueryWithTld",
                "variables": {
                    "employerId": int(companyId),
                    "isLoggedIn": True,
                    "isROWProfile": False
                },
                "locale": "fr-FR",
                "query": """query EmployerBaseDataQueryWithTld($employerId: Int!, $isLoggedIn: Boolean!, $isROWProfile: Boolean!, $tldId: Int) {
                                employer(id: $employerId) {
                                    id
                                    shortName
                                    website(useRow: $isROWProfile, useTld: $tldId)
                                    type
                                    revenue(useRow: $isROWProfile, useTld: $tldId)
                                    headquarters(useRow: $isROWProfile, useTld: $tldId)
                                    size(useRow: $isROWProfile, useTld: $tldId)
                                    stock
                                    squareLogoUrl(size: SMALL)
                                    officeAddresses {
                                    id
                                    __typename
                                    }
                                    primaryIndustry {
                                    industryId
                                    industryName
                                    sectorId
                                    __typename
                                    }
                                    yearFounded
                                    overview {
                                    description
                                    mission
                                    __typename
                                    }
                                    links {
                                    manageoLinkData {
                                        url
                                        urlText
                                        employerSpecificText
                                        __typename
                                    }
                                    faqUrl
                                    __typename
                                    }
                                    bestPlacesToWorkAwards: bestPlacesToWork(onlyCurrent: false, limit: 30) {
                                    id
                                    name
                                    rank
                                    timePeriod
                                    __typename
                                    }
                                    legalActionBadges {
                                    headerText
                                    bodyText
                                    __typename
                                    }
                                    competitors {
                                    shortName
                                    __typename
                                    }
                                    __typename
                                }
                                getCompanyFollowsForUser @include(if: $isLoggedIn) {
                                    employer {
                                    id
                                    __typename
                                    }
                                    follow
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
            LOGGER.error(f'Error when call company glassdoor for {companyId} result : {res}')
            return None
        res_json = res.json()
    
        return self._scrape_details_task(res_json)
    
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
    
    fallback_token = "Ft6oHEWlRZrxDww95Cpazw:0pGUrkb2y3TyOpAIqF2vbPmUXoXVkD3oEGDVkvfeCerceQ5-n8mBg3BovySUIjmCPHCaW0H2nQVdqzbtsYqf4Q:wcqRqeegRUa9MVLJGyujVXB7vWFPjdaS1CtrrzJq-ok"
    
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