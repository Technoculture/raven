import frappe
from frappe import _
from frappe.auth import clear_cookies

RAVEN_ROUTE_PREFIXES = ("/raven", "/raven_mobile")
RAVEN_METHOD_PREFIX = "raven."


def validate():
	user = frappe.session.user

	if not user or user == "Guest":
		return

	if not frappe.db.get_value("User", user, "enabled"):
		clear_cookies()
		frappe.throw(
			_("User {0} is disabled. Please contact your System Manager.").format(user),
			frappe.AuthenticationError,
		)

	if is_raven_request() and not frappe.db.exists("Raven User", {"user": user, "enabled": 1}):
		frappe.throw(
			_("Your Raven access is disabled. Please contact your administrator."),
			frappe.PermissionError,
		)


def is_raven_request() -> bool:
	path = frappe.local.request.path if frappe.local.request else ""
	cmd = frappe.local.form_dict.get("cmd") or ""

	return path.startswith(RAVEN_ROUTE_PREFIXES) or cmd.startswith(RAVEN_METHOD_PREFIX)
