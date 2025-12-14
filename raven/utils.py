import frappe
import json
import datetime
import io
import contextlib


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


def get_bot_commands(bot_name):
    try:
        doc = frappe.get_doc("Raven Bot", bot_name)
        command_table = []        
        if doc.command_table:
            for row in doc.command_table:
                command_table.append({
                    'command': row.command_name,
                    'description': row.command_description,
                    'script': row.command_script
                })

        bot_color = doc.bot_color if hasattr(doc, 'bot_color') else None
        channel_names = doc.channel_names if hasattr(doc, 'channel_names') else None

        return {
            'command_table': command_table,
            'bot_color': bot_color,
            'channel_names': channel_names
        }
    
    except frappe.DoesNotExistError:
        print(f"Bot with name '{bot_name}' not found.")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


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

def get_bot_command(bot_name:str):
	commands = frappe.get_doc(
    "Raven Bot",bot_name
)
	return commands
	



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


# Handling Non Agentic Bots
def handle_non_agentic_bots(message , bot):
	result = bifurcate_command(message_dict=message.as_dict())
	return result
    

def bifurcate_command(message_dict):
    """
    Extracts and transforms message details into a simplified structure:
    - For Text messages: msgType, command, chat
    - For File messages: msgType, file
    Returns None if required fields are missing or malformed.
    """
    try:
        message_type = message_dict.get("message_type")
        if not message_type:
            return None

        result = {
            "msgType": message_type
        }

        if message_type == "File":
            file_path = message_dict.get("file")
            if not file_path:
                return None
            result["file"] = file_path
            return result

        elif message_type == "Text":
            json_str = message_dict.get("json")
            if not json_str:
                return None

            doc_json = json.loads(json_str)
            content_items = doc_json.get("content", [])[0].get("content", [])

            command_mention = None
            text_value = None

            for item in content_items:
                if item.get("type") == "commandMention":
                    command_mention = item.get("attrs", {}).get("id")
                elif item.get("type") == "text":
                    text_value = item.get("text")

            if not command_mention or not text_value:
                return None

            result["command"] = command_mention
            result["chat"] = text_value.strip()
            return result

        return None

    except (json.JSONDecodeError, IndexError, AttributeError, TypeError):
        return None




def execute_bot_script(script, variables=None, allowed_builtins=None, entrypoint=None):
    """
    Execute a script with injected variables and capture output, result,
    and log the execution status.
    """

    output_buffer = io.StringIO()
    error = None
    result = None

    logger = frappe.logger("bot_script")

    if allowed_builtins is None:
        allowed_builtins = {
            "print": print,
            "len": len,
            "range": range,
            "__import__": __import__,
        }

    safe_globals = {
        "__builtins__": allowed_builtins
    }

    if variables:
        safe_globals.update(variables)

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(script, safe_globals)

            if entrypoint and entrypoint in safe_globals:
                result = safe_globals[entrypoint](safe_globals.get("data"))

            elif "result" in safe_globals:
                result = safe_globals["result"]

        success = True

        logger.info({
            "event": "bot_script_executed",
            "status": "success",
            "entrypoint": entrypoint,
            "output": output_buffer.getvalue().strip(),
            "result": result,
        })

    except Exception as e:
        success = False
        error = str(e)

        logger.error({
            "event": "bot_script_error",
            "status": "failed",
            "entrypoint": entrypoint,
            "error": error,
            "output": output_buffer.getvalue().strip(),
        })

    return {
        "success": success,
        "output": output_buffer.getvalue().strip(),
        "error": error,
        "result": result,
    }


def get_map(doctype_name):
    meta = frappe.get_meta(doctype_name)
    data = {}

    for df in meta.fields:
        if df.fieldtype in ("Section Break", "Column Break"):
            continue

        if df.fieldtype == "Table":
            child_meta = frappe.get_meta(df.options)
            child_row = {}
            for child_df in child_meta.fields:
                if child_df.fieldtype not in ("Section Break", "Column Break"):
                    child_row[child_df.fieldname] = None
            data[df.fieldname] = [child_row]
        else:
            data[df.fieldname] = None

    return data



def dependent_channel_serializer(channel_list:list[str], status:bool, response:str, bot:str):
    """
    List of the channels where the bot has been subrcribed to
    Not the client ones but the ones that that have been mentioned 
    in the bot commands
    Arguments:
        channel_list (list[str]): List of dependent channel names.
        status (bool): Indicates success (True) or failure (False).
        response (str): Message content to be dispatched.
        bot (str): Name or ID of the bot that owns the message.
    """
    if not bot:
         frappe.throw("I need the name of bot, bot")
    if not channel_list:
         frappe.logger().info(f"Tell the ops guy to feed the dependents channel")

    if status:
        for channel_name in channel_list:
            message_dispatch(channel_name=channel_name, bot=bot , response=response)
    else:
        last_channel = channel_list[-1]
        message_dispatch(channel_name=last_channel , bot=bot , response=response)
    
          
          

      

def message_dispatch(channel_name, bot , response):
    """
    Get the dependant Channels List and dispatch to them
    The messages Stored in the Success Table based of 
    the result that we have recieved.

    Args:
        channel_name (str): Channel where the messge has to be dispatched
    """
    bot_user = frappe.get_cached_value("Raven Bot", bot , "bot_user")
    print(bot_user , bot , "hello" , channel_name , "channel_name")
    value = frappe.get_doc({
          "doctype":"Raven Message",
          "channel_id":channel_name,
          "text":response,
          "content":response,
          "message_type":"Text",
          "is_bot_message":1,
          "bot":bot,
          "owner":bot_user


    }).insert(ignore_permissions=True)

    commited =  frappe.db.commit()
    print("Hello" , value , commited)


def data_builder(doctype_name, overrides=None):
    """
    Get the default structure of a DocType (including child tables),
    and apply the values provided in `overrides`.

    Args:
        doctype_name (str): The parent DocType
        overrides (dict): Values to insert into the default structure

    Returns:
        dict: Fully structured data dict
    """
    base_data = get_map(doctype_name)

    def deep_update(target, updates):
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                deep_update(target[key], value)
            else:
                target[key] = value

    if overrides:
        deep_update(base_data, overrides)

    return base_data



def get_overrides_for_command(doctype, command_context, message):
    """
    Generates overrides based on command context.

    Args:
        doctype (str): Target DocType
        command_context (dict): The parsed command tree
        message (object): The message object (e.g., self)

    Returns:
        dict: Overrides to apply to base data
    """

    if doctype == "Daily Work Updates":
        return {
            "log_date": datetime.date.today(),
            "email": message.owner,
            "type": message.type,
            "log_table": [
                {
                    "uid": message.name,
                    "task": command_context.get("chat"),
                    "time_log": datetime.datetime.now().time()
                }
            ]
        }

    else:
        return {}


def get_username_by_email(email):
    print(email, "email dispatched")
    user = frappe.get_value("Raven User", {"user": email}, "full_name")
    print(user , "user is ddefined")
    return user
