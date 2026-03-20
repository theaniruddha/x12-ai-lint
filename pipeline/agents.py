from dotenv import load_dotenv
from duckduckgo_search import DDGS
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent

from .models import ClaimVerdict, PipelineState

load_dotenv()


# -- Tool -------------------------------------------------------------------

@tool
def search_medical_code(query: str) -> str:
    """Search for a medical code's official name and clinical description."""
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return f"No results found for: {query}"
        snippets = [r.get("body", "") for r in results if r.get("body")]
        if not snippets:
            return f"No content found for: {query}"
        return "\n\n".join(snippets[:3])
    except Exception as e:
        return f"Search error: {e}"


# -- Node 1: code resolution ReAct agent ------------------------------------

RESOLVER_PROMPT = (
    "You are a medical code resolver. You receive ICD-10 diagnosis codes and CPT procedure codes. "
    "Use the search tool to find the official name and a short clinical description for each code. "
    "Search for each code separately. Return your findings clearly labeled."
)

_llm = ChatGroq(model="llama-3.3-70b-versatile")

resolver_agent = create_react_agent(_llm, tools=[search_medical_code], prompt=RESOLVER_PROMPT)


def resolve_codes(state: PipelineState) -> dict:
    user_msg = (
        f"Resolve these codes:\n"
        f"Diagnosis (ICD-10): {state['dx_code']}\n"
        f"Procedure (CPT): {state['cpt_code']}"
    )
    result = resolver_agent.invoke({"messages": [("user", user_msg)]})
    return {"code_resolution": result["messages"][-1].content}


# -- Node 2: claim validation with structured output ------------------------

AUDITOR_PROMPT = (
    "You are a senior medical claims auditor. You receive a diagnosis code (ICD-10) and a procedure code (CPT) "
    "along with their resolved clinical descriptions. "
    "Your job is to assess whether the procedure is clinically justified by the diagnosis. "
    "Base your decision on standard clinical practice: "
    "APPROVED if there is a clear, direct clinical relationship; "
    "REVIEW if the link is plausible but indirect, unusual, or requires more clinical context; "
    "DENIED if there is no reasonable clinical justification. "
    "Be precise, conservative, and flag any concerns."
)

_auditor = _llm.with_structured_output(ClaimVerdict)


def validate_claim(state: PipelineState) -> dict:
    user_msg = (
        f"Audit this claim:\n"
        f"Diagnosis: {state['dx_code']}\n"
        f"Procedure: {state['cpt_code']}\n\n"
        f"Resolved descriptions:\n{state['code_resolution']}"
    )
    verdict = _auditor.invoke([
        SystemMessage(content=AUDITOR_PROMPT),
        HumanMessage(content=user_msg),
    ])
    return {"verdict": verdict}


# -- Graph ------------------------------------------------------------------

_builder = StateGraph(PipelineState)
_builder.add_node("resolve_codes", resolve_codes)
_builder.add_node("validate_claim", validate_claim)
_builder.set_entry_point("resolve_codes")
_builder.add_edge("resolve_codes", "validate_claim")
_builder.add_edge("validate_claim", END)
pipeline = _builder.compile()


# -- Test -------------------------------------------------------------------

if __name__ == "__main__":
    test_pairs = [
        ("E11.9", "83036", "diabetes + HbA1c test — expect APPROVED"),
        ("M54.5", "71046", "low back pain + chest X-ray — expect REVIEW/DENIED"),
        ("L70.0", "90837", "acne + psychotherapy — expect DENIED"),
    ]

    for dx, cpt, note in test_pairs:
        print()
        print("=" * 64)
        print(f"  {dx} + {cpt}  |  {note}")
        print("=" * 64)
        state = pipeline.invoke({"dx_code": dx, "cpt_code": cpt})
        v = state["verdict"]
        print(f"  dx_code:              {v.dx_code}")
        print(f"  dx_description:       {v.dx_description}")
        print(f"  cpt_code:             {v.cpt_code}")
        print(f"  cpt_description:      {v.cpt_description}")
        print(f"  status:               {v.status}")
        print(f"  confidence:           {v.confidence}")
        print(f"  rationale:            {v.rationale}")
        print(f"  flags:                {v.flags}")
        print(f"  suggested_code:       {v.suggested_code}")
        print(f"  suggested_description:{v.suggested_description}")
