import xml.etree.ElementTree as ET
import re

NS = {
    "ns": "urn:kr:or:kec:standard:Tax:ReusableAggregateBusinessInformationEntitySchemaModule:1:0"
}


def text_or_none(elem):
    if elem is None or elem.text is None:
        return None
    value = elem.text.strip()
    return value if value else None


def format_biz_no(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    return raw


def format_date_yyyymmdd(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 8:
        return f"{digits[:4]}/{digits[4:6]}/{digits[6:]}"
    return raw


def split_classification(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [x.strip() for x in value.split(",")]
    return [x for x in parts if x]


def find_text(parent, path: str):
    if parent is None:
        return None
    return text_or_none(parent.find(path, NS))


def clean_amount(val_str: str | None) -> int:
    if not val_str:
        return 0
    cleaned = re.sub(r"[^\d\-]", "", str(val_str))
    return int(cleaned) if cleaned else 0


def parse_tax_invoice_xml(xml_path: str):
    """지정된 경로의 세금계산서 XML을 파싱하여 딕셔너리 3개를 반환합니다."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    doc = root.find("ns:TaxInvoiceDocument", NS)
    settlement = root.find("ns:TaxInvoiceTradeSettlement", NS)

    invoicer = settlement.find("ns:InvoicerParty", NS) if settlement is not None else None
    invoicee = settlement.find("ns:InvoiceeParty", NS) if settlement is not None else None
    money = settlement.find("ns:SpecifiedMonetarySummation", NS) if settlement is not None else None

    supplier_dict = {
        "등록번호": format_biz_no(find_text(invoicer, "ns:ID")),
        "상호": find_text(invoicer, "ns:NameText"),
        "대표자명": find_text(invoicer, "ns:SpecifiedPerson/ns:NameText"),
        "사업장주소": find_text(invoicer, "ns:SpecifiedAddress/ns:LineOneText"),
        "업태": find_text(invoicer, "ns:TypeCode"),
        "종목": split_classification(find_text(invoicer, "ns:ClassificationCode")),
    }

    buyer_dict = {
        "등록번호": format_biz_no(find_text(invoicee, "ns:ID")),
        "상호": find_text(invoicee, "ns:NameText"),
        "대표자명": find_text(invoicee, "ns:SpecifiedPerson/ns:NameText"),
        "사업장주소": find_text(invoicee, "ns:SpecifiedAddress/ns:LineOneText"),
        "업태": find_text(invoicee, "ns:TypeCode"),
        "종목": split_classification(find_text(invoicee, "ns:ClassificationCode")),
    }

    line_items = []
    for item in root.findall("ns:TaxInvoiceTradeLineItem", NS):
        purchase_date = find_text(item, "ns:PurchaseExpiryDateTime")

        qty = find_text(item, "ns:InvoicedQuantity")
        unit_price = find_text(item, "ns:UnitPrice/ns:UnitAmount")
        spec = find_text(item, "ns:InformationText")
        remark = find_text(item, "ns:DescriptionText")

        item_dict = {
            "월": purchase_date[4:6] if purchase_date and len(purchase_date) >= 8 else None,
            "일": purchase_date[6:8] if purchase_date and len(purchase_date) >= 8 else None,
            "적요": find_text(item, "ns:NameText"),
            "규격": spec,
            "수량": float(qty) if qty else None,
            "단가": clean_amount(unit_price) if unit_price else 0,
            "공급가액": clean_amount(find_text(item, "ns:InvoiceAmount")),
            "세액": clean_amount(find_text(item, "ns:TotalTax/ns:CalculatedAmount")),
            "비고": remark,
        }
        line_items.append(item_dict)

    exchanged_doc = root.find("ns:ExchangedDocument", NS)
    referenced_id = find_text(exchanged_doc, "ns:ReferencedDocument/ns:ID") if exchanged_doc is not None else None

    content_dict = {
        "작성일자": format_date_yyyymmdd(find_text(doc, "ns:IssueDateTime")),
        "공급가액": clean_amount(find_text(money, "ns:ChargeTotalAmount")),
        "세액": clean_amount(find_text(money, "ns:TaxTotalAmount")),
        "품목": line_items,
        "합계금액": clean_amount(find_text(money, "ns:GrandTotalAmount")),
        "현금": None,
        "수표": None,
        "어음": None,
        "외상미수금": None,
        "비고": find_text(doc, "ns:DescriptionText"),
        "승인번호": find_text(doc, "ns:IssueID"),
        "일련번호": referenced_id,
    }

    return supplier_dict, buyer_dict, content_dict


def parse_tax_invoice_xml_to_dict(xml_path: str):
    supplier_dict, buyer_dict, content_dict = parse_tax_invoice_xml(xml_path)
    return {
        "공급자": supplier_dict,
        "공급받는자": buyer_dict,
        "내용": content_dict,
        "xml_path": xml_path,
    }
