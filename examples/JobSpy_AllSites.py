
import pandas as pd
from ..src.jobspyOtm import scrape_jobs
import logging
from IPython.display import display, HTML


#logging.basicConfig()
#logging.getLogger().setLevel(logging.DEBUG)
#requests_log = logging.getLogger("requests.packages.urllib3")
#requests_log.setLevel(logging.DEBUG)
#requests_log.propagate = True


jobs: pd.DataFrame = scrape_jobs(
    site_name=["WelcomeToJungle"],
    search_term="CTO",
    location="Paris",
    results_wanted=5,  # be wary the higher it is, the more likey you'll get blocked (rotating proxy can help tho)
    country_indeed="USA",
    hours_old=168
    # proxy="http://jobspy:5a4vpWtj8EeJ2hoYzk@ca.smartproxy.com:20001",
)

# formatting for pandas
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", 50)  # set to 0 to see full job url / desc

# 1: output to console
print(jobs)

#html = jobs.to_html(escape=False)
# change max-width: 200px to show more or less of the content
#truncate_width = f'<style>.dataframe td {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}</style>{html}'
#display(HTML(truncate_width))
# 2: output to .csv
jobs.to_csv("./jobs.csv", index=False)
#print("outputted to jobs.csv")

# 3: output to .xlsx
#jobs.to_xlsx('jobs.xlsx', index=False)

# 4: display in Jupyter Notebook (1. pip install jupyter 2. jupyter notebook)
# display(jobs)
