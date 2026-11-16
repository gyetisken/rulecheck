"""The canonical requirements every city is mapped onto.

Five cities describe the same handful of obligations in five vocabularies.
Austin calls it an operator's license, San Diego a short-term residential
occupancy licence, New Orleans a permit. Reading them side by side is only
possible once they point at a shared set of identifiers, so this is that set.

It is deliberately small and deliberately fixed. Growing it per city would
defeat the point: a canonical model that bends to accommodate every source is
just the sources again with extra steps. When a requirement genuinely does not
fit, it stays unmapped and shows up as such, which is information rather than
a gap to paper over.
"""

from typing import Literal

CanonicalId = Literal[
    "LICENSE_REQUIRED",
    "LICENSE_DISPLAYED_IN_ADVERTS",
    "LICENSE_NOT_TRANSFERABLE",
    "LICENSE_RENEWAL",
    "OWNER_MUST_OWN_UNIT",
    "OWNER_MUST_OCCUPY",
    "MAX_UNITS_PER_OPERATOR",
    "MIN_SEPARATION_BETWEEN_RENTALS",
    "LOCAL_CONTACT_REQUIRED",
    "OCCUPANCY_LIMIT",
    "INSURANCE_REQUIRED",
    "SAFETY_EQUIPMENT",
    "LODGING_TAX",
    "NOISE_LIMITS",
    "NO_COMMERCIAL_EVENTS",
    "NO_SIGNAGE",
    "GUEST_RECORDS",
    "UNMAPPED",
]

CANONICAL: dict[str, str] = {
    "LICENSE_REQUIRED": "A licence, permit or registration must be held before renting.",
    "LICENSE_DISPLAYED_IN_ADVERTS": "The licence number must appear in listings or advertising.",
    "LICENSE_NOT_TRANSFERABLE": "The licence cannot be sold, transferred or passed on with the property.",
    "LICENSE_RENEWAL": "The licence expires and must be renewed, on a stated schedule.",
    "OWNER_MUST_OWN_UNIT": "The operator must own the unit, as opposed to renting or managing it.",
    "OWNER_MUST_OCCUPY": "The unit must be the operator's residence, or be occupied by them for part of the year.",
    "MAX_UNITS_PER_OPERATOR": "A limit on how many units one person or entity may operate.",
    "MIN_SEPARATION_BETWEEN_RENTALS": "A required distance or density limit between short-term rentals.",
    "LOCAL_CONTACT_REQUIRED": "A nearby responsible person must be reachable, often within a stated time.",
    "OCCUPANCY_LIMIT": "A cap on how many guests may stay, usually per bedroom or per unit.",
    "INSURANCE_REQUIRED": "Liability or hazard insurance must be carried.",
    "SAFETY_EQUIPMENT": "Smoke alarms, carbon monoxide detectors, extinguishers or similar equipment.",
    "LODGING_TAX": "Hotel, lodging or occupancy tax must be registered for, collected or remitted.",
    "NOISE_LIMITS": "Noise, amplified sound or nuisance limits, often with quiet hours.",
    "NO_COMMERCIAL_EVENTS": "Weddings, parties and commercial events are prohibited at the property.",
    "NO_SIGNAGE": "Signs advertising the rental are restricted or prohibited.",
    "GUEST_RECORDS": "Records of guests or stays must be kept and produced on request.",
    "UNMAPPED": "A real requirement that none of the canonical entries describes.",
}
