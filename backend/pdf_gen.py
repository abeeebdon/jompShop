"""ReportLab PDF generators for trade documents."""
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

NAVY = colors.HexColor("#0A1628")
GOLD = colors.HexColor("#C9922A")
TEAL = colors.HexColor("#1A7A6E")
DARK = colors.HexColor("#1A1A2E")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="HelixTitle", fontName="Helvetica-Bold", fontSize=22, textColor=NAVY, spaceAfter=4))
    ss.add(ParagraphStyle(name="HelixSub", fontName="Helvetica", fontSize=9, textColor=TEAL, spaceAfter=18, alignment=TA_LEFT))
    ss.add(ParagraphStyle(name="HelixH2", fontName="Helvetica-Bold", fontSize=11, textColor=NAVY, spaceBefore=12, spaceAfter=6))
    ss.add(ParagraphStyle(name="HelixBody", fontName="Helvetica", fontSize=10, textColor=DARK, leading=14))
    ss.add(ParagraphStyle(name="HelixMono", fontName="Courier", fontSize=9, textColor=DARK))
    return ss


def _header_table(doc_title: str, doc_number: str, issue_date: str) -> Table:
    data = [
        [Paragraph("<b>JOMP SHOP</b>", ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=14, textColor=GOLD)),
         Paragraph(f"<font color='#0A1628'><b>{doc_title.upper()}</b></font>", ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=14, alignment=TA_RIGHT))],
        [Paragraph("Riby Inc · JompStart Digital · Powered by Anchor", ParagraphStyle("s", fontName="Helvetica", fontSize=8, textColor=TEAL)),
         Paragraph(f"<font color='#1A1A2E'>No. <b>{doc_number}</b><br/>Issued: {issue_date}</font>",
                   ParagraphStyle("d", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT))],
    ]
    t = Table(data, colWidths=[95 * mm, 85 * mm])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 1), (-1, 1), 1, GOLD),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _kv_table(rows: list[list[str]], col_widths=None) -> Table:
    t = Table(rows, colWidths=col_widths or [40 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
        ("FONT", (1, 0), (1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _line_items_table(items: list[dict], currency: str = "USD") -> Table:
    header = ["#", "Description", "Qty", "Unit", f"Unit Price ({currency})", f"Line Total ({currency})"]
    rows = [header]
    total = 0.0
    for i, it in enumerate(items, start=1):
        line_total = it["qty"] * it["unit_price"]
        total += line_total
        rows.append([str(i), it["desc"], str(it["qty"]), it.get("unit", "unit"),
                     f"{it['unit_price']:,.2f}", f"{line_total:,.2f}"])
    rows.append(["", "", "", "", "TOTAL", f"{total:,.2f}"])
    t = Table(rows, colWidths=[10 * mm, 70 * mm, 15 * mm, 15 * mm, 30 * mm, 35 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -2), "Helvetica", 9),
        ("TEXTCOLOR", (0, 1), (-1, -2), DARK),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -2), 0.3, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, -1), (-1, -1), GOLD),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 10),
        ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _build_doc(doc_title: str, doc_number: str, seller: dict, buyer: dict,
               items: list[dict], order_meta: dict,
               footer_note: str = "", currency: str = "USD") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = _styles()
    story = []
    story.append(_header_table(doc_title, doc_number, datetime.utcnow().strftime("%Y-%m-%d")))
    story.append(Spacer(1, 8))

    # parties
    party_rows = [
        [Paragraph("<b>Seller / Exporter</b>", styles["HelixH2"]), Paragraph("<b>Buyer / Importer</b>", styles["HelixH2"])],
        [Paragraph(f"{seller.get('name','')}<br/>{seller.get('address','')}<br/>{seller.get('country','')}", styles["HelixBody"]),
         Paragraph(f"{buyer.get('name','')}<br/>{buyer.get('address','')}<br/>{buyer.get('country','')}", styles["HelixBody"])],
    ]
    p_table = Table(party_rows, colWidths=[85 * mm, 85 * mm])
    p_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(p_table)
    story.append(Spacer(1, 12))

    # meta
    meta_rows = []
    for k, v in order_meta.items():
        meta_rows.append([k, Paragraph(str(v), styles["HelixMono"])])
    story.append(_kv_table(meta_rows))
    story.append(Spacer(1, 8))

    # items
    story.append(Paragraph("Line Items", styles["HelixH2"]))
    story.append(_line_items_table(items, currency=currency))

    if footer_note:
        story.append(Spacer(1, 14))
        story.append(Paragraph(footer_note, ParagraphStyle("f", fontName="Helvetica-Oblique", fontSize=8, textColor=TEAL)))

    doc.build(story)
    return buf.getvalue()


def proforma_invoice_pdf(order: dict, seller: dict, buyer: dict) -> bytes:
    items = [{
        "desc": order["product_name"],
        "qty": order["quantity"],
        "unit": order.get("unit", "unit"),
        "unit_price": order["unit_price_usd"],
    }]
    meta = {
        "Order Number": order["order_number"],
        "Order Date": str(order.get("created_at", ""))[:10],
        "Delivery Address": order.get("delivery_address", ""),
        "Expected Delivery": order.get("target_delivery_date", "—"),
        "Payment Status": order.get("payment_status", "pending").upper(),
    }
    if order.get("anchor_reserved_account_number"):
        meta["Virtual Account"] = order["anchor_reserved_account_number"]
    return _build_doc("Proforma Invoice", order["order_number"], seller, buyer, items, meta,
                      footer_note="This proforma invoice is subject to final confirmation. Payment via GetAnchor virtual account. All goods subject to export and import compliance of applicable jurisdictions.")


def commercial_invoice_pdf(order: dict, seller: dict, buyer: dict) -> bytes:
    items = [{"desc": order["product_name"], "qty": order["quantity"], "unit": order.get("unit", "unit"), "unit_price": order["unit_price_usd"]}]
    meta = {
        "Order Number": order["order_number"],
        "Invoice Date": datetime.utcnow().strftime("%Y-%m-%d"),
        "Incoterms": "FOB Apapa Port, Lagos",
        "Country of Origin": seller.get("country", "Nigeria"),
        "Country of Destination": buyer.get("country", "United States"),
        "Currency": "USD",
    }
    return _build_doc("Commercial Invoice", order["order_number"], seller, buyer, items, meta,
                      footer_note="We certify that the information on this invoice is true and correct and that the contents are as stated.")


def packing_list_pdf(order: dict, seller: dict, buyer: dict) -> bytes:
    items = [{
        "desc": f"{order['product_name']} (packaged in {order.get('unit', 'unit')})",
        "qty": order["quantity"],
        "unit": order.get("unit", "unit"),
        "unit_price": 0,  # packing list has no price
    }]
    # override to hide prices
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = _styles()
    story = [_header_table("Packing List", order["order_number"], datetime.utcnow().strftime("%Y-%m-%d")), Spacer(1, 8)]
    party_rows = [
        [Paragraph("<b>Shipper</b>", styles["HelixH2"]), Paragraph("<b>Consignee</b>", styles["HelixH2"])],
        [Paragraph(f"{seller.get('name','')}<br/>{seller.get('address','')}<br/>{seller.get('country','')}", styles["HelixBody"]),
         Paragraph(f"{buyer.get('name','')}<br/>{buyer.get('address','')}<br/>{buyer.get('country','')}", styles["HelixBody"])],
    ]
    t = Table(party_rows, colWidths=[85 * mm, 85 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)
    story.append(Spacer(1, 12))

    header = ["#", "Description", "Qty", "Unit", "Gross Weight", "Net Weight"]
    rows = [header]
    for i, it in enumerate(items, start=1):
        rows.append([str(i), it["desc"], str(it["qty"]), it["unit"], "—", "—"])
    table = Table(rows, colWidths=[10 * mm, 85 * mm, 20 * mm, 20 * mm, 25 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), DARK),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Container sealed and verified at origin. Exporter declares goods described above are as per commercial invoice.",
                           ParagraphStyle("f", fontName="Helvetica-Oblique", fontSize=8, textColor=TEAL)))
    doc.build(story)
    return buf.getvalue()


def certificate_of_origin_pdf(order: dict, seller: dict, buyer: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = _styles()
    story = [_header_table("Certificate of Origin", order["order_number"], datetime.utcnow().strftime("%Y-%m-%d")), Spacer(1, 8)]
    story.append(Paragraph("The undersigned hereby declares that the goods described below originate in the country indicated.", styles["HelixBody"]))
    story.append(Spacer(1, 12))
    kv = [
        ["Exporter", f"{seller.get('name','')}, {seller.get('address','')}"],
        ["Consignee", f"{buyer.get('name','')}, {buyer.get('address','')}"],
        ["Country of Origin", seller.get("country", "Nigeria")],
        ["Country of Destination", buyer.get("country", "United States")],
        ["Goods Description", order["product_name"]],
        ["Quantity", f"{order['quantity']} {order.get('unit','unit')}"],
        ["Order Reference", order["order_number"]],
    ]
    story.append(_kv_table([[k, Paragraph(str(v), styles["HelixBody"])] for k, v in kv], col_widths=[45 * mm, 125 * mm]))
    story.append(Spacer(1, 24))
    story.append(Paragraph("<i>Template — exporter to complete official version with chamber of commerce stamp.</i>",
                           ParagraphStyle("f", fontName="Helvetica-Oblique", fontSize=9, textColor=TEAL)))
    doc.build(story)
    return buf.getvalue()
