
import frappe
from datetime import datetime
from raven.utils import push_message_to_channel 

def post_work_plan():
    channel_id = "updates"
    text = "Daily Work Plan:\nPlease update your Work Plan for today!"
    
    bot_user_id = "HelloBot"
    push_message_to_channel(channel_id, text, is_bot_message=True, bot_user=bot_user_id)



def post_work_update():
    channel_id = "updates"
    text = "Daily Work Plan:\nPlease update your tasks for today!"
    
    bot_user_id = "HelloBot"
    push_message_to_channel(channel_id, text, is_bot_message=True, bot_user=bot_user_id)


def get_todays_work_updates():
   
    today = datetime.today().date()

    filters = {
        "creation": [">=", f"{today} 00:00:00"],
        "creation": ["<=", f"{today} 23:59:59"]
    }

  

    entries = frappe.get_all(
        "Work Updates",
        filters=filters,
        fields=["name", "email"],
        order_by="creation desc"
    )

    return entries
