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

          


def dispatch_managers():
    values = check_missing_daily_updates()
    for val in values:
        reporting_manager = get_reporting_manager_email(val)
        message_dispatch(reporting_manager ,f"The user {val} has not updated the daily status")


def get_reporting_manager_email(email):
  
    try:
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": email},
            ["name", "employee_name", "reports_to"],
            as_dict=True
        )
        
        if not employee:
            return {
                "success": False,
                "manager_email": None,
                "manager_user_id": None,
                "manager_name": None,
                "employee_name": None,
                "message": f"No employee found with user_id: {email}"
            }
        
        if not employee.reports_to:
            return {
                "success": False,
                "manager_email": None,
                "manager_user_id": None,
                "manager_name": None,
                "employee_name": employee.employee_name,
                "message": f"Employee {employee.employee_name} has no reporting manager assigned"
            }
        
        manager = frappe.db.get_value(
            "Employee",
            employee.reports_to,
            ["employee_name", "user_id"],
            as_dict=True
        )
        
        if not manager:
            return {
                "success": False,
                "manager_email": None,
                "manager_user_id": None,
                "manager_name": None,
                "employee_name": employee.employee_name,
                "message": "Reporting manager record not found"
            }
        
        return {
            "success": True,
            "manager_email": manager.user_id,
            "manager_user_id": manager.user_id,
            "manager_name": manager.employee_name,
            "employee_name": employee.employee_name,
            "message": "Success"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_reporting_manager_email: {str(e)}")
        return {
            "success": False,
            "manager_email": None,
            "manager_user_id": None,
            "manager_name": None,
            "employee_name": None,
            "message": f"Error: {str(e)}"
        }
    


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


def check_missing_daily_updates():
    """
    Check if users are missing either morning plan or evening update
    
    Returns:
        dict: {
            "missing_plan": list of emails missing morning plan,
            "missing_update": list of emails missing evening update,
            "missing_either": list of emails missing either one or both
        }
    """
    today = nowdate()

    raven_users = frappe.get_all(
        "Raven User",
        filters={"enabled": 1, "type": "User"},
        fields=["user"]  
    )

    missing_either = []

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

        has_update = frappe.db.exists(
            "Daily Work Updates",
            {
                "email": email,
                "log_date": today,
                "type": "Update"
            }
        )


        
        if not has_plan or not has_update:
            missing_either.append(email)
    return missing_either
   
