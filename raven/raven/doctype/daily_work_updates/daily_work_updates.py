# Copyright (c) 2025, The Commit Company (Algocode Technologies Pvt. Ltd.) and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DailyWorkUpdates(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from raven.raven.doctype.task_log.task_log import TaskLog

		email: DF.Data
		log_date: DF.Date
		log_table: DF.Table[TaskLog]
		type: DF.Literal["Plan", "Update"]
	# end: auto-generated types

	pass
