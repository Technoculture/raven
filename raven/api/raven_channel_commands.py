import frappe
from raven.api.raven_channel import get_peer_user




@frappe.whitelist()
def get_command_table(bot_name):
    """
    Fetch command_table for a Raven Bot
    """

    if not bot_name:
        return []

    query = """
        SELECT *
        FROM `tabBot Commands Table`
        WHERE
            parent = %(bot_name)s
            AND parenttype = 'Raven Bot'
            AND parentfield = 'command_table'
        ORDER BY idx
    """

    return frappe.db.sql(query, {"bot_name": bot_name}, as_dict=True)

@frappe.whitelist()
def search_dependent_channels(keyword):
    """
    Search keyword in dependent_channels child table
    """

    if not keyword:
        return []

    keyword = f"%{keyword}%"

    query = """
        SELECT
            rb.name AS bot_name,
            rcu.channel_name,
            rcu.response
        FROM `tabRaven Channel Updates` rcu
        INNER JOIN `tabRaven Bot` rb
            ON rb.name = rcu.parent
        WHERE
            rcu.parenttype = 'Raven Bot'
            AND rcu.parentfield = 'dependent_channels'
            AND (
                rcu.channel_name LIKE %(keyword)s
                OR rcu.response LIKE %(keyword)s
            )
        ORDER BY rb.modified DESC
    """

    return frappe.db.sql(query, {"keyword": keyword}, as_dict=True)

@frappe.whitelist()
def get_commands(channel_id:str):
	all_commands = {}
	is_dm = is_dm_to_bot(channel_id=channel_id)
	if is_dm:
			peer_user = get_peer_user(channel_id=channel_id , is_direct_message=is_dm)
			print(peer_user , "peer user")
			bot = frappe.get_doc("Raven Bot" , peer_user.user_id)
			commands = []
			dm_allowed = bot.allow_dm
			if dm_allowed:
				for row in bot.command_table:
					if (row.approved == 1 and row.disable == 0 and row.approved_by):
						
						commands.append({
							"command_name":row.command_name,
							"command_description":row.command_description,
							"command_script":row.command_script

						})

				all_commands[peer_user.user_id] = commands

	else:
		# Lets assume there are mutiple bots installed and each bot in his/her/** command list has got multiple commands
		# will be listed through out the channel in which they are conjured up.  
		# need to remove or atleast verify List
		values = search_dependent_channels(channel_id)
		for bot_name in values:
			insect = get_command_table(bot_name.bot_name)
			peer_user = get_peer_user(channel_id=channel_id , is_direct_message=is_dm)

			print(insect , "peer_ser" , bot_name)

			commands = []
			for row in insect:
				if (row.approved == 1 and row.disable == 0 and row.approved_by):
					commands.append({
							"command_name":row.command_name,
							"command_description":row.command_description,
							"command_script":row.command_script

						})
				
			all_commands[bot_name.bot_name] = commands	
	return all_commands

@frappe.whitelist()
def is_dm_to_bot(channel_id:str):
	try:
		channel = frappe.get_doc("Raven Channel" , channel_id)
		return channel.is_direct_message
	except frappe.DoesNotExistError:
		frappe.throw(f"Raven Channel with ID {channel_id} not found")



def get_installed_bots(channel_id):
	# cache_key = f"install_bot_{channel_id}"
	# There are only two hard things in Computer Science Cache Invalidation and Naming Things ~ Some Important Guy
	# Perhaps lets throw these into shredder with a button on ui otherwise Underperfoming Cron JOB (TTL) is to cache invalidation what wrapper is to Linux Kernal Devs. 
	# cached_bots = frappe.cache.get_value(cache_key)
	# if cached_bots:
	# 	return cached_bots
	raven_channel = frappe.get_doc("Raven Channel" , channel_id)
	print(channel_id , "channel_id" , raven_channel)
	installed_bots_table = raven_channel.bots_table
	bots = []
	if installed_bots_table:
		for bot in installed_bots_table:
			bots.append(bot.bot_name)
	else:
		# "No Bots" found try some MMORPG even players seems to be bots there
		bots = None
	if bots:
		frappe.cache.set_value(cache_key , bots)

	return bots