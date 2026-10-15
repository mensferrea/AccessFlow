import os
import pytest
from app.services.xml_validator import XmlValidatorService

XSD_PATH = os.path.abspath("docs/integration/contracts/legacy_access_message.xsd")
VALID_XML_PATH = os.path.abspath("docs/integration/examples/sample_legacy_request.xml")

def test_xml_validation_success():
    with open(VALID_XML_PATH, "r", encoding="utf-8") as f:
        xml_content = f.read()

    is_valid, errors = XmlValidatorService.validate_xml(xml_content, XSD_PATH)
    assert is_valid is True
    assert len(errors) == 0

def test_xml_validation_failure_missing_element():
    invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <AccessProvisionRequest xmlns="http://bank.corp/accessflow/legacy/v1">
      <MessageId>MSG-INVALID-001</MessageId>
      <Timestamp>2026-10-15T21:00:00Z</Timestamp>
      <Payload>
        <RequestId>1042</RequestId>
        <RequestUUID>e3b0c442-98fc-1c14-9afbf4c8996fb924</RequestUUID>
        <!-- SystemCode missing -->
        <Operation>GRANT</Operation>
      </Payload>
    </AccessProvisionRequest>
    """
    is_valid, errors = XmlValidatorService.validate_xml(invalid_xml, XSD_PATH)
    assert is_valid is False
    assert len(errors) > 0
