"""Deterministic synthetic fixture construction. No randomness or seed required."""

LABEL = "SYNTHETIC FIXTURE: invented document metadata, not Henry's real documents."


def fixture_records():
    records = []
    for number in range(1, 201):
        category = ("applications", "finance", "identity", "school")[(number - 1) % 4]
        expiry = "2026-09-29" if number <= 20 else "2026-10-15" if number <= 40 else "2027-01-01" if number <= 80 else None
        records.append({"id": f"DOC-{number:03d}", "title": f"Synthetic {category} document {number:03d}",
                        "category": category, "path": f"C:\\Synthetic Vault\\{category}\\document-{number:03d}.pdf",
                        "issued_on": "2026-01-01", "expires_on": expiry,
                        "tags": ["synthetic", "renewal" if number <= 40 else "archive"], "synthetic": True,
                        "amount_minor": ((number - 1) % 4 + 1) * 100})
    return records


def expectations():
    """Independent hand-counted blocks: 20 + 20 + 40 + 120 = 200; 50 * (100+200+300+400)."""
    return {"_label": LABEL, "synthetic": True, "as_of": "2026-09-30",
            "calculation": "200 records; 50 per category; 20 expired, 20 due, 40 current, 120 undated. Pence: 50 * 1000 = 50000.",
            "figures": {"total_records": 200, "expired_count": 20, "upcoming_count": 20,
                        "current_count": 40, "no_expiry_count": 120, "amount_record_count": 200,
                        "declared_amount_total_gbp_pence": 50000,
                        "category_counts": {"applications": 50, "finance": 50, "identity": 50, "school": 50}},
            "cases": {"expired_ids": [f"DOC-{i:03d}" for i in range(1, 21)],
                      "upcoming_ids": [f"DOC-{i:03d}" for i in range(21, 41)],
                      "current_ids": [f"DOC-{i:03d}" for i in range(41, 81)],
                      "no_expiry_ids": [f"DOC-{i:03d}" for i in range(81, 201)]}}


def tiny_records():
    """Five hand-written synthetic records exercising every expiry status and Unicode."""
    return [
        {"id": "T1", "title": "Synthetic passport", "category": "identity", "path": "C:\\Vault\\passport.pdf", "issued_on": "2020-01-01", "expires_on": "2026-09-29", "tags": ["travel"], "synthetic": True},
        {"id": "T2", "title": "Synthetic application", "category": "applications", "path": "application.pdf", "issued_on": "2026-09-01", "expires_on": "2026-09-30", "tags": ["deadline"], "synthetic": True},
        {"id": "T3", "title": "Synthetic school certificate", "category": "school", "path": "certificate.pdf", "issued_on": "2026-01-01", "expires_on": None, "tags": [], "synthetic": True},
        {"id": "T4", "title": "Synthetic insurance", "category": "finance", "path": "insurance.pdf", "issued_on": "2026-01-01", "expires_on": "2027-01-01", "tags": ["policy"], "synthetic": True},
        {"id": "T5", "title": "Synthetic café 文件", "category": "school", "path": "C:\\Vault\\文件.pdf", "issued_on": "2026-01-01", "expires_on": None, "tags": ["études"], "synthetic": True},
    ]
