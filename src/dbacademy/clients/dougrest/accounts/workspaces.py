__all__ = ["Workspace", "Workspaces", "STATUS_FAILED", "STATUS_PROVISIONING", "STATUS_UNKNOWN"]

from typing import Any, Type, Dict
from dbacademy.clients.dougrest.client import DatabricksApi, DatabricksApiException
from dbacademy.clients.dougrest.accounts import AccountsApi
from dbacademy.common import overrides
from dbacademy.clients.rest.common import HttpMethod, HttpReturnType, HttpStatusCodes, IfExists, IfNotExists
from dbacademy.clients.dougrest.accounts.crud import AccountsCRUD

STATUS_FAILED = "FAILED"
STATUS_RUNNING = "RUNNING"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_PROVISIONING = "PROVISIONING"


class Workspace(DatabricksApi):

    def __init__(self, data_dict, accounts_api: AccountsApi):
        hostname = data_dict.get("deployment_name")
        auth = accounts_api.session.headers["Authorization"]
        self.accounts = accounts_api

        super().__init__(hostname + ".cloud.databricks.com",
                         username=accounts_api.username,
                         authorization_header=auth)
        self.update(data_dict)

    def wait_until_ready(self, timeout_seconds=30 * 60):
        import time

        start = time.time()

        while self.get("workspace_status") == STATUS_PROVISIONING:
            workspace_id = self.get("workspace_id")
            data = self.accounts.workspaces.get_by_id(workspace_id)
            self.update(data)
            if time.time() - start > timeout_seconds:
                raise TimeoutError(f"Workspace not ready after waiting {timeout_seconds} seconds")
            if self.get("workspace_status") == STATUS_PROVISIONING:
                time.sleep(15)

        final_status = self.get("workspace_status")
        if final_status == STATUS_FAILED:
            return False
        elif final_status != STATUS_RUNNING:
            return False

        return True

    def wait_until_gone(self, timeout_seconds=30*60):
        import time

        start = time.time()
        workspace_id = self.get("workspace_id")

        while True:
            if not self.accounts.workspaces.get_by_id(workspace_id, if_not_exists="ignore"):
                break
            if time.time() - start > timeout_seconds:
                raise TimeoutError(f"Workspace not ready after waiting {timeout_seconds} seconds")
            time.sleep(15)

    @overrides
    def api(self,
            _http_method: HttpMethod,
            _endpoint_path: str,
            _data: Dict[str, Any] = None, *,
            _expected: HttpStatusCodes = None,
            _result_type: Type[HttpReturnType] = dict,
            _base_url: str = None,
            **data: Any) -> HttpReturnType:

        self.wait_until_ready()
        try:
            return super().api(_http_method, _endpoint_path, _data,
                               _expected=_expected, _result_type=_result_type,
                               _base_url=_base_url, **data)
        except DatabricksApiException as e:
            if e.http_code == 401 and self.username is not None:
                try:
                    self.add_as_admin(self.username)
                except DatabricksApiException:
                    raise e
                return super().api(_http_method, _endpoint_path, _data,
                                   _expected=_expected, _result_type=_result_type,
                                   _base_url=_base_url, **data)
            else:
                raise e

    def add_as_admin(self, username):
        user = self.accounts.users.get_by_username(username, if_not_exists="error")
        user_id = user.get("id")
        workspace_id = self.get("workspace_id")
        return self.accounts.api("PUT", f"workspaces/{workspace_id}/roleassignments/principals/{user_id}",
                                 _base_url=f"/api/2.0/preview/accounts/{self.accounts.account_id}/", roles=["ADMIN"])


class Workspaces(AccountsCRUD):
    # Cannot be imported due to circular dependency

    # noinspection PyUnresolvedReferences
    def __init__(self, client: "AccountsApi"):
        from dbacademy.clients.dougrest.accounts import AccountsApi
        super().__init__(client, "/workspaces", "workspace")

        # noinspection PyTypeChecker
        self.client: AccountsApi = client

    @overrides
    def _wrap(self, item: Dict[str, Any]) -> Workspace:
        if "workspace_id" not in item:
            raise ValueError(f"Invalid response.  Expected workspace dict, found: {item}")
        return Workspace(item, self.client) if item is not None else None

    def get_by_deployment_name(self, name, if_not_exists: IfNotExists = "error"):
        """
        Returns the first {singular} found that with the given deployment_name.
        Raises exception if not found.
        """
        result = next((item for item in self._list() if item["deployment_name"] == name), None)
        if result is None and if_not_exists == "error":
            raise DatabricksApiException(f"{self.singular} with deployment_name '{name}' not found", 404)
        return self._wrap(result)

    @overrides(check_signature=False)
    def create(self, workspace_name, *, deployment_name=None, region, pricing_tier=None,
               credentials=None, credentials_id=None, credentials_name=None,
               storage_configuration=None, storage_configuration_id=None, storage_configuration_name=None,
               network=None, network_id=None, network_name=None,
               private_access_settings=None, private_access_settings_id=None, private_access_settings_name=None,
               services_encryption_key=None, services_encryption_key_id=None, services_encryption_key_name=None,
               storage_encryption_key=None, storage_encryption_key_id=None, storage_encryption_key_name=None,
               fetch: bool = None, if_exists: IfExists = "error") -> Workspace:

        if credentials_id:
            pass
        elif credentials:
            credentials_id = credentials[f"credentials_id"]
        elif credentials_name:
            credentials_id = self.client.credentials.get_by_name(credentials_name)["credentials_id"]
        else:
            raise DatabricksApiException("Must provide one of credentials, credentials_id, or credentials_name")

        if storage_configuration_id:
            pass
        elif storage_configuration:
            storage_configuration_id = storage_configuration[f"storage_configuration_id"]
        elif storage_configuration_name:
            storage_configuration_id = self.client.storage.get_by_name(storage_configuration_name)[
                "storage_configuration_id"]
        else:
            raise DatabricksApiException("Must provide one of credentials, credentials_id, or credentials_name")

        if network_id:
            pass
        elif network:
            network_id = network[f"network_id"]
        elif network_name:
            network_id = self.client.networks.get_by_name(network_name)["network_id"]

        if private_access_settings_id:
            pass
        elif private_access_settings:
            private_access_settings_id = private_access_settings[f"private_access_settings_id"]
        elif private_access_settings_name:
            private_access_settings_id = self.client.private_access.get_by_name(private_access_settings_name)[
                "private_access_settings_id"]

        if services_encryption_key_id:
            pass
        elif services_encryption_key:
            services_encryption_key_id = services_encryption_key[f"customer_managed_key_id"]
        elif services_encryption_key_name:
            services_encryption_key_id = self.client.keys.get_by_name(services_encryption_key_name)[
                "customer_managed_key_id"]

        if storage_encryption_key_id:
            pass
        elif storage_encryption_key:
            storage_encryption_key_id = storage_encryption_key[f"customer_managed_key_id"]
        elif storage_encryption_key_name:
            storage_encryption_key_id = self.client.keys.get_by_name(storage_encryption_key_name)[
                "customer_managed_key_id"]

        spec = {
            "workspace_name": workspace_name,
            "deployment_name": deployment_name,
            "aws_region": region,
            "pricing_tier": pricing_tier,
            "credentials_id": credentials_id,
            "storage_configuration_id": storage_configuration_id,
            "network_id": network_id,
            "private_access_settings_id": private_access_settings_id,
            "managed_services_customer_managed_key_id": services_encryption_key_id,
            "storage_customer_managed_key_id": storage_encryption_key_id,
        }
        for key, value in list(spec.items()):
            if value is None or value == "":
                del spec[key]

        # TODO fix error or remove TODO statement
        # noinspection PyTypeChecker
        return self.create_by_example(spec, fetch=fetch, if_exists=if_exists)
