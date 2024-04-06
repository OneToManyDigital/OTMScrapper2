from botasaurus import *
from botasaurus.wait import *
from ..company import CompanyResponse, CompanyDescr, CompanySite
from ..scrapers.utils import getElementText,getElement, markdown_converter


BASE_URL="https://fr.indeed.com/cmp/"

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

    def scrape(self, companyList:  list[str]) -> CompanyResponse:
        all_company: list[CompanyDescr] = []
        for company in companyList:
            if company is None or company == "":
                continue
            __company= company.replace(" ", "-")
            result = scrape_details_task(__company)
            if result:
                all_company.append(result)
        return CompanyResponse(companyList=all_company)
