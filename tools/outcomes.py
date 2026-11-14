"""Single source of truth for outcome keys, labels and display order.

The CSS tokens (--oc-<key>) and site.js (OC.OUTCOMES) mirror this table;
tests in build.py check that every key here has a matching CSS class.
"""

# key, verdict label in the campaign CSV, short label, one-line definition
OUTCOMES = [
    ("supported", "Supported", "Supported",
     "The pre-registered decision rule was met."),
    ("partial", "Partially supported", "Partial",
     "Some parts of the decision rule were met, but not all."),
    ("not_supported", "Not supported", "Not supported",
     "The test ran and the decision rule was not met."),
    ("inconclusive", "Inconclusive", "Inconclusive",
     "The test ran but was underpowered, ambiguous or confounded, so the data cannot settle it."),
    ("not_testable", "Not testable (data)", "Not testable",
     "Not tested, or tested only through a proxy, because suitable data were unavailable or unsuitable."),
    ("not_run", "Not tested (run did not execute)", "Not run",
     "Never tested: the run halted, failed technically or ran out of time or compute, or the hypothesis was proposed but never run."),
]

OUTCOME_KEYS = [o[0] for o in OUTCOMES]
EVALUATED_KEYS = OUTCOME_KEYS[:5]          # the 136 "evaluated" hypotheses
VERDICT_TO_KEY = {o[1]: o[0] for o in OUTCOMES}
LABEL = {o[0]: o[1] for o in OUTCOMES}
SHORT = {o[0]: o[2] for o in OUTCOMES}
DEFINITION = {o[0]: o[3] for o in OUTCOMES}

# runs.csv count columns -> outcome keys
RUN_COUNT_COLUMNS = {
    "supported": "supported",
    "partially_supported": "partial",
    "not_supported": "not_supported",
    "inconclusive": "inconclusive",
    "not_tested_data": "not_testable",
    "not_tested_other": "not_run",
}

DISEASE_LABEL = {"PD": "Parkinson's disease", "AD": "Alzheimer's disease", "CROSS": "Cross-disease"}
ORIGIN_LABEL = {"plan": "Pre-registered", "on_the_fly": "Proposed on the fly"}
STOP_REASON_LABEL = {
    "INFRASTRUCTURE": "Stopped before planning (dry-run test, superseded launch, usage limit or process failure)",
    "IDEATE_ONLY": "Ideation-only run (ended after proposing research directions, by design)",
}
CENSUS_LABEL = {
    "SUCCESS": "Success",
    "PARTIAL": "Partial",
    "EARLY": "Early stop",
}
STATUS_LABEL = {"done": "Done", "halted": "Halted", "in_progress": "Stopped without a final status"}
