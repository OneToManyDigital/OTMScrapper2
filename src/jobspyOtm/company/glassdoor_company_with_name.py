
from botasaurus import browser,AntiDetectDriver,bt
from . import CompanyResponse, CompanyDescr, CompanySite
from typing import Optional


BASE_GLASSDOOR_URL="https://www.glassdoor.fr/"

@browser(block_images=True,
         block_resources=True,
         output=None,
        close_on_crash=True,
        cache=False,
        headless=True,
         )
def scrape_details_task(driver: AntiDetectDriver, data):
    driver.organic_get(data, accept_cookies=True)
    listELement= driver.get_elements_or_none_by_xpath('*//ul[@data-test="companyDetails"]//li')

    headquarters=size=type_of_ownership = founded =revenue =sector =""
    if listELement != None and len(listELement) > 0:
        headquarters =  listELement[1].text
        size = listELement[2].text
        if len(listELement) > 4:
            type_of_ownership =  listELement[4].text
        #industry =  getElementText(info,'//label[text()="Industry"]//following-sibling::*')
        if len(listELement) > 5:
            founded = listELement[5].text
        if len(listELement) > 6:
            revenue =   listELement[6].text
        if len(listELement) > 7:
            sector = listELement[7].text
    competitors = driver.get_elements_or_none_by_xpath('*//span[@class=" employer-overview__employer-overview-module__employerCompetitorsList"]')
    socialLink =driver.get_elements_or_none_by_xpath('*//div[@id="SocialMediaBucket"]/a')
    hrefList=[]
    if socialLink:
        for link in socialLink: 
            hrefList.append(link.get_attribute("href"))
    return CompanyDescr (
         url = data,
         headquarters= headquarters,
         size=size,
         founded=founded,
         type_of_ownership= type_of_ownership,
         sector= sector,
         revenue=revenue,
         competitors=competitors,
         socials=hrefList
    )

@browser(block_images=True,
         block_resources=True,
         output=None,
        close_on_crash=True,
        cache=False,
        headless=True
         )
def search_company(driver: AntiDetectDriver, data):

    # driver.organic_get(BASE_GLASSDOOR_URL+ "Overview/Working-at-" +data, accept_cookies=True)
    #driver.organic_get("https://www.glassdoor.fr/Pr%C3%A9sentation/Travailler-chez-Sopra-Steria-EI_IE466295.16,28.htm", accept_cookies=True)
    driver.organic_get(f'{BASE_GLASSDOOR_URL}/Avis/{data}-avis-SRCH_KE0,5.htm', accept_cookies=True)
    resultElements =driver.get_elements_or_none_by_xpath('//h2/a')
    details=None
    if resultElements != None and len(resultElements) > 0:
           details= scrape_details_task(resultElements[0].get_attribute("href"), proxy = driver.config.proxy)
   
    return details

class GlassdoorCpyScraperWithName():
    def __init__(self, proxy: Optional[str] = None):
        """
        Initializes GlassdoorCpyScraperWithName with the Glassdoor job search url
        """
        self.proxy=proxy[:-1] if proxy.endswith('/') else proxy

    def scrape(self, companyList:  list[str]) -> CompanyResponse:
        all_company: list[CompanyDescr] = []
        for company in companyList:
            if company is None or company == "":
                continue
            __company= company.replace(" ", "-")
            result = search_company(__company,  proxy=self.proxy)
            if result:
                result.name = company
                all_company.append(result)
        return CompanyResponse(companyList=all_company)