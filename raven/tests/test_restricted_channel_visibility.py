from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from raven.api.chat_stream import get_messages
from raven.api.raven_channel import get_channel_list
from raven.notification import send_sender_private_notifications
from raven.permissions import can_view_message


class TestRestrictedChannelVisibility(FrappeTestCase):
	def setUp(self):
		frappe.get_doc("User", "test@example.com").add_roles("Raven Admin")
		for user in ("test@example.com", "test1@example.com", "test3@example.com"):
			frappe.get_doc("User", user).add_roles("Raven User")

		frappe.set_user("test@example.com")
		self.workspace = frappe.get_doc(
			{
				"doctype": "Raven Workspace",
				"workspace_name": "Restricted visibility test " + frappe.generate_hash(length=8),
				"type": "Private",
			}
		).insert()

		for user in ("test1@example.com", "test3@example.com"):
			frappe.get_doc(
				{"doctype": "Raven Workspace Member", "workspace": self.workspace.name, "user": user}
			).insert(ignore_permissions=True)

		self.channel = frappe.get_doc(
			{
				"doctype": "Raven Channel",
				"channel_name": "private-work-updates",
				"type": "Private",
				"workspace": self.workspace.name,
				"members_can_only_view_own_messages": 1,
			}
		).insert()

		for user in ("test1@example.com", "test3@example.com"):
			frappe.get_doc(
				{"doctype": "Raven Channel Member", "channel_id": self.channel.name, "user_id": user}
			).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Raven Channel Member",
				"channel_id": self.channel.name,
				"user_id": "Administrator",
			}
		).insert(ignore_permissions=True)

		self.manager_message = self._insert_message("test@example.com", "Manager update")
		self.employee_message = self._insert_message("test1@example.com", "Employee one update")
		self.other_employee_message = self._insert_message("test3@example.com", "Employee two update")
		self.tagged_message = self._insert_message(
			"test3@example.com",
			'Please review <span data-type="userMention" data-id="test1@example.com">@Test User 1</span>',
		)

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		frappe.clear_cache()

	def _insert_message(self, user, text):
		frappe.set_user(user)
		return frappe.get_doc(
			{
				"doctype": "Raven Message",
				"channel_id": self.channel.name,
				"message_type": "Text",
				"text": f"<p>{text}</p>",
			}
		).insert(ignore_permissions=True)

	def test_member_can_read_only_own_message(self):
		self.assertTrue(can_view_message(self.employee_message, "test1@example.com"))
		self.assertFalse(can_view_message(self.other_employee_message, "test1@example.com"))
		self.assertFalse(can_view_message(self.manager_message, "test1@example.com"))
		self.assertTrue(can_view_message(self.tagged_message, "test1@example.com"))

	def test_channel_admin_can_read_every_message(self):
		for message in (
			self.manager_message,
			self.employee_message,
			self.other_employee_message,
			self.tagged_message,
		):
			self.assertTrue(can_view_message(message, "test@example.com"))

	def test_administrator_without_channel_admin_flag_cannot_read_other_messages(self):
		self.assertFalse(can_view_message(self.employee_message, "Administrator"))

	def test_chat_stream_filters_messages_for_member(self):
		frappe.set_user("test1@example.com")
		response = get_messages(self.channel.name, update_last_visit=False)
		self.assertEqual(
			[message.name for message in response["messages"]],
			[self.tagged_message.name, self.employee_message.name],
		)

	def test_chat_stream_returns_every_message_for_manager(self):
		frappe.set_user("test@example.com")
		response = get_messages(self.channel.name, update_last_visit=False)
		self.assertEqual(
			{message.name for message in response["messages"] if message.message_type != "System"},
			{
				self.manager_message.name,
				self.employee_message.name,
				self.other_employee_message.name,
				self.tagged_message.name,
			},
		)

	def test_normal_private_channel_keeps_shared_visibility(self):
		self.channel.db_set("members_can_only_view_own_messages", 0)
		frappe.clear_cache(doctype="Raven Channel")
		self.assertTrue(can_view_message(self.other_employee_message, "test1@example.com"))

	def test_channel_preview_is_personalized_for_member(self):
		frappe.set_user("test1@example.com")
		channel = next(row for row in get_channel_list() if row.name == self.channel.name)
		self.assertEqual(
			channel.last_message_timestamp, frappe.utils.get_datetime(self.tagged_message.creation)
		)
		self.assertIn("Please review", channel.last_message_details)
		self.assertNotIn("Employee two update", channel.last_message_details)

	def test_realtime_message_event_targets_only_sender_and_managers(self):
		with patch("frappe.publish_realtime") as publish:
			self.other_employee_message.publish_visibility_aware_event("message_created", {"secret": 1})

		recipients = {call.kwargs.get("user") for call in publish.call_args_list}
		self.assertEqual(recipients, {"test@example.com", "test3@example.com"})

	def test_realtime_tagged_message_also_targets_mentioned_member(self):
		with patch("frappe.publish_realtime") as publish:
			self.tagged_message.publish_visibility_aware_event("message_created", {"secret": 1})

		recipients = {call.kwargs.get("user") for call in publish.call_args_list}
		self.assertEqual(
			recipients,
			{"test@example.com", "test1@example.com", "test3@example.com"},
		)

	def test_push_notification_targets_only_opted_in_managers(self):
		manager_member = frappe.db.get_value(
			"Raven Channel Member",
			{"channel_id": self.channel.name, "user_id": "test@example.com"},
			"name",
		)
		frappe.db.set_value("Raven Channel Member", manager_member, "allow_notifications", 1)
		frappe.clear_cache()

		with patch("raven.notification.send_notification_to_user") as send:
			send_sender_private_notifications(self.other_employee_message)

		self.assertEqual(send.call_count, 1)
		self.assertEqual(send.call_args.kwargs["user_id"], "test@example.com")

	def test_v3_batch_endpoint_filters_hidden_messages(self):
		from raven.api.raven_message import get_message_batch

		frappe.set_user("test1@example.com")
		self.assertEqual(get_message_batch(self.other_employee_message.name), [])
		self.assertEqual(
			get_message_batch(self.employee_message.name)[0].name, self.employee_message.name
		)

	def test_v3_files_endpoint_filters_hidden_messages(self):
		from raven.api.search import get_channel_files

		for message in (self.employee_message, self.other_employee_message):
			frappe.db.set_value(
				"Raven Message", message.name, {"message_type": "File", "file": "/private/files/test.pdf"}
			)
		frappe.set_user("test1@example.com")
		files = get_channel_files(self.channel.name)
		self.assertEqual([row.id for row in files], [self.employee_message.name])

	def test_sqlite_results_recheck_current_message_permissions(self):
		from raven.api.search import RavenSearch

		frappe.set_user("test1@example.com")
		results = [
			{"id": f"Raven Message:{m.name}"}
			for m in (self.employee_message, self.other_employee_message, self.tagged_message)
		]
		with patch(
			"frappe.search.sqlite_search.SQLiteSearch._process_search_results", return_value=results
		):
			visible = RavenSearch()._process_search_results([], "update")
		self.assertEqual([row["id"] for row in visible], [results[0]["id"], results[2]["id"]])

	def test_v3_forward_rejects_hidden_message(self):
		from raven.api.raven_message import _forward_payloads

		frappe.set_user("test1@example.com")
		with self.assertRaises(frappe.PermissionError):
			_forward_payloads(self.other_employee_message.name)


test_dependencies = ["User"]
