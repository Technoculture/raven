import unittest
from unittest.mock import patch

import frappe
from raven import utils


class TestMemberIdentity(unittest.TestCase):
    def test_membership_email_case(self):
        for kind in ("channel", "workspace"):
            getter = getattr(utils, f"get_{kind}_member")
            checker = getattr(utils, f"is_{kind}_member")
            for stored, requested in (
                ("khusboo1@exrna.com", "Khusboo1@exrna.com"),
                ("Khusboo1@exrna.com", "khusboo1@exrna.com"),
                ("khusboo1@exrna.com", "khusboo1@exrna.com"),
            ):
                with self.subTest(kind=kind, stored=stored, requested=requested):
                    member = {"name": "existing-member", "is_admin": 0}
                    members = {stored: member}
                    with patch.object(utils, f"get_{kind}_members", return_value=members):
                        self.assertIs(getter("channel-or-workspace", requested), member)
                        self.assertTrue(checker("channel-or-workspace", requested))
                        self.assertIsNone(getter("channel-or-workspace", "other@exrna.com"))
                        self.assertFalse(checker("channel-or-workspace", "other@exrna.com"))
                    self.assertEqual(list(members), [stored])
                    self.assertEqual(member["is_admin"], 0)

    def test_non_email_ids_remain_exact(self):
        for kind in ("channel", "workspace"):
            with patch.object(utils, f"get_{kind}_members", return_value={"Bot": {"name": "bot"}}):
                self.assertIsNone(getattr(utils, f"get_{kind}_member")("scope", "bot"))
                self.assertFalse(getattr(utils, f"is_{kind}_member")("scope", "bot"))

    def test_empty_membership_does_not_grant_access(self):
        for kind in ("channel", "workspace"):
            with patch.object(utils, f"get_{kind}_members", return_value={}):
                self.assertIsNone(getattr(utils, f"get_{kind}_member")("scope", "Khusboo1@exrna.com"))
                self.assertFalse(getattr(utils, f"is_{kind}_member")("scope", "Khusboo1@exrna.com"))
