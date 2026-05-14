import re
import xml.etree.ElementTree as ET
from typing import Optional

XML_NS = {"ns": "urn:kr:or:kec:standard:Tax:ReusableAggregateBusinessInformationEntitySchemaModule:1:0"}


def _text(elem, path: str) -> Optional[str]:
    if elem is None:
        return None
    node = elem.find(path, XML_NS)
    if node is None or not node.text:
        return None
    return node.text.strip() or None


def _format_biz_no(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    d = re.sub(r"\D", "", raw)
    return f"{d[:3]}-{d[3:5]}-{d[5:]}" if len(d) == 10 else raw


def _format_date(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    d = re.sub(r"\D", "", raw)
    return f"{d[:4]}/{d[4:6]}/{d[6:8]}" if len(d) >= 8 else raw


def parse_tax_invoice_xml(xml_path: str) -> tuple[dict, dict, dict]:
    """
    반환: (supplier_dict, buyer_dict, content_dict)
    content_dict 안에 '항목' 리스트 포함.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    doc        = root.find("ns:TaxInvoiceDocument", XML_NS)
    settlement = root.find("ns:TaxInvoiceTradeSettlement", XML_NS)
    exchanged  = root.find("ns:ExchangedDocument", XML_NS)

    invoicer = settlement.find("ns:InvoicerParty", XML_NS) if settlement is not None else None
    invoicee = settlement.find("ns:InvoiceeParty", XML_NS) if settlement is not None else None
    money    = settlement.find("ns:SpecifiedMonetarySummation", XML_NS) if settlement is not None else None

    def party(node) -> dict:
        return {
            "등록번호": _format_biz_no(_text(node, "ns:ID")),
            "상호":     _text(node, "ns:NameText"),
            "대표자명": _text(node, "ns:SpecifiedPerson/ns:NameText"),
            "사업장주소": _text(node, "ns:SpecifiedAddress/ns:LineOneText"),
            "업태":     _text(node, "ns:TypeCode"),
        }

    items = []
    for item in root.findall("ns:TaxInvoiceTradeLineItem", XML_NS):
        pdate = _text(item, "ns:PurchaseExpiryDateTime")
        items.append({
            "월":     pdate[4:6] if pdate and len(pdate) >= 8 else None,
            "일":     pdate[6:8] if pdate and len(pdate) >= 8 else None,
            "품목":   _text(item, "ns:NameText"),
            "공급가액": _text(item, "ns:InvoiceAmount"),
            "세액":   _text(item, "ns:TotalTax/ns:CalculatedAmount"),
        })

    ref_doc = exchanged.find("ns:ReferencedDocument", XML_NS) if exchanged is not None else None
    content = {
        "작성일자":  _format_date(_text(doc, "ns:IssueDateTime")),
        "공급가액":  _text(money, "ns:ChargeTotalAmount"),
        "세액":      _text(money, "ns:TaxTotalAmount"),
        "합계금액":  _text(money, "ns:GrandTotalAmount"),
        "비고":      _text(doc, "ns:DescriptionText"),
        "승인번호":  _text(doc, "ns:IssueID"),
        "항목":      items,
    }

    return party(invoicer), party(invoicee), content
