"""Regression checks for retryable syncs and non-destructive history recovery.
Run: python3 -m unittest discover -s scripts -p test_plaid_sync.py
"""
import copy
import sys
import types
import unittest
from unittest.mock import patch

from services import plaid_client as client, budget_store as store


def row(tid, day, amount, **extra):
    return dict(id=tid, transaction_id=tid, source="plaid", date=day,
                description="Payroll", account="Ally Bills", amount=amount, **extra)


class SyncRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state = {"items": [{"item_id": "ally", "access_token": "test", "cursor": "old",
                                  "institution_name": "Ally", "accounts": []}]}
        self.txns = [row("existing", "2026-09-17", 2190.73, category_override="My income")]
        self.events = []
        sdk = types.ModuleType("plaid.model.transactions_sync_request")
        sdk.TransactionsSyncRequest = lambda **kwargs: kwargs
        patches = [
            patch.dict(sys.modules, {"plaid.model.transactions_sync_request": sdk}),
            patch.object(client, "is_configured", return_value=True),
            patch.object(client, "_load_items_file", side_effect=lambda: copy.deepcopy(self.state)),
            patch.object(client, "_save_items_file", side_effect=self.save_state),
            patch.object(store, "load_transactions", side_effect=lambda: self.txns),
            patch.object(store, "save_transactions", side_effect=self.save_txns),
            patch.object(store, "_save_json"),
            patch("services.budget_categorizer.recategorize_all"),
            patch.object(client, "_plaid_tx_to_record", side_effect=lambda t, a: dict(t)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.api = self.enterContext(patch.object(client, "_get_client")).return_value

    def save_state(self, state):
        self.events.append("cursor")
        self.state = copy.deepcopy(state)

    def save_txns(self, txns):
        self.events.append("transactions")
        self.txns = txns

    def response(self, added=None, **extra):
        return dict(added=added or [], modified=[], removed=[], has_more=False,
                    next_cursor="new", **extra)

    def test_repair_preserves_history_overrides_and_is_idempotent(self):
        self.api.transactions_sync.return_value = self.response([
            row("existing", "2026-09-17", 2190.73), row("missing", "2026-09-09", 2190.72)])
        result = client.sync_all_items(full_rebuild=True, item_id="ally")
        self.assertTrue(result["ok"])
        self.assertEqual(result["added"], 1)
        self.assertEqual(self.events, ["transactions", "cursor"])
        self.assertEqual(self.txns[0]["category_override"], "My income")
        self.assertNotIn("cursor", self.api.transactions_sync.call_args.args[0])
        client.sync_all_items(full_rebuild=True)
        self.assertEqual(len(self.txns), 2)
        self.assertEqual(self.txns[0]["category_override"], "My income")

    def test_failed_transaction_save_does_not_advance_cursor_or_mutate_cache(self):
        self.api.transactions_sync.return_value = self.response([row("missing", "2026-09-09", 2190.72)])
        before = copy.deepcopy(self.txns)
        with patch.object(store, "save_transactions", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                client.sync_all_items()
        self.assertEqual(self.state["items"][0]["cursor"], "old")
        self.assertEqual(self.txns, before)
        self.assertFalse(client._sync_lock.locked())

    def test_failed_page_preserves_rows_and_cursor(self):
        page = self.response([row("missing", "2026-09-09", 2190.72)])
        page["has_more"] = True
        self.api.transactions_sync.side_effect = [page, RuntimeError("offline")]
        result = client.sync_all_items(full_rebuild=True)
        self.assertFalse(result["ok"])
        self.assertEqual(self.events, [])
        self.assertEqual(len(self.txns), 1)
        self.assertEqual(self.state["items"][0]["cursor"], "old")

    def test_empty_repair_keeps_existing_history(self):
        self.api.transactions_sync.return_value = self.response()
        result = client.sync_all_items(full_rebuild=True)
        self.assertTrue(result["ok"])
        self.assertEqual(len(self.txns), 1)

    def test_incomplete_pagination_does_not_commit(self):
        page = self.response()
        page["has_more"] = True
        self.api.transactions_sync.return_value = page
        result = client.sync_all_items()
        self.assertFalse(result["ok"])
        self.assertEqual(self.events, [])

    def test_other_bank_failure_keeps_its_history_and_cursor(self):
        self.state["items"].append(dict(item_id="other", access_token="other", cursor="other-old"))
        self.txns.append(row("other-row", "2026-09-03", -50))
        self.api.transactions_sync.side_effect = [self.response([row("missing", "2026-09-09", 2190.72)]), RuntimeError("offline")]
        result = client.sync_all_items(full_rebuild=True)
        self.assertFalse(result["ok"])
        self.assertEqual(len(self.txns), 3)
        self.assertEqual(self.state["items"][1]["cursor"], "other-old")

    def test_targeted_repair_does_not_call_other_banks(self):
        self.state["items"].append(dict(item_id="other", access_token="other", cursor="other-old"))
        self.api.transactions_sync.return_value = self.response()
        client.sync_all_items(full_rebuild=True, item_id="ally")
        self.assertEqual(self.api.transactions_sync.call_count, 1)
        self.assertEqual(self.state["items"][1]["cursor"], "other-old")

    def test_overlapping_sync_is_rejected(self):
        with client._sync_lock:
            self.assertFalse(client.sync_all_items()["ok"])
        self.api.transactions_sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
