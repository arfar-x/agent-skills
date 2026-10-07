import requests

from lib.credentials import BearerCredential


def test_bearer_credential_sets_header_and_hides_token():
    session = requests.Session()
    cred = BearerCredential("s3cr3t-value")
    cred.apply(session)
    assert session.headers["Authorization"] == "Bearer s3cr3t-value"
    assert "s3cr3t-value" not in repr(cred)
