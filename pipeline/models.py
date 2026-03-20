from typing import NotRequired, Optional, TypedDict

from pydantic import BaseModel, Field


class ClaimVerdict(BaseModel):
    dx_code: str = Field(description="The ICD-10 diagnosis code as provided")
    dx_description: str = Field(description="Official name and brief clinical description of the diagnosis")
    cpt_code: str = Field(description="The CPT procedure code as provided")
    cpt_description: str = Field(description="Official name and brief clinical description of the procedure")
    status: str = Field(
        description=(
            "Claim decision. Use exactly one of: "
            "APPROVED — procedure is clinically justified by the diagnosis; "
            "REVIEW — possible justification but uncertain, indirect link, or missing context — needs human review; "
            "DENIED — no reasonable clinical justification for this procedure given this diagnosis."
        )
    )
    confidence: float = Field(
        description="Confidence in the decision as a float between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
    )
    rationale: str = Field(
        description="Clinical reasoning explaining the decision based on the relationship between the diagnosis and procedure"
    )
    flags: list[str] = Field(
        description=(
            "Machine-readable concern tags. Use from: unrelated_specialty, cosmetic_not_medical, "
            "missing_clinical_indication, experimental_treatment, wrong_setting, "
            "duplicate_billing, upcoding_suspected. Empty list if no concerns."
        )
    )
    suggested_code: Optional[str] = Field(
        default=None,
        description="Alternative CPT code if status is REVIEW or DENIED and a more appropriate code exists. Null otherwise.",
    )
    suggested_description: Optional[str] = Field(
        default=None,
        description="Brief description of the suggested alternative CPT code. Null if no suggestion.",
    )


class PipelineState(TypedDict):
    dx_code: str
    cpt_code: str
    code_resolution: NotRequired[str]
    verdict: NotRequired[Optional[ClaimVerdict]]
