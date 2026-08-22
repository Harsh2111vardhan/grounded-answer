from src.grounding.gate import GroundingDecision, GroundingGate
from src.grounding.entailment import EntailmentResult
from src.grounding.conflict import ConflictResult
from src.models import Evidence

class E:
    def __init__(self, ok=True): self.ok=ok
    def check_all(self, claims, evidence):
        return [EntailmentResult(c.text,c.citation,self.ok,"test") for c in claims]

class C:
    def __init__(self, results=None): self.results=results or []
    def check_all(self, evidence): return self.results

def ev(i="§1.4.6"):
    return Evidence(i,"Policy text.","Part 1","1.4",1,retrieval_sources=["semantic"])

def test_answer():
    r=GroundingGate(E(True),C()).evaluate("The institution determines full-time status (§1.4.6).",[ev()])
    assert r.decision==GroundingDecision.ANSWER

def test_refuse_without_evidence():
    r=GroundingGate(E(True),C()).evaluate("No evidence.",[])
    assert r.decision==GroundingDecision.REFUSE

def test_conflict_wins():
    conflict=ConflictResult("§4.3.2","§9.1.4",True,"Different deadlines.")
    r=GroundingGate(E(True),C([conflict])).evaluate("The deadline is in §4.3.2.",[ev("§4.3.2"),ev("§9.1.4")])
    assert r.decision==GroundingDecision.CONFLICT
