# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = ["Raven Workspace"]

EMOJI = '<img data-type="customEmoji" src="/files/x.png" alt=":{0}:" class="emoji">'
MENTION = '<span data-type="userMention" data-id="{0}">@{0}</span>'


def content_of(html):
	message = frappe.get_doc({"doctype": "Raven Message", "message_type": "Text", "text": html})
	message.parse_html_content()
	return message.content


class TestRavenMessage(FrappeTestCase):
	def setUp(self):
		super().setUp()
		if not frappe.db.exists("Raven Workspace", "Public Workspace"):
			frappe.get_doc(
				{"doctype": "Raven Workspace", "workspace_name": "Public Workspace", "type": "Public"}
			).insert()

	def test_custom_emoji_shortcode_in_text(self):
		self.assertEqual(content_of(f"<p>hi {EMOJI.format('party')} there</p>"), "hi :party: there")
		self.assertEqual(content_of(f"<p>{EMOJI.format('what?')}</p>"), ":what?:")

	def test_code_keeps_its_backticks(self):
		self.assertEqual(content_of("<p>run <code>:party:</code> now</p>"), "run `:party:` now")
		self.assertEqual(content_of("<pre><code>x = 1</code></pre>"), "`x = 1`")

	def test_literal_backticks_never_read_as_code_markers(self):
		# A backtick in the message (inside code or out) becomes the lookalike
		# modifier grave, so the preview's marker pairing stays exact.
		self.assertEqual(content_of("<p>press ` now</p>"), "press ˋ now")
		self.assertEqual(content_of("<p>run <code>x ` :party:</code></p>"), "run `x ˋ :party:`")

	def test_custom_emoji_in_spoiler_is_hidden(self):
		html = f'<p><span data-spoiler="true">{EMOJI.format("party")}</span></p>'
		self.assertEqual(content_of(html), "▒▒▒▒▒▒")

	def test_gif_only_message(self):
		self.assertEqual(content_of('<p><img src="https://media.tenor.com/a.gif"></p>'), "Sent a GIF")

	def test_editing_keeps_read_state_of_unchanged_mentions(self):
		channel = frappe.get_doc(
			{
				"doctype": "Raven Channel",
				"channel_name": "mention-edit-test",
				"type": "Public",
				"workspace": "Public Workspace",
			}
		).insert()
		self.addCleanup(frappe.delete_doc, "Raven Channel", channel.name, force=True)

		message = frappe.get_doc(
			{
				"doctype": "Raven Message",
				"channel_id": channel.name,
				"message_type": "Text",
				"text": f"<p>hi {MENTION.format('test@example.com')}</p>",
			}
		).insert()

		# The user viewed the mention, then the message gets edited.
		frappe.db.set_value("Raven Mention", message.mentions[0].name, "is_read", 1)
		message.reload()
		message.text = (
			f"<p>hello {MENTION.format('test@example.com')} {MENTION.format('test1@example.com')}</p>"
		)
		message.save()

		read_by_user = {mention.user: mention.is_read for mention in message.mentions}
		self.assertEqual(read_by_user["test@example.com"], 1)
		self.assertEqual(read_by_user["test1@example.com"], 0)


# Copyright (c) 2023, The Commit Company and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from raven.api.threads import create_thread

EXTRA_TEST_RECORD_DEPENDENCIES = ["User", "Raven User"]


class TestCustomRavenMessage(FrappeTestCase):
	def setUp(self):
		user = frappe.get_doc("User", "test@example.com")
		user.add_roles("Raven Admin")
		user.add_roles("Raven User")

		user1 = frappe.get_doc("User", "test1@example.com")
		user1.add_roles("Raven User")
		user1.remove_roles("Raven Admin")

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		frappe.clear_cache()

	def create_private_channel(self):
		frappe.set_user("test@example.com")
		workspace = frappe.get_doc(
			{
				"doctype": "Raven Workspace",
				"workspace_name": "Message Test Workspace",
				"type": "Public",
			}
		).insert()

		frappe.get_doc(
			{
				"doctype": "Raven Workspace Member",
				"workspace": workspace.name,
				"user": "test1@example.com",
			}
		).insert(ignore_permissions=True)

		return frappe.get_doc(
			{
				"doctype": "Raven Channel",
				"channel_name": "private-message-test",
				"type": "Private",
				"workspace": workspace.name,
			}
		).insert()

	def make_mention_message(self, channel_id):
		return frappe.get_doc(
			{
				"doctype": "Raven Message",
				"channel_id": channel_id,
				"message_type": "Text",
				"text": (
					'<p>Hello <span data-type="userMention" class="mention" '
					'data-id="test1@example.com" data-label="Test User 1">'
					"@Test User 1</span></p>"
				),
			}
		)

	def add_test1_to_channel(self, channel_id):
		return frappe.get_doc(
			{
				"doctype": "Raven Channel Member",
				"channel_id": channel_id,
				"user_id": "test1@example.com",
			}
		).insert()

	def create_thread_channel(self):
		channel = self.create_private_channel()
		self.add_test1_to_channel(channel.name)

		parent_message = frappe.get_doc(
			{
				"doctype": "Raven Message",
				"channel_id": channel.name,
				"message_type": "Text",
				"text": "<p>Parent message</p>",
			}
		).insert()

		return create_thread(parent_message.name)["thread_id"]

	def test_private_channel_mentions_require_channel_membership(self):
		channel = self.create_private_channel()

		message = self.make_mention_message(channel.name)

		with self.assertRaisesRegex(frappe.ValidationError, "Invite"):
			message.insert()

		self.assertFalse(
			frappe.db.exists(
				"Raven Message",
				{
					"channel_id": channel.name,
					"text": message.text,
				},
			)
		)

	def test_private_channel_mentions_allow_channel_members(self):
		channel = self.create_private_channel()

		self.add_test1_to_channel(channel.name)

		message = self.make_mention_message(channel.name).insert()

		self.assertTrue(message.name)
		self.assertEqual(message.mentions[0].user, "test1@example.com")

	def test_thread_mentions_require_thread_membership(self):
		thread_id = self.create_thread_channel()

		message = self.make_mention_message(thread_id)

		with self.assertRaisesRegex(frappe.ValidationError, "thread"):
			message.insert()

		self.assertFalse(
			frappe.db.exists(
				"Raven Message",
				{
					"channel_id": thread_id,
					"text": message.text,
				},
			)
		)

	def test_thread_mentions_allow_thread_members(self):
		thread_id = self.create_thread_channel()
		self.add_test1_to_channel(thread_id)

		message = self.make_mention_message(thread_id).insert()

		self.assertTrue(message.name)
		self.assertEqual(message.mentions[0].user, "test1@example.com")


test_dependencies = ["User"]
