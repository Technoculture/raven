import frappe

from raven.utils import (
	get_channel_member,
	get_channel_members,
	get_workspace_member,
	is_channel_member,
	is_workspace_member,
)


def check_app_permission():
	"""Check if user has permission to access the app (for showing the app on app screen)"""
	if frappe.session.user == "Administrator":
		return True

	if frappe.db.exists("Raven User", {"user": frappe.session.user}):
		return True

	return False


def raven_user_has_permission(doc, user=None, ptype=None):

	if doc.type == "Bot":
		# Anyone with Raven User role can view the bot details
		if ptype == "read":
			return True

		# Raven Admins can change the bot details
		roles = frappe.get_roles(user)
		if "Raven Admin" in roles:
			return True
	else:
		# Only the user can change their own details
		if doc.user == user:
			return True
		if ptype == "read":
			return True

	return False


def workspace_has_permission(doc, user=None, ptype=None):
	"""
	1. Only Raven Admins can create a workspace
	2. Only Workspace admins can update/delete a workspace
	3. If the workspace is public, anyone can read
	4. If the workspace is private, only member can read
	"""
	if ptype == "create":
		# Return True since this is checked via the Role in the doctype - only Raven Admins can create a workspace
		return True

	if ptype == "write" or ptype == "delete":
		# Only Workspace admins can update/delete a workspace
		workspace_member = get_workspace_member(doc.name, user)
		if workspace_member and workspace_member.get("is_admin"):
			return True
		else:
			return False

	if ptype == "read":
		if doc.type == "Public":
			return True

		if doc.type == "Private":
			# Check if the user is a member of the workspace
			if is_workspace_member(doc.name, user):
				return True

	return False


def workspace_member_has_permission(doc, user=None, ptype=None):

	# If the workspace is a public workspace, anyone can join
	if ptype == "create":
		workspace_type = frappe.get_cached_value("Raven Workspace", doc.workspace, "type")
		if workspace_type == "Public":
			# Anyone can join a public workspace, but not as an admin
			if user == doc.user and not doc.is_admin:
				return True
			else:
				workspace_member = get_workspace_member(doc.workspace, user)
				if workspace_member and workspace_member.get("is_admin"):
					return True

		if workspace_type == "Private":
			workspace_member = get_workspace_member(doc.workspace, user)
			if workspace_member and workspace_member.get("is_admin"):
				return True

	if ptype == "write":
		workspace_member = get_workspace_member(doc.workspace, user)
		if workspace_member and workspace_member.get("is_admin"):
			return True

	if ptype == "delete":
		if doc.user == user:
			return True
		else:
			workspace_member = get_workspace_member(doc.workspace, user)
			if workspace_member and workspace_member.get("is_admin"):
				return True

	if ptype == "read":
		if doc.user == user:
			return True

		if is_workspace_member(doc.workspace, user):
			return True

	return False


def channel_has_permission(doc, user=None, ptype=None):
	if doc.is_direct_message:
		# Users can create direct message channels
		if ptype == "create":
			return True

		if ptype == "read":
			return is_channel_member(doc.name, user)

	elif doc.is_thread:

		if ptype == "create":
			# Users can create threads in channels they are a member of the main channel in which the thread is created
			main_channel = frappe.get_cached_value("Raven Message", doc.channel_name, "channel_id")

			if is_channel_member(main_channel, user):
				return True

		if ptype == "read":
			main_channel = frappe.get_cached_value("Raven Message", doc.channel_name, "channel_id")
			# Check if the user has read permission to the main channel
			channel_doc = frappe.get_cached_doc("Raven Channel", main_channel)
			return channel_doc.has_permission("read", user=user)

		if ptype == "delete":
			# Only the creator of the thread can delete the thread
			return doc.owner == user

	else:
		# For regular channels
		if ptype == "create":
			# Channels can only be created by members of the workspace
			workspace_member = get_workspace_member(doc.workspace, user)
			if not workspace_member:
				return False
			# Workspace admins can always create a channel
			if workspace_member.get("is_admin"):
				return True
			# If the workspace allows any member to create a channel, then the user can create a channel
			if not frappe.db.get_value("Raven Workspace", doc.workspace, "only_admins_can_create_channels"):
				return True

		if ptype == "delete" or ptype == "write":
			# Only channel admins can update or delete a channel
			channel_member = get_channel_member(doc.name, user)
			if channel_member:
				if channel_member.get("is_admin"):
					return True
				# If the user is a Raven Admin, they can update or delete the channel
				roles = frappe.get_roles(user)
				if "Raven Admin" in roles:
					return True

		if ptype == "read":
			# Check if the channel type is public or open
			if doc.type == "Public" or doc.type == "Open":
				return is_workspace_member(doc.workspace, user)
			else:
				return is_channel_member(doc.name, user)

	return False

	# if doc.type == "Open" or doc.type == "Public":
	# 	# If the channel is public/open, check if the user is a member of the workspace
	# 	if doc.workspace:
	# 		return frappe.db.exists("Raven Workspace Member", {"workspace": doc.workspace, "user": user})
	# 	return True
	# elif doc.type == "Private":
	# 	if doc.is_thread:
	# 		if ptype == "read" or ptype == "create":
	# 			# Only users who are part of the original channel can read the thread
	# 			return frappe.has_permission(doctype="Raven Message", doc=doc.name, ptype="read")

	# 	if frappe.db.exists("Raven Channel Member", {"channel_id": doc.name, "user_id": user}):
	# 		return True
	# 	elif (
	# 		doc.owner == user and frappe.db.count("Raven Channel Member", {"channel_id": doc.name}) <= 0
	# 	):
	# 		return True
	# 	else:
	# 		return False


def can_assign_channel_admins(channel_id: str, user: str) -> bool:
	"""True if the user is in the channel and is its admin or a Raven Admin."""
	channel_member = get_channel_member(channel_id, user)
	if not channel_member:
		return False
	return bool(channel_member.get("is_admin")) or "Raven Admin" in frappe.get_roles(user)


def channel_member_has_permission(doc, user=None, ptype=None):

	# Allow reads and writes on your own membership.
	# Changing is_admin on an existing membership is checked in the controller.
	if doc.user_id == user:
		if ptype == "read" or ptype == "write":
			return True

	if ptype == "read":
		# Other channel members can read the channel member document
		return frappe.db.exists("Raven Channel Member", {"channel_id": doc.channel_id, "user_id": user})

	channel_doc = frappe.get_cached_doc("Raven Channel", doc.channel_id)

	channel_type = channel_doc.type
	is_direct_message = channel_doc.is_direct_message
	workspace = channel_doc.workspace

	if ptype == "create":
		if is_direct_message:
			# This is handled in the creation of a direct message channel so we can safely return False
			return False

		# Only channel admins and Raven Admins can add someone as an admin.
		# The server's own admin inserts (like the channel creator) skip this with ignore_permissions.
		if doc.is_admin and not can_assign_channel_admins(doc.channel_id, user):
			return False

		if doc.user_id == user:
			# Check if the channel is open or public. If yes, then the user needs to be a member of the workspace
			# if the channel is private, the user cannot add themselves to the channel
			if channel_type == "Open" or channel_type == "Public":
				return is_workspace_member(workspace, user)

			if channel_doc.is_thread:
				# Check if the user is a member of the main channel
				main_channel = frappe.db.get_value("Raven Message", doc.channel_id, "channel_id")
				return is_channel_member(main_channel, user)

		else:
			# Someone else is adding a new member to the channel
			# Only existing channel members can add a new channel member
			# If the member to be added is a member of the workspace, they can be added to the channel
			if is_workspace_member(workspace, doc.user_id):
				return frappe.db.exists(
					"Raven Channel Member", {"channel_id": doc.channel_id, "user_id": user}
				)

	if ptype == "delete":
		if is_direct_message:
			# Users cannot delete their members in a direct message channel
			return False

		elif doc.user_id == user:
			# Users can delete their own channel member document
			return True

		else:
			# Only channel admins can delete a channel member
			channel_member = get_channel_member(doc.channel_id, user)
			if channel_member and channel_member.get("is_admin"):
				return True

	if ptype == "write":
		# Only channel admins can update a channel member
		channel_member = get_channel_member(doc.channel_id, user)
		if channel_member:
			if channel_member.get("is_admin"):
				return True
			# If the user is a Raven Admin, they can update the channel member
			roles = frappe.get_roles(user)
			if "Raven Admin" in roles:
				return True

	# Allow self to modify their own channel member document
	# if doc.user_id == user:
	# 	if ptype == "create":
	# 		return True
	# 	# Check if the user is a member of the worksp
	# 	if ptype in ["delete", "write"]:
	# 		return True

	# if channel_type == "Open" or channel_type == "Public":
	# 	return True

	# if channel_type == "Private":
	# 	# If it's a private channel, only the members can modify the channel member
	# 	if frappe.db.exists("Raven Channel Member", {"channel_id": doc.channel_id, "user_id": user}):
	# 		return True

	return False


def message_has_permission(doc, user=None, ptype=None):

	# To send any message, the user needs to be a member of the channel

	if ptype == "read":
		return can_view_message(doc, user)

	# To create, update, or delete a message, the user needs to own this message
	if ptype in ["create", "write", "delete"]:
		channel_member = get_channel_member(doc.channel_id, user)
		if not channel_member:
			return False

		return doc.owner == user

	return False


def get_message_visibility_channel(channel_id: str) -> str:
	channel_doc = frappe.get_cached_doc("Raven Channel", channel_id)
	if channel_doc.is_thread:
		return frappe.get_cached_value("Raven Message", channel_id, "channel_id") or channel_id
	return channel_id


def can_view_all_channel_messages(channel_id: str, user: str | None = None) -> bool:
	"""Return whether the user is a manager for a sender-private channel."""
	user = user or frappe.session.user
	member = get_channel_member(get_message_visibility_channel(channel_id), user)
	return bool(member and member.get("is_admin"))


def channel_has_sender_private_messages(channel_id: str) -> bool:
	channel_id = get_message_visibility_channel(channel_id)
	return bool(
		frappe.get_cached_value("Raven Channel", channel_id, "members_can_only_view_own_messages")
	)


def can_view_message(doc, user: str | None = None) -> bool:
	user = user or frappe.session.user
	channel_doc = frappe.get_cached_doc("Raven Channel", doc.channel_id)
	if not channel_has_permission(channel_doc, user, "read"):
		return False

	if not channel_has_sender_private_messages(doc.channel_id):
		return True

	return (
		doc.owner == user
		or can_view_all_channel_messages(doc.channel_id, user)
		or frappe.db.exists("Raven Mention", {"parent": doc.name, "user": user})
	)


def get_sender_private_message_recipients(
	channel_id: str, owner: str, mentioned_users: list[str] | None = None
) -> list[str]:
	visibility_channel = get_message_visibility_channel(channel_id)
	mentioned_users = set(mentioned_users or [])
	return [
		user_id
		for user_id, member in get_channel_members(visibility_channel).items()
		if user_id == owner or member.get("is_admin") or user_id in mentioned_users
	]


def apply_message_visibility(query, message, channel_id: str, user: str | None = None):
	"""Apply the sender-private visibility rule to a Query Builder query."""
	user = user or frappe.session.user
	if channel_has_sender_private_messages(channel_id) and not can_view_all_channel_messages(
		channel_id, user
	):
		mention = frappe.qb.DocType("Raven Mention")
		mentioned_messages = frappe.qb.from_(mention).select(mention.parent).where(mention.user == user)
		return query.where((message.owner == user) | message.name.isin(mentioned_messages))
	return query


def get_message_visibility_criterion(message, channel, channel_member, user: str | None = None):
	"""Visibility rule for queries which span multiple channels."""
	user = user or frappe.session.user
	mention = frappe.qb.DocType("Raven Mention")
	mentioned_messages = frappe.qb.from_(mention).select(mention.parent).where(mention.user == user)
	return (
		(channel.members_can_only_view_own_messages == 0)
		| (message.owner == user)
		| (channel_member.is_admin == 1)
		| message.name.isin(mentioned_messages)
	)


def raven_poll_vote_has_permission(doc, user=None, ptype=None):
	"""
	Allowed users can add a vote to a poll and read votes (if the poll is not anonymous)
	"""
	# Check if the user has permission to the poll itself
	if not frappe.has_permission("Raven Poll", doc=doc.poll_id, ptype="read", user=user):
		return False

	if ptype == "create":
		# User can only vote if they are a member of the channel
		channel_id = frappe.get_cached_value("Raven Message", {"poll_id": doc.poll_id}, "channel_id")
		if is_channel_member(channel_id):
			if doc.owner == user:
				return True
			else:
				return False

	if ptype in ["read", "delete"]:
		if doc.owner == user:
			return True
		else:
			is_anonymous = frappe.get_cached_value("Raven Poll", doc.poll_id, "is_anonymous")
			if not is_anonymous:
				if ptype == "read":
					return True

	return False


def raven_poll_has_permission(doc, user=None, ptype=None):
	"""
	Allowed users can create a poll and read polls.
	Only the poll creator can delete the poll
	"""
	if ptype == "read" or ptype == "delete" or ptype == "write":
		# Permissions to read the poll are delegated to the message associated with the poll
		message = frappe.get_doc("Raven Message", {"poll_id": doc.name})

		return message.has_permission(ptype, user=user)

	if ptype == "create":
		if doc.owner == user:
			return True

	return False


def raven_workspace_query(user):
	if not user:
		user = frappe.session.user

	# Get all workspaces that the user is a member of
	workspace_members = frappe.get_all(
		"Raven Workspace Member", filters={"user": user}, fields=["workspace"]
	)

	workspace_names = [frappe.db.escape(member.workspace) for member in workspace_members]

	if workspace_names:
		return f"`tabRaven Workspace`.name in ({', '.join(workspace_names)}) OR `tabRaven Workspace`.type = 'Public'"
	else:
		return "`tabRaven Workspace`.type = 'Public'"


def raven_workspace_member_query(user):
	if not user:
		user = frappe.session.user

	# Get all workspaces that the user is a member of
	workspace_members = frappe.get_all(
		"Raven Workspace Member", filters={"user": user}, fields=["workspace"]
	)

	workspace_names = [frappe.db.escape(member.workspace) for member in workspace_members]

	if workspace_names:
		return f"`tabRaven Workspace Member`.workspace in ({', '.join(workspace_names)})"
	else:
		return f"`tabRaven Workspace Member`.owner = {frappe.db.escape(user)}"


def raven_channel_member_query(user):
	if not user:
		user = frappe.session.user

	return f"`tabRaven Channel Member`.user_id = {frappe.db.escape(user)}"


def raven_channel_query(user):
	if not user:
		user = frappe.session.user

	"""
      Only show channels that the user is a owner of

      We could also remove "Raven User" from the Raven Channel doctype role, but then permission checks for joining socket rooms for the channel would fail

      Hence, we are adding a WHERE clause to the query - this is inconsequential since we will never use the standard get_list query for Raven Channel,
      but needed for security since we do not want users to be able to view channels they are not a member of
    """
	return f"`tabRaven Channel`.owner = {frappe.db.escape(user)}"


def raven_message_query(user):
	if not user:
		user = frappe.session.user

	"""
      Only show messages created by the user using a WHERE clause

      We could also remove "Raven User" from the Raven Message doctype role, but then permission checks for attached files would also fail.

      Hence, we are adding a WHERE clause to the query - this is inconsequential since we will never use the standard get_list query for Raven Message,
      but needed for security since we do not want users to be able to view messages from channels they are not a member of
    """
	return f"""(`tabRaven Message`.owner = {frappe.db.escape(user)} OR EXISTS (
		SELECT 1 FROM `tabRaven Mention` mention
		WHERE mention.parent = `tabRaven Message`.name
			AND mention.user = {frappe.db.escape(user)}
	) OR EXISTS (
		SELECT 1 FROM `tabRaven Channel` restricted_channel
		INNER JOIN `tabRaven Channel Member` manager
			ON manager.channel_id = restricted_channel.name
		WHERE restricted_channel.name = `tabRaven Message`.channel_id
			AND restricted_channel.members_can_only_view_own_messages = 1
			AND manager.user_id = {frappe.db.escape(user)}
			AND manager.is_admin = 1
	))"""


def raven_poll_query(user):
	if not user:
		user = frappe.session.user

	return f"`tabRaven Poll`.owner = {frappe.db.escape(user)}"


def raven_poll_vote_query(user):
	if not user:
		user = frappe.session.user

	"""
	  Only show votes created by the user using a WHERE clause

	  Hence, we are adding a WHERE clause to the query - this is inconsequential since we will never use the standard get_list query for Raven Poll Vote,
	  but needed for security since we do not want users to be able to view votes from polls they did not vote for
	"""
	return f"`tabRaven Poll Vote`.owner = {frappe.db.escape(user)}"
