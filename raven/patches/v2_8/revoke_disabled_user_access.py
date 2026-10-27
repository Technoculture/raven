import frappe

from raven.raven.doctype.raven_user.raven_user import revoke_disabled_user_access


def execute():
	disabled_users = frappe.get_all("User", filters={"enabled": 0}, pluck="name")

	for user in disabled_users:
		revoke_disabled_user_access(user)
