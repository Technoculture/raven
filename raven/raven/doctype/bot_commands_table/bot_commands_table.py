# Copyright (c) 2025, The Commit Company (Algocode Technologies Pvt. Ltd.) and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BotCommandsTable(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		approved: DF.Check
		approved_by: DF.Link | None
		command_description: DF.Data | None
		command_name: DF.Data
		command_script: DF.Code
		disable: DF.Check
		failure_message: DF.Text | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		success_message: DF.Text | None
	# end: auto-generated types

	pass
