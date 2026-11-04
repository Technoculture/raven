from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from raven.api.search import RavenSearch


class TestSearchIndex(TestCase):
	def test_message_identity_survives_explicit_field_projection(self):
		# Frappe 15 returns only the requested fields; it does not add name for us.
		record = {
			"name": "search-index-regression",
			"content": "Search compatibility regression",
			"channel_id": "search-test-channel",
			"owner": "Administrator",
			"message_type": "Text",
		}

		def project_fields(doctype, fields, **kwargs):
			return Mock(
				run=Mock(return_value=[frappe._dict({field: record.get(field) for field in fields})])
			)

		with (
			patch.object(frappe.qb, "get_query", side_effect=project_fields),
			patch.object(frappe.db, "get_value", return_value=(0, "Private", 0)),
			patch.object(frappe.db, "exists", return_value=False),
			patch.object(frappe.db, "get_all", return_value=[]),
		):
			search = RavenSearch()
			documents = search.get_documents()
			self.assertEqual(documents[0].name, record["name"])
			indexed = search.prepare_document(documents[0])
			self.assertIsNotNone(indexed)
			self.assertEqual(indexed["id"], "Raven Message:search-index-regression")
			self.assertEqual(indexed["content"], record["content"])
