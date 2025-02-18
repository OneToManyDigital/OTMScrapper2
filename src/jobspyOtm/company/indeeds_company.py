
from botasaurus import browser,AntiDetectDriver,bt
from ..company import CompanyResponse, CompanyDescr, CompanySite
from ..scrapers.utils import getElementText,getElement, markdown_converter
from typing import Optional


BASE_URL="https://fr.indeed.com/cmp/"

@browser(block_images=True,
         block_resources=True,
         output=None,
        close_on_crash=True,
        cache=False,
        headless=True
         )
def scrape_details_task(driver: AntiDetectDriver, data):
    driver.organic_get(BASE_URL+data, accept_cookies=True)

    # Retrieve the heading element's text
   # eltList = driver.get_elements_or_none_by_selector(".sh-dgr__content")
    sections =driver.get_elements_or_none_by_xpath('*//section[@data-testid="AboutSection-section"]')
    if sections == None:
        return None
    nameDiv = driver.get_element_or_none('*//div[@itemprop="name"]')
    name=''
    if nameDiv :
        name= nameDiv.text
    
    section = sections[0]
    date_founded=getElementText(section,'*//li[@data-testid="companyInfo-founded"]/div[2]')
    revenue=getElementText(section,'*//li[@data-testid="companyInfo-revenue"]/div[2]')
    industry=getElementText(section,'*//li[@data-testid="companyInfo-industry"]/div[2]')
    headquarters=getElementText(section,'*//li[@data-testid="companyInfo-headquartersLocation"]/span')
    size=getElementText(section,'*//li[@data-testid="companyInfo-employee"]/div[2]')

    description_tag=getElement(section,'*//div[@data-testid="more-text"]')
#li data-testid="companyInfo-industry" 2div  a text (href pour récupérer les autres du même type en anglais)
#     #div data-testid="more-text" (tou recupérer les text)
    description=None
    if description_tag:
        description = markdown_converter(description_tag.get_attribute('innerHTML'))
    return CompanyDescr (
         name =name,
         size= size,
         url = BASE_URL+data,
         headquarters= headquarters,
         founded=date_founded,
         sector= industry,
         revenue=revenue,
         description=description
    )


class IndeedCpyScraper():
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
            result = scrape_details_task(__company,  proxy=self.proxy)
            if result:
                all_company.append(result)
        return CompanyResponse(companyList=all_company)
