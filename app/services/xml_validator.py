import os
from typing import Tuple, List
from lxml import etree

class XmlValidatorService:
    @staticmethod
    def validate_xml(xml_content: str, xsd_path: str) -> Tuple[bool, List[str]]:
        if not os.path.exists(xsd_path):
            raise FileNotFoundError(f"XSD schema file not found at: {xsd_path}")

        try:
            with open(xsd_path, "rb") as xsd_file:
                schema_root = etree.XML(xsd_file.read())
                schema = etree.XMLSchema(schema_root)

            xml_doc = etree.fromstring(xml_content.encode("utf-8"))
            is_valid = schema.validate(xml_doc)
            errors = [str(err) for err in schema.error_log]
            return is_valid, errors
        except etree.XMLSyntaxError as e:
            return False, [f"XML Syntax Error: {str(e)}"]
        except Exception as e:
            return False, [f"Validation Exception: {str(e)}"]
