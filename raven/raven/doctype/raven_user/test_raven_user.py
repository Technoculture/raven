# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest import TestCase as UnitTestCase
from unittest.mock import patch

import frappe
from frappe.core.doctype.user.user import User
from frappe.tests.utils import FrappeTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record depdendencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class TestRavenUser(UnitTestCase):
	"""
	Unit tests for RavenUser.
	Use this class for testing individual functions and methods.
	"""

	pass


class TestRavenUser(FrappeTestCase):
	"""
	Integration tests for RavenUser.
	Use this class for testing interactions between multiple components.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def _user_with_raven(self):
		"""A fresh User with the Raven User role. The hook creates its Raven User."""
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"{frappe.generate_hash('raven', 8)}@example.com",
				"first_name": "Deleted",
				"send_welcome_email": 0,
				"roles": [{"role": "Raven User"}],
			}
		).insert()
		self.assertTrue(frappe.db.exists("Raven User", user.name))
		return user

	def test_deleting_a_user_does_not_save_the_user_again(self):
		# A save mid-delete runs every app's on_update hooks on the dying User,
		# which let other apps recreate their records and fail the deletion.
		user = self._user_with_raven()
		with patch.object(User, "save") as save:
			user.delete()
		save.assert_not_called()
		self.assertFalse(frappe.db.exists("Raven User", user.name))
		self.assertFalse(frappe.db.exists("User", user.name))

	def test_deleting_a_raven_user_removes_the_role_without_a_user_save(self):
		user = self._user_with_raven()
		with patch.object(User, "save") as save:
			frappe.delete_doc("Raven User", user.name)
		save.assert_not_called()
		self.assertNotIn("Raven User", frappe.get_roles(user.name))

	def test_first_name_follows_full_name_change(self):
		"""A profile rename writes only full_name; the derived first_name must
		follow it, or short displays (e.g. the typing indicator) show the old name."""
		user = frappe.get_doc("Raven User", "test@example.com")
		user.full_name = "Renamed Person"
		user.save()
		self.assertEqual(user.first_name, "Renamed")

	def test_explicit_first_name_edit_wins(self):
		user = frappe.get_doc("Raven User", "test@example.com")
		user.full_name = "Renamed Person"
		user.first_name = "Custom"
		user.save()
		self.assertEqual(user.first_name, "Custom")


# Copyright (c) 2024, The Commit Company (Algocode Technologies Pvt. Ltd.) and Contributors
# See license.txt

from unittest import TestCase as UnitTestCase

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now

from raven.raven.doctype.raven_user.raven_user import revoke_disabled_user_access

# On IntegrationTestCase, the doctype test records and all
# link-field test record depdendencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class TestCustomRavenUser(UnitTestCase):
	"""
	Unit tests for RavenUser.
	Use this class for testing individual functions and methods.
	"""

	pass


class TestCustomRavenUser(FrappeTestCase):
	"""
	Integration tests for RavenUser.
	Use this class for testing interactions between multiple components.
	"""

	def test_user_name(self):
		user = frappe.get_doc("Raven User", "test@example.com")
		self.assertEqual(user.name, "test@example.com")
		self.assertEqual(user.full_name, "_Test")

	def test_revoke_disabled_user_access(self):
		user = "test1@example.com"
		session_id = "test-disabled-session-" + frappe.generate_hash(length=8)
		access_token = "test-disabled-token-" + frappe.generate_hash(length=8)
		push_token_name = "test-disabled-push-" + frappe.generate_hash(length=8)

		frappe.db.sql(
			"""
			insert into `tabSessions`
				(`sid`, `user`, `sessiondata`, `status`, `lastupdate`)
			values
				(%s, %s, %s, 'Active', %s)
			""",
			(session_id, user, "{}", now()),
		)
		frappe.db.sql(
			"""
			insert into `tabOAuth Bearer Token`
				(`name`, `creation`, `modified`, `owner`, `modified_by`, `docstatus`, `idx`,
				`client`, `user`, `scopes`, `access_token`, `refresh_token`, `status`)
			values
				(%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
				'test-client', %s, 'all openid', %s, 'test-disabled-user-refresh-token', 'Active')
			""",
			(access_token, now(), now(), user, access_token),
		)
		frappe.db.sql(
			"""
			insert into `tabRaven Push Token`
				(`name`, `creation`, `modified`, `owner`, `modified_by`, `docstatus`, `idx`,
				`user`, `environment`, `fcm_token`)
			values
				(%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
				%s, 'Mobile', 'test-disabled-user-fcm-token')
			""",
			(push_token_name, now(), now(), user),
		)

		try:
			with patch(
				"raven.raven.doctype.raven_push_token.raven_push_token.delete_token_from_raven_cloud"
			):
				revoke_disabled_user_access(user)

			self.assertFalse(frappe.db.exists("Sessions", session_id))
			self.assertEqual(frappe.db.get_value("OAuth Bearer Token", access_token, "status"), "Revoked")
			self.assertFalse(frappe.db.exists("Raven Push Token", push_token_name))
		finally:
			frappe.db.delete("Sessions", {"sid": session_id})
			frappe.db.delete("OAuth Bearer Token", {"name": access_token})
			frappe.db.delete("Raven Push Token", {"name": push_token_name})


test_dependencies = ["User"]
