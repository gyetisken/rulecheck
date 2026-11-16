"""Where each city's ordinance comes from.

Kept in code rather than in a note, so `rulecheck fetch` reproduces the corpus
from scratch and nobody has to guess which PDF a text file came from.
"""

from .fetch import Source

SOURCES: dict[str, Source] = {
    "austin": Source(
        city="Austin, Texas",
        url="https://services.austintexas.gov/edims/document.cfm?id=458363",
        description="City Code Chapter 4-23, Short-Term Rentals (repeal and replace, 2025)",
    ),
    "san-diego": Source(
        city="San Diego, California",
        url="https://docs.sandiego.gov/municode/MuniCodeChapter05/Ch05Art10Division01.pdf",
        description="Municipal Code Chapter 5, Article 10, Division 1, Short-Term Residential Occupancy",
    ),
    "nashville": Source(
        city="Nashville, Tennessee",
        url="https://www.nashville.gov/sites/default/files/2022-03/Substitute-BL2020-187.pdf",
        description="Substitute Ordinance BL2020-187, short term rental property",
    ),
    "denver": Source(
        city="Denver, Colorado",
        url="https://www.denvergov.org/content/dam/denvergov/Portals/723/documents/Short_Term_Rental_Signed_Rules_01.25.19.pdf",
        description="Rules Governing Short Term Rental Licenses",
    ),
    "new-orleans": Source(
        city="New Orleans, Louisiana",
        url="https://czo.nola.gov/article-21/",
        description="Comprehensive Zoning Ordinance Article 21, short term rental standards",
        # Article 21 covers every use standard in the city. Only 21.8.C.18 is
        # about short term rentals; the rest is bed and breakfasts, kennels,
        # wind turbines and so on.
        start=r"21\.8\.C\.18\s+Short Term Rental",
        end=r"Adopted by Ordinance No\.|This website uses cookies",
    ),
}

DROP = (
    "COA Law Department",
    "STR Reg (repeal & replace)",
    "Council Meeting Backup",
    "File ID:",
    "City of Austin",
)
