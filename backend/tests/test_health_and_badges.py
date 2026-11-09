from app.main import health, check_eligibility, EligibilityRequest
from app.eligibility import load_schemes

def test_health_reports_provider_and_scheme_versions_without_credentials():
    payload=health()
    assert payload["status"]=="ok" and payload["version"]
    assert set(payload["schemes"])=={"pm_kisan","pmfby","pm_kusum"}
    assert all(isinstance(value,str) for value in payload["providers"].values())
    assert not any("key" in key.casefold() or "secret" in key.casefold() for key in payload)
    assert set(payload["modes"]) == {"voice_mock", "llm_mock"}
    assert all(isinstance(value, bool) for value in payload["modes"].values())

def test_unverified_schemes_are_badged_in_api_results():
    slots={"owns_land":True,"is_institutional_holder":False,"pays_income_tax":False,
           "state":"Tamil Nadu","district":"Madurai","crop":"rice","season":"kharif",
           "area_notified":True,"component":"B","state_application_open":True,
           "state_requirements_confirmed":True}
    payload=check_eligibility(EligibilityRequest(slots=slots,confirmed=True))
    assert all(row["verified"] is False and row["badge"]=="Unverified draft" for row in payload["results"])
    pmk=next(row for row in payload["results"] if row["scheme_id"]=="pm_kisan")
    assert "PM-KISAN" in pmk["source_basis"]
    assert "checked" in pmk["source_basis"]
    scheme=next(item for item in load_schemes() if item.id=="pm_kisan")
    assert any(rule.source_ref for rule in scheme.rules)
