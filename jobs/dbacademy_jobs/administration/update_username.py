import os

from dbacademy.clients.databricks import accounts

account_id = os.environ.get("WORKSPACE_SETUP_CURR_ACCOUNT_ID")
username = os.environ.get("WORKSPACE_SETUP_CURR_USERNAME")
password = os.environ.get("WORKSPACE_SETUP_CURR_PASSWORD")

accounts = accounts.from_args_aws(account_id=account_id,
                                  username=username,
                                  password=password)

for i in range(0, 250+1):
    username = f"class+{i:03d}@databricks.com"
    user = accounts.scim.users.get_by_username(username)
    user_id = user.get("id")

    print(f"processing {username}.")
    updated_user = accounts.scim.users.update_by_id(user_id, first_name=f"Participant", last_name=f"#{i:03d}")

pass
