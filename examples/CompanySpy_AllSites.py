
import pandas as pd
from ..src.jobspyOtm import scrape_company
from deltalake import DeltaTable

#'FoxIntelligence', 'Skell', 'onboard-workspace',
company: pd.DataFrame = scrape_company(
    companyList=[ 'Saisir', 'Hitec'],
 
)

# 1: output to console
print(company)
company.to_excel("data.xlsx", index=False)
