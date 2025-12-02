import frappe


def get_raven_room():
	"""
	Room which any user with the role "Raven User" is subscribed to.
	"""
	# When they open the app, the will be subscribed to the users list.
	# We are just using the doctype room to send events to them
	# If we use "all" instead, then the events are only sent to System Users and not users who do not have Desk access.
	return "doctype:Raven User"


def track_channel_visit(channel_id, user=None, commit=False, publish_event_for_user=False):
	"""
	Track the last visit of the user to the channel.
	If the user is not a member of the channel, create a new member record
	"""

	if not user:
		user = frappe.session.user

	# Get the channel member record
	channel_member = get_channel_member(channel_id, user)

	now = frappe.utils.now()

	if channel_member:
		# Update the last visit
		frappe.db.set_value("Raven Channel Member", channel_member["name"], "last_visit", now)

	# Else if the user is not a member of the channel and the channel is open, create a new member record
	elif frappe.get_cached_value("Raven Channel", channel_id, "type") == "Open":
		frappe.get_doc(
			{
				"doctype": "Raven Channel Member",
				"channel_id": channel_id,
				"user_id": frappe.session.user,
				"last_visit": now,
			}
		).insert()

	# Need to commit the changes to the database if the request is a GET request
	if commit:
		frappe.db.commit()  # nosempgrep

	if publish_event_for_user:
		frappe.publish_realtime(
			"raven:unread_channel_count_updated",
			{"channel_id": channel_id, "sent_by": frappe.session.user, "last_message_timestamp": now},
			user=user,
		)


# Workspace Members
def get_workspace_members(workspace_id: str):
	"""
	Gets all members of a workspace from the cache
	"""
	cache_key = f"raven:workspace_members:{workspace_id}"

	data = frappe.cache().get_value(cache_key)
	if data:
		return data

	members = frappe.db.get_all(
		"Raven Workspace Member",
		filters={"workspace": workspace_id},
		fields=["name", "user", "is_admin"],
	)

	data = {member.user: member for member in members}
	frappe.cache().set_value(cache_key, data)
	return data


def delete_workspace_members_cache(workspace_id: str):
	cache_key = f"raven:workspace_members:{workspace_id}"
	frappe.cache().delete_value(cache_key)


def get_workspace_member(workspace_id: str, user: str = None) -> dict:
	"""
	Get the workspace member ID
	"""
	if not user:
		user = frappe.session.user

	return get_workspace_members(workspace_id).get(user, None)


def is_workspace_member(workspace_id: str, user: str = None) -> bool:
	"""
	Check if a user is a member of a workspace
	"""
	if not user:
		user = frappe.session.user

	all_members = get_workspace_members(workspace_id)

	return user in all_members


def get_channel_members(channel_id: str):
	"""
	Gets all members of a channel from the cache as a map - also includes the type of the user
	"""
	cache_key = f"raven:channel_members:{channel_id}"

	data = frappe.cache().get_value(cache_key)
	if data:
		return data

	raven_channel_member = frappe.qb.DocType("Raven Channel Member")
	raven_user = frappe.qb.DocType("Raven User")

	query = (
		frappe.qb.from_(raven_channel_member)
		.join(raven_user)
		.on(raven_channel_member.user_id == raven_user.name)
		.select(
			raven_channel_member.name,
			raven_channel_member.user_id,
			raven_channel_member.is_admin,
			raven_channel_member.allow_notifications,
			raven_user.type,
		)
		.where(raven_channel_member.channel_id == channel_id)
	)

	members = query.run(as_dict=True)

	data = {member.user_id: member for member in members}
	frappe.cache().set_value(cache_key, data)
	return data


def delete_channel_members_cache(channel_id: str):
	"""
	Delete the channel members cache and clear the push tokens for the channel if the flag is set to True

	By default, the push tokens are cleared when the channel members cache is deleted
	"""
	cache_key = f"raven:channel_members:{channel_id}"
	frappe.cache().delete_value(cache_key)

	frappe.publish_realtime(
		"channel_members_updated",
		{"channel_id": channel_id},
		room=get_raven_room(),
		after_commit=True,
	)


def get_channel_member(channel_id: str, user: str = None) -> dict:
	"""
	Get the channel member ID
	"""

	if not user:
		user = frappe.session.user

	all_members = get_channel_members(channel_id)

	return all_members.get(user, None)


def is_channel_member(channel_id: str, user: str = None) -> bool:
	"""
	Check if a user is a member of a channel
	"""
	if not user:
		user = frappe.session.user

	return user in get_channel_members(channel_id)


def get_raven_user(user_id: str) -> str:
	"""
	Get the Raven User ID of a user
	"""
	# TODO: Run this via cache
	return frappe.db.get_value("Raven User", {"user": user_id}, "name")


def get_thread_reply_count(thread_id: str) -> int:
	"""
	Get the number of replies in a thread
	"""
	return frappe.cache().hget(
		"raven:thread_reply_count",
		thread_id,
		lambda: frappe.db.count(
			"Raven Message", {"channel_id": thread_id, "message_type": ["!=", "System"]}
		),
	)


def refresh_thread_reply_count(thread_id: str):
	"""
	Refresh the thread reply count
	"""
	new_count = frappe.db.count(
		"Raven Message", {"channel_id": thread_id, "message_type": ["!=", "System"]}
	)
	frappe.cache().hset("raven:thread_reply_count", thread_id, new_count)

	return new_count


def clear_thread_reply_count_cache(thread_id: str):
	"""
	Clear the thread reply count cache
	"""
	frappe.cache().hdel("raven:thread_reply_count", thread_id)



def push_message_to_channel(channel_id, text, is_bot_message=False, bot_user=None):
    doc = frappe.get_doc({
        "doctype": "Raven Message",
        "channel_id": channel_id,
        "text": text,
        "message_type": "Text",
        "is_bot_message": is_bot_message,
        "bot": bot_user if is_bot_message else None,
    })


    doc.insert(ignore_permissions=True)

from datetime import date
import frappe

def create_doc(data, ignore_permissions=False):
    today = date.today()

    # Check if a Work Updates doc already exists for today
    existing = frappe.get_list(
        "Work Updates",
        filters={"employee": data.get("employee"), "date": today},
        fields=["name"]
    )

    if existing:
        # Fetch the existing doc
        doc = frappe.get_doc("Work Updates", existing[0].name)

        # Option 1: Append new tasks to child table
        for task in data.get("work_update_tasks", []):
            doc.append("work_update_tasks", task)

        # Optionally update any other fields from data
        if "title" in data:
            doc.title = data["title"]

        doc.save(ignore_permissions=ignore_permissions)
        return doc

    # If not existing, create new
    doc = frappe.get_doc({
        "doctype": "Work Updates",
        **data
    })

    doc.insert(ignore_permissions=ignore_permissions)
    return doc

def create_doc(data, ignore_permissions=False):
    today = date.today()

    existing = frappe.get_list(
        "Work Updates",
        filters={"email": data["email"], "log_date": today , "type":data["type"]},
        fields=["name"]
    )

    if existing:
        doc = frappe.get_doc("Work Updates", existing[0].name)

        for task in data.get("c_log_table", []):
            doc.append("c_log_table", task)

        doc.save(ignore_permissions=ignore_permissions)
        return doc

    # If not existing, create new
    doc = frappe.get_doc({
        "doctype": "Work Updates",
        **data
    })

    doc.insert(ignore_permissions=ignore_permissions)
    return doc


def update_doc(data, ignore_permissions=False):
    """
    Upserts a Work Updates document:
    - If it exists, update child table rows based on uid
    - If not, create a new Work Updates document
    - Appends child rows if uid not found
    """

    required_fields = ["uid", "task"]  # Add more required fields if needed
    today = date.today()

    # Validate input structure
    for row in data.get("c_log_table", []):
        for field in required_fields:
            if not row.get(field):
                frappe.throw(f"Missing required field '{field}' in child table row: {row}")

    # Check for existing Work Updates doc
    existing = frappe.get_list(
        "Work Updates",
        filters={
            "email": data["email"],
            "log_date": today,
            "type": data["type"]
        },
        fields=["name"]
    )

    if existing:
        doc = frappe.get_doc("Work Updates", existing[0].name)
    else:
        # Create new Work Updates document
        doc = frappe.get_doc({
            "doctype": "Work Updates",
            "email": data["email"],
            "log_date": today,
            "type": data["type"],
            "c_log_table": []
        })

    # Map incoming data by UID
    uid_map = {row["uid"]: row for row in data.get("c_log_table", [])}
    updated_uids = []

    # Update existing child rows
    for row in doc.c_log_table:
        if row.uid in uid_map:
            updates = uid_map[row.uid]
            for key, value in updates.items():
                if key != "uid":
                    setattr(row, key, value)
            updated_uids.append(row.uid)

    # Append new child rows that weren't updated
    for uid, row_data in uid_map.items():
        if uid not in updated_uids:
            doc.append("c_log_table", row_data)

    # Save the document
    doc.save(ignore_permissions=ignore_permissions)
    return doc
