import re
import unittest

UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

def resolve_feedback_row(headers, payload, timestamp):
    """
    Simulates Google Apps Script dynamic row mapping based on headers.
    """
    row = []
    for header in headers:
        h = (header or "").strip().lower()
        if "time" in h or "date" in h:
            row.append(timestamp)
        elif "visitor" in h:
            row.append(payload.get("visitorId", ""))
        elif "session" in h:
            row.append(payload.get("sessionId", ""))
        elif "category" in h or "type" in h:
            row.append(payload.get("category", ""))
        elif "message" in h or "feedback" in h or "comment" in h:
            row.append(payload.get("message", ""))
        elif "email" in h:
            row.append(payload.get("email", ""))
        elif "url" in h or "page" in h:
            row.append(payload.get("url", ""))
        else:
            row.append("")
    return row

def auto_migrate_feedback_headers(headers):
    """
    Ensures 'Visitor ID' and 'Session ID' exist in headers.
    """
    new_headers = list(headers)
    norm = [h.strip().lower() for h in new_headers]
    if not any("visitor" in h for h in norm):
        new_headers.append("Visitor ID")
        norm.append("visitor id")
    if not any("session" in h for h in norm):
        new_headers.append("Session ID")
        norm.append("session id")
    return new_headers

def repair_feedback_rows(headers, rows):
    """
    Simulates repairFeedbackSheet logic.
    Detects if category column contains a UUID and unshifts.
    """
    migrated_headers = auto_migrate_feedback_headers(headers)
    
    # Map column indices for migrated headers
    col_map = {}
    for i, h in enumerate(migrated_headers):
        hl = h.strip().lower()
        if "time" in hl or "date" in hl:
            col_map["timestamp"] = i
        elif "visitor" in hl:
            col_map["visitorId"] = i
        elif "session" in hl:
            col_map["sessionId"] = i
        elif "category" in hl or "type" in hl:
            col_map["category"] = i
        elif "message" in hl or "feedback" in hl:
            col_map["message"] = i
        elif "email" in hl:
            col_map["email"] = i
        elif "url" in hl or "page" in hl:
            col_map["url"] = i

    cat_idx = col_map.get("category", 1)
    repaired_rows = []
    repaired_count = 0

    for row in rows:
        row_list = list(row) + [""] * (len(migrated_headers) - len(row))
        val_in_cat = str(row_list[cat_idx] if cat_idx < len(row_list) else "").strip()
        
        # Check if category column has a UUID (corrupted row shifted by visitorId/sessionId)
        if UUID_PATTERN.match(val_in_cat):
            # The row was inserted as: [timestamp, visitorId, sessionId, category, message, email, url]
            # where row_list[0]=timestamp, [1]=visitorId, [2]=sessionId, [3]=category, [4]=message, [5]=email, [6]=url
            orig_ts = row_list[0]
            true_visitor_id = row_list[1] if len(row_list) > 1 else ""
            true_session_id = row_list[2] if len(row_list) > 2 else ""
            true_category = row_list[3] if len(row_list) > 3 else ""
            true_message = row_list[4] if len(row_list) > 4 else ""
            true_email = row_list[5] if len(row_list) > 5 else ""
            true_url = row_list[6] if len(row_list) > 6 else ""

            # Build corrected row matching migrated_headers
            new_row = [""] * len(migrated_headers)
            if "timestamp" in col_map: new_row[col_map["timestamp"]] = orig_ts
            if "visitorId" in col_map: new_row[col_map["visitorId"]] = true_visitor_id
            if "sessionId" in col_map: new_row[col_map["sessionId"]] = true_session_id
            if "category" in col_map: new_row[col_map["category"]] = true_category
            if "message" in col_map: new_row[col_map["message"]] = true_message
            if "email" in col_map: new_row[col_map["email"]] = true_email
            if "url" in col_map: new_row[col_map["url"]] = true_url

            repaired_rows.append(new_row)
            repaired_count += 1
        else:
            repaired_rows.append(row_list)

    return migrated_headers, repaired_rows, repaired_count


class TestGoogleAppsScriptFeedback(unittest.TestCase):
    def test_legacy_5_column_mapping_with_auto_migrate(self):
        legacy_headers = ["Timestamp", "Category", "Message", "Email", "URL"]
        migrated = auto_migrate_feedback_headers(legacy_headers)
        self.assertEqual(migrated, ["Timestamp", "Category", "Message", "Email", "URL", "Visitor ID", "Session ID"])

        payload = {
            "type": "feedback",
            "category": "Suggestion",
            "message": "Add Ligue 1 puzzles!",
            "email": "fan@example.com",
            "visitorId": "e920666d-38ba-4945-83f4-03e3df8e75a7",
            "sessionId": "eff464cc-a172-46e2-a30a-59b10727e297",
            "url": "https://playmaker.best/games/top_scorers.html"
        }
        ts = "2026-09-15T14:00:00.000Z"
        row = resolve_feedback_row(migrated, payload, ts)

        # Col 0: Timestamp
        self.assertEqual(row[0], ts)
        # Col 1: Category MUST be "Suggestion", not visitorId
        self.assertEqual(row[1], "Suggestion")
        # Col 2: Message MUST be "Add Ligue 1 puzzles!", not sessionId
        self.assertEqual(row[2], "Add Ligue 1 puzzles!")
        # Col 3: Email MUST be "fan@example.com"
        self.assertEqual(row[3], "fan@example.com")
        # Col 4: URL
        self.assertEqual(row[4], "https://playmaker.best/games/top_scorers.html")
        # Col 5: Visitor ID
        self.assertEqual(row[5], "e920666d-38ba-4945-83f4-03e3df8e75a7")
        # Col 6: Session ID
        self.assertEqual(row[6], "eff464cc-a172-46e2-a30a-59b10727e297")

    def test_7_column_headers_in_standard_order(self):
        headers = ["Timestamp", "Visitor ID", "Session ID", "Category", "Message", "Email", "URL"]
        payload = {
            "category": "Bug Report",
            "message": "Typo in puzzle #45",
            "email": "",
            "visitorId": "11111111-2222-3333-4444-555555555555",
            "sessionId": "66666666-7777-8888-9999-000000000000",
            "url": "https://playmaker.best"
        }
        ts = "2026-09-15T14:00:00.000Z"
        row = resolve_feedback_row(headers, payload, ts)
        self.assertEqual(row[0], ts)
        self.assertEqual(row[1], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(row[2], "66666666-7777-8888-9999-000000000000")
        self.assertEqual(row[3], "Bug Report")
        self.assertEqual(row[4], "Typo in puzzle #45")
        self.assertEqual(row[5], "")
        self.assertEqual(row[6], "https://playmaker.best")

    def test_repair_corrupted_rows(self):
        headers = ["Timestamp", "Category", "Message", "Email", "URL"]
        # Corrupted row where visitorId went to Category, sessionId to Message, Suggestion to Email, etc.
        corrupted_row = [
            "2026-09-10T12:00:00Z",
            "e920666d-38ba-4945-83f4-03e3df8e75a7",  # in Category col
            "eff464cc-a172-46e2-a30a-59b10727e297",  # in Message col
            "Suggestion",                             # in Email col
            "Love the game! Please add dark mode",    # in URL col
            "user@test.com",                          # overflow col F
            "https://playmaker.best"                  # overflow col G
        ]
        # Already clean row
        clean_row = [
            "2026-09-11T12:00:00Z",
            "Question",
            "How does daily scoring work?",
            "fan@test.com",
            "https://playmaker.best",
            "",
            ""
        ]

        migrated_headers, repaired_rows, count = repair_feedback_rows(headers, [corrupted_row, clean_row])
        self.assertEqual(count, 1)

        rep = repaired_rows[0]
        # headers are ["Timestamp", "Category", "Message", "Email", "URL", "Visitor ID", "Session ID"]
        self.assertEqual(rep[0], "2026-09-10T12:00:00Z")
        self.assertEqual(rep[1], "Suggestion")
        self.assertEqual(rep[2], "Love the game! Please add dark mode")
        self.assertEqual(rep[3], "user@test.com")
        self.assertEqual(rep[4], "https://playmaker.best")
        self.assertEqual(rep[5], "e920666d-38ba-4945-83f4-03e3df8e75a7")
        self.assertEqual(rep[6], "eff464cc-a172-46e2-a30a-59b10727e297")

        # Clean row should have its category and message preserved
        clean = repaired_rows[1]
        self.assertEqual(clean[1], "Question")
        self.assertEqual(clean[2], "How does daily scoring work?")

if __name__ == "__main__":
    unittest.main()
