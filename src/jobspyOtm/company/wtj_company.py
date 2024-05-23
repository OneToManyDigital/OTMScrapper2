import re
from botasaurus import browser,AntiDetectDriver,bt
from ..company import CompanyResponse, CompanyDescr, CompanySite
from ..scrapers.utils import getElementText,getElement,getElementsText,getElements, markdown_converter
from typing import Optional


@browser(block_images=True,
         block_resources=True,
         output=None,
        close_on_crash=True,
        cache=False,
        headless=True
         )
def search_company(driver: AntiDetectDriver, data):

    driver.organic_get(f'https://www.welcometothejungle.com/fr/companies/{data}', accept_cookies=True)
    content = driver.get_element_or_none_by_selector('[data-testid="organization-page-profile"]')
    header = driver.get_element_or_none_by_selector('[data-testid="showcase-header"]')
    # extract infos on company ANNÉE DE CRÉATION
    # TODO : use html to markdown to get all text 
    creationDate= getElementText(content, '*//span[@data-testid="stats-creation-year"]')
    employees =  getElementText(content, '*//span[@data-testid="stats-nb-employees"]')
    manPercentage_tag= getElementText(content, '*//span[@data-testid="stats-parity-men"]')
    turnover=womanPercentage=averageAge=manPercentage=None
    if manPercentage_tag:
        manPercentage=re.sub("[^-0-9]", "", manPercentage_tag)
    womanPercentage_tag= getElementText(content, '*//span[@data-testid="stats-parity-women"]')
    if womanPercentage_tag:
        womanPercentage=re.sub("[^-0-9]", "", womanPercentage_tag)
    averageAge_tag= getElementText(content, '*//span[@data-testid="stats-average-age"]')
    if averageAge_tag:
        averageAge=re.sub("[^-0-9]", "", averageAge_tag)
    turnover_tag= getElementText(content, '*//span[@ data-testid="stats-turnover"]')
    if turnover_tag:
        turnover=re.sub("[^-0-9]", "", turnover_tag)

       
    sideBar = driver.get_element_or_none_by_selector('[data-testid="organization-page-profile-column-sidebar"]')
    goodToKnow=presentation=lookingFor=None
    if sideBar:
        presentation_tag=getElement(sideBar, '(*//div[@data-testid="organization-content-block-text"])[1]')
        if presentation_tag: 
            presentation = markdown_converter(presentation_tag.get_attribute('innerHTML'))
        lookingFor_tag=getElement(sideBar, '(*//div[@data-testid="organization-content-block-text"])[2]')
        if lookingFor_tag: 
            lookingFor = markdown_converter(lookingFor_tag.get_attribute('innerHTML'))
        goodToKnow_tag=getElement(sideBar, '(*//div[@data-testid="organization-content-block-text"])[3]')
        if goodToKnow_tag: 
            goodToKnow = markdown_converter(goodToKnow_tag.get_attribute('innerHTML'))
    sector=getElementText(header, '*//div[@data-testid="showcase-header-sector"]/p')
    location=getElementText(header, '*//div[@data-testid="showcase-header-office"]')
    urlELemnt =getElement(header, '*//div[@data-testid="showcase-header-website"]/p/a')
    url =""
    if urlELemnt:
     url=urlELemnt.get_attribute("href")


    socialLinks= []
    social_tags=driver.get_element_or_none_by_selector('[data-testid="organization-content-block-social-networks"]')
    
    if social_tags:
        socialList =getElements(social_tags, "*//a")
        for social_tag in  socialList:
            socialLinks.append(social_tag.get_attribute("href"))


    link = driver.get_element_or_none_by_selector('[data-testid="organization-nav-link-les"]')
    if link == None:
        return {}
    link.click()
    principalElt=driver.get_element_or_none_by_selector('[data-testid="organization-page-lesplus-1-column-main"]')
    if principalElt == None:
        # old version 
        principalElt=driver.get_element_or_none_by_selector('[data-testid="organization-page-les-plus-column-main"]')
        if principalElt == None:
            return {}

    resultElements = getElements(principalElt,'*//div[@data-testid="organization-content-block-text-v2"]')
    result=[]
    if resultElements:
        for elt in resultElements:
            result.append(markdown_converter(elt.get_attribute('innerHTML')))
    resultElements = getElements(principalElt,'*//div[@data-testid="organization-content-block-text"]')
    if resultElements:
        for elt in resultElements:
            result.append(markdown_converter(elt.get_attribute('innerHTML')))
    resultElements = getElements(principalElt,'*//div[@data-testid="organization-content-block-number-v2"]')
    if resultElements:
        for elt in resultElements:
            result.append(markdown_converter(elt.get_attribute('innerHTML')))
    resultElements = getElements(principalElt,'*//div[@data-testid="organization-content-block-image-with-text-v2"]')
    if resultElements:
        for elt in resultElements:
            result.append(markdown_converter(elt.get_attribute('innerHTML')))
    
    return CompanyDescr (
         name =data,
         size= employees,
         url= f'https://www.welcometothejungle.com/fr/companies/{data}',
         company_url = url,
         headquarters= location,
         founded=creationDate,
         sector= sector,
         description=presentation,
         manPercentage =manPercentage,
         womanPercentage=womanPercentage,
         averageAge=averageAge,
         socials=socialLinks,
         goodToKnow=goodToKnow,
         lookingFor = lookingFor,
         benefits=result,
         turnover=turnover
    )

from unidecode import unidecode
class WTJCpyScraper():
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
            __company = __company.lower()
            __company = unidecode(__company)
            result = search_company(__company,  proxy=self.proxy)
            if result:
                result.name = company
                all_company.append(result)
        return CompanyResponse(companyList=all_company)