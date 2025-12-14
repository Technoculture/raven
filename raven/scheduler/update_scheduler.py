import frappe
from frappe.utils import nowdate
from raven.utils import message_dispatch


def create_direct_message_channel(user_id , text):
     channel_name = frappe.db.get_value(
		"Raven Channel",
		filters={
			"is_direct_message": 1,
			"channel_name": [
				"in",
				["Daily Update Bot" + " _ " + user_id, user_id + " _ " + "Daily Update Bot"],
			],
		},
		fieldname="name",
	)
     if channel_name:
          message_dispatch(channel_name=channel_name , bot="Daily Update Bot" , response=text)
     else:
          channel = frappe.get_doc(
			{
				"doctype": "Raven Channel",
		 		"channel_name": "Daily Update Bot" + " _ " + user_id,
		 		"is_direct_message": 1,
		 		"is_self_message": "Daily Update Bot" == user_id,
		 	}
		 )
          channel.flags.is_created_by_bot = True
          channel.insert()
          message_dispatch(channel_name=channel.name , bot="Daily Update Bot" , response=text)

          
          
          

def check_morning_plan():
    today = nowdate()

    raven_users = frappe.get_all(
        "Raven User",
        filters={"enabled": 1, "type": "User"},
        fields=["user"]  
    )

    missing_plan_users = []

    for ru in raven_users:
        email = ru.user

        has_plan = frappe.db.exists(
            "Daily Work Updates",
            {
                "email": email,
                "log_date": today,
                "type": "Plan"
            }
        )


        if not has_plan:
            missing_plan_users.append(email)

    for user in missing_plan_users:
         create_direct_message_channel(user_id=user , text="Update your Morning Work Plan")
    


def check_evening_update():
    today = nowdate()

    raven_users = frappe.get_all(
        "Raven User",
        filters={"enabled": 1, "type": "User"},
        fields=["user"]  
    )

    missing_plan_users = []

    for ru in raven_users:
        email = ru.user

        has_plan = frappe.db.exists(
            "Daily Work Updates",
            {
                "email": email,
                "log_date": today,
                "type": "Update"
            }
        )

        if not has_plan:
            missing_plan_users.append(email)


    for user in missing_plan_users:
         create_direct_message_channel(user_id=user , text="Update your Evening Work Update")

    return missing_plan_users
