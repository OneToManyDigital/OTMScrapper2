from __future__ import annotations

import pandas as pd
from typing import Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .salary.glassdoor_salary import GlassdoorSalaryScraper

from .salary import JobInput, SalaryResponse, SalarySite
from .jobs import JobType, Location
from .scrapers.utils import logger, set_logger_level
from .scrapers.indeed import IndeedScraper
from .scrapers.ziprecruiter import ZipRecruiterScraper
from .scrapers.glassdoor import GlassdoorScraper
from .scrapers.linkedin import LinkedInScraper
from .scrapers.wtj import WTJScraper
from .scrapers import ScraperInput, Site, JobResponse, Country
from .company import CompanyInput, CompanySite,CompanyResponse
from .company.glassdoor_company_with_name import  GlassdoorCpyScraperWithName
from .company.glassdoor_company import  GlassdoorCpyScraper
from .company.indeeds_company import IndeedCpyScraper
from .company.wtj_company import WTJCpyScraper

from .scrapers.exceptions import (
    LinkedInException,
    IndeedException,
    ZipRecruiterException,
    GlassdoorException,
)
import importlib.metadata

__version__ = importlib.metadata.version("python-jobspy-otm")

def scrape_jobs(
    site_name: str | list[str] | Site | list[Site] | None = None,
    search_term: str | None = None,
    location: str | None = None,
    distance: int | None = 50,
    is_remote: bool = False,
    job_type: str | None = None,
    easy_apply: bool | None = None,
    results_wanted: int = 15,
    country_indeed: str = "usa",
    hyperlinks: bool = False,
    proxy: str | None = None,
    description_format: str = "markdown",
    linkedin_fetch_description: bool | None = False,
    linkedin_company_ids: list[int] | None = None,
    offset: int | None = 0,
    hours_old: int = None,
    verbose: int = 2,
    **kwargs,
) -> pd.DataFrame:
    """
    Simultaneously scrapes job data from multiple job sites.
    :return: pandas dataframe containing job data
    """
    SCRAPER_MAPPING = {
        Site.LINKEDIN: LinkedInScraper,
        Site.INDEED: IndeedScraper,
        Site.ZIP_RECRUITER: ZipRecruiterScraper,
        Site.GLASSDOOR: GlassdoorScraper,
        Site.WELCOMETOJUNGLE: WTJScraper
    }
    set_logger_level(verbose)

    def map_str_to_site(site_name: str) -> Site:
        return Site[site_name.upper()]

    def get_enum_from_value(value_str):
        for job_type in JobType:
            if value_str in job_type.value:
                return job_type
        raise Exception(f"Invalid job type: {value_str}")

    job_type = get_enum_from_value(job_type) if job_type else None

    def get_site_type():
        site_types = list(Site)
        if isinstance(site_name, str):
            site_types = [map_str_to_site(site_name)]
        elif isinstance(site_name, Site):
            site_types = [site_name]
        elif isinstance(site_name, list):
            site_types = [
                map_str_to_site(site) if isinstance(site, str) else site
                for site in site_name
            ]
        return site_types

    country_enum = Country.from_string(country_indeed)

    scraper_input = ScraperInput(
        site_type=get_site_type(),
        country=country_enum,
        search_term=search_term,
        location=location,
        distance=distance,
        is_remote=is_remote,
        job_type=job_type,
        easy_apply=easy_apply,
        description_format=description_format,
        linkedin_fetch_description=linkedin_fetch_description,
        results_wanted=results_wanted,
        linkedin_company_ids=linkedin_company_ids,
        offset=offset,
        hours_old=hours_old,
    )

    def scrape_site(site: Site) -> Tuple[str, JobResponse]:
        scraper_class = SCRAPER_MAPPING[site]
        scraper = scraper_class(proxy=proxy)
        scraped_data: JobResponse = scraper.scrape(scraper_input)
        cap_name = site.value.capitalize()
        site_name = "ZipRecruiter" if cap_name == "Zip_recruiter" else cap_name
        logger.info(f"{site_name} finished scraping")
        return site.value, scraped_data

    site_to_jobs_dict = {}

    def worker(site):
        site_val, scraped_info = scrape_site(site)
        return site_val, scraped_info

    with ThreadPoolExecutor() as executor:
        future_to_site = {
            executor.submit(worker, site): site for site in scraper_input.site_type
        }

        for future in as_completed(future_to_site):
            site_value, scraped_data = future.result()
            site_to_jobs_dict[site_value] = scraped_data

    jobs_dfs: list[pd.DataFrame] = []

    for site, job_response in site_to_jobs_dict.items():
        for job in job_response.jobs:
            job_data = job.model_dump()
            job_url = job_data["job_url"]
            job_data["job_url_hyper"] = f'<a href="{job_url}">{job_url}</a>'
            job_data["site"] = site
            job_data["company"] = job_data["company_name"]
            job_data["job_type"] = (
                ", ".join(job_type.value[0] for job_type in job_data["job_type"])
                if job_data["job_type"]
                else None
            )
            job_data["emails"] = (
                ", ".join(job_data["emails"]) if job_data["emails"] else None
            )
            job_data["benefits"] = (
                ", ".join(job_data["benefits"]) if job_data["benefits"] else None
            )
            
            if job_data["location"]:
                job_data["location"] = Location(
                    **job_data["location"]
                ).display_location()

            compensation_obj = job_data.get("compensation")
            if compensation_obj and isinstance(compensation_obj, dict):
                job_data["interval"] = (
                    compensation_obj.get("interval").value
                    if compensation_obj.get("interval")
                    else None
                )
                job_data["min_amount"] = compensation_obj.get("min_amount")
                job_data["max_amount"] = compensation_obj.get("max_amount")
                job_data["currency"] = compensation_obj.get("currency", "USD")
            else:
                job_data["interval"] = None
                job_data["min_amount"] = None
                job_data["max_amount"] = None
                job_data["currency"] = None

            exp_obj = job_data.get("exp")
            if exp_obj and isinstance(exp_obj, dict):
                job_data["exp_count"] = exp_obj.get("count")
                job_data["exp_type"] = exp_obj.get("type").value
            else:
                job_data["exp_count"] = None
                job_data["exp_type"] = None
            job_data['version_scraper'] =__version__
            job_df = pd.DataFrame([job_data])
            jobs_dfs.append(job_df)

    if jobs_dfs:
        # Step 1: Filter out all-NA columns from each DataFrame before concatenation
        filtered_dfs = [df.dropna(axis=1, how="all") for df in jobs_dfs]

        # Step 2: Concatenate the filtered DataFrames
        jobs_df = pd.concat(filtered_dfs, ignore_index=True)

        # Desired column order
        desired_order = [
            "id",
            "site",
            "job_url_hyper" if hyperlinks else "job_url",
            "job_url_direct",
            "title",
            "company",
            "location",
            "job_type",
            "date_posted",
            "interval",
            "min_amount",
            "max_amount",
            "currency",
            "is_remote",
            "emails",
            "description",
            "company_url",
            "company_url_direct",
            "company_addresses",
            "company_industry",
            "company_num_employees",
            "company_revenue",
            "company_description",
            "logo_photo_url",
            "banner_photo_url",
            "ceo_name",
            "ceo_photo_url",
            "exp_count",
            "exp_type",
            "education_level",
            "remote_details",
            "company_id",
            "minDuration",
            "maxDuration",
            "benefits",
            "version_scraper"
        ]

        # Step 3: Ensure all desired columns are present, adding missing ones as empty
        for column in desired_order:
            if column not in jobs_df.columns:
                jobs_df[column] = None  # Add missing columns as empty

        # Reorder the DataFrame according to the desired order
        jobs_df = jobs_df[desired_order]

        # Step 4: Sort the DataFrame as required
        return jobs_df.sort_values(by=["site", "date_posted"], ascending=[True, False])
    else:
        return pd.DataFrame()


def scrape_company(
    companyList:  list[CompanyInput]
)-> pd.DataFrame:
    SCRAPER_CPY_MAPPING = {
        CompanySite.INDEED: IndeedCpyScraper,
        CompanySite.GLASSDOOR: GlassdoorCpyScraperWithName,
        CompanySite.WELCOMETOJUNGLE: WTJCpyScraper
    }

    idsList= [obj for obj in companyList if obj.id is not None]
    namesList_withoutIds= [obj.name for obj in companyList if obj.id is None]
    namesList = [obj.name for obj in companyList]

    site_to_company_dict = {}
    def scrape_site(site: CompanySite) -> Tuple[str, CompanyResponse]:
        scraper_class = SCRAPER_CPY_MAPPING[site]
        scraper = scraper_class()
        if site == CompanySite.GLASSDOOR:
            scraped_data: CompanyResponse = scraper.scrape(namesList_withoutIds)
        else:
            scraped_data: CompanyResponse = scraper.scrape(namesList)
        cap_name = site.value.capitalize()
        logger.info(f"{cap_name} finished scraping")
        return site.value, scraped_data

    def worker(companySite):
        site_val, scraped_info = scrape_site(companySite)
        return site_val, scraped_info
    
    def worker_id():
        idsList_filtered= [obj.id for obj in idsList if obj.site == CompanySite.GLASSDOOR.value ]
        scraped_data: CompanyResponse = GlassdoorCpyScraper().scrape(companyIdList=idsList_filtered, country=Country.FRANCE)
        cap_name =CompanySite.GLASSDOOR.value.capitalize()
        logger.info(f"{cap_name} with ids finished scraping")
        return CompanySite.GLASSDOOR.value + "_id", scraped_data
    
    with ThreadPoolExecutor() as executor:
        future_to_site = {
            executor.submit(worker, companySite): companySite for companySite in CompanySite
        }
        futureAlone = executor.submit(worker_id)
        site_value, scraped_data = futureAlone.result()
        site_to_company_dict[site_value] = scraped_data

        for future in as_completed(future_to_site):
            site_value, scraped_data = future.result()
            site_to_company_dict[site_value] = scraped_data

    company_dfs: list[pd.DataFrame] = []

    for site, cpy_response in site_to_company_dict.items():
        for company in cpy_response.companyList:
            cpy_data = company.model_dump()
            cpy_data["site"] = site
            cpy_data["socials"] = (
                ", ".join(cpy_data["socials"]) if cpy_data["socials"] else None
            )
            cpy_data["benefits"] = (
                "__==__".join(cpy_data["benefits"]) if cpy_data["benefits"] else None
            )

            cpy_data["bestPlacesToWork"] = (
                ", ".join(cpy_data["bestPlacesToWork"]) if cpy_data["bestPlacesToWork"] else None
            )

            cpy_data['version_scraper'] =__version__
            
            cpy_df = pd.DataFrame([cpy_data])
            company_dfs.append(cpy_df)
    if company_dfs:
        # Step 1: Filter out all-NA columns from each DataFrame before concatenation
        filtered_dfs = [df.dropna(axis=1, how="all") for df in company_dfs]

        # Step 2: Concatenate the filtered DataFrames
        company_df = pd.concat(filtered_dfs, ignore_index=True)

        # Desired column order
        desired_order = [
            "site",
            "name",
            "url",
            "company_url",
            "size",
            "founded",
            "type_of_ownership",
            "sector",
            "revenue",
            "manPercentage",
            "womanPercentage",
            "averageAge",
            "turnover",
            "competitors",
            "socials",
            "description",
            "goodToKnow",
            "lookingFor",
            "benefits",
            "bestPlacesToWork",
            "version_scraper"
        ]
        # Step 3: Ensure all desired columns are present, adding missing ones as empty
        for column in desired_order:
            if column not in company_df.columns:
                company_df[column] = None  # Add missing columns as empty

        # Reorder the DataFrame according to the desired order
        company_df = company_df[desired_order]

        # Step 4: Sort the DataFrame as required
        return company_df.sort_values(by=["site"], ascending=[True])
    else:
     return pd.DataFrame()
    


def scrape_salary(
    jobInputList:  list[JobInput]
)-> pd.DataFrame:
    SCRAPER_SALARY_MAPPING = {
        SalarySite.GLASSDOOR: GlassdoorSalaryScraper
    }
    
    ALLOW_SITE = [SalarySite.GLASSDOOR]

    site_to_salary_dict = {}
    def scrape_site(site: SalarySite) -> Tuple[str, SalaryResponse]:
        scraper_class = SCRAPER_SALARY_MAPPING[site]
        scraper = scraper_class()
        scraped_data: SalaryResponse = scraper.scrapeList(jobInputList)
        cap_name = site.value.capitalize()
        logger.info(f"{cap_name} finished scraping")
        return site.value, scraped_data

    def worker(site):
        site_val, scraped_info = scrape_site(site)
        return site_val, scraped_info
    
    with ThreadPoolExecutor() as executor:
        future_to_site = {
            executor.submit(worker, salarySite): salarySite for salarySite in ALLOW_SITE
        }

        for future in as_completed(future_to_site):
            site_value, scraped_data = future.result()
            site_to_salary_dict[site_value] = scraped_data

    salary_dfs: list[pd.DataFrame] = []

    for site, salary_response in site_to_salary_dict.items():
        for salary in salary_response.salaryList:
            salary_data = salary.model_dump()
            salary_data["site"] = site
            
            salary_data['version_scraper'] =__version__
            
            cpy_df = pd.DataFrame([salary_data])
            salary_dfs.append(cpy_df)
    if salary_dfs:
        # Step 1: Filter out all-NA columns from each DataFrame before concatenation
        filtered_dfs = [df.dropna(axis=1, how="all") for df in salary_dfs]

        # Step 2: Concatenate the filtered DataFrames
        salary_df = pd.concat(filtered_dfs, ignore_index=True)

        # Desired column order
        desired_order = [
            "site",
            "name",
            "fullJobName",
            "jobId",
            "min_val",
            "max_val",
            "payPeriod",
            "currency",
            "location",
            "exp",
            "version_scraper",
        ]

        # Step 3: Ensure all desired columns are present, adding missing ones as empty
        for column in desired_order:
            if column not in salary_df.columns:
                salary_df[column] = None  # Add missing columns as empty

        # Reorder the DataFrame according to the desired order
        salary_df = salary_df[desired_order]

        # Step 4: Sort the DataFrame as required
        return salary_df.sort_values(by=["site"], ascending=[True])
    else:
     return pd.DataFrame()