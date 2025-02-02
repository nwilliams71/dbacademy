__all__ = ["JobsClient"]

from typing import Dict, Any, Optional
from dbacademy.clients.rest.common import ApiClient, ApiContainer
from dbacademy.clients.databricks.jobs.job_config_classes import JobConfig


class JobsClient(ApiContainer):

    def __init__(self, client: ApiClient):
        from dbacademy.common import validate
        from dbacademy.clients.databricks import DBAcademyRestClient

        self.client: DBAcademyRestClient = validate.any_value(DBAcademyRestClient, client=client, required=True)
        self.base_uri = f"{self.client.endpoint}/api/2.1/jobs"

    def create_from_config(self, config: JobConfig) -> str:
        return self.create_from_dict(config.params)

    def create_from_dict(self, params: Dict[str, Any]) -> str:
        response = self.client.api("POST", f"{self.base_uri}/create", params)
        return response.get("job_id")

    def run_now(self, job_id: str, notebook_params: Dict[str, Any] = None):
        payload = {
            "job_id": job_id
        }
        if notebook_params is not None:
            payload["notebook_params"] = notebook_params

        return self.client.api("POST", f"{self.client.endpoint}/api/2.0/jobs/run-now", payload)

    def get_by_id(self, job_id):
        return self.client.api("GET", f"{self.client.endpoint}/api/2.0/jobs/get?job_id={job_id}")

    def get_by_name(self, name: str):
        offset = 0  # Start with zero
        limit = 25  # Default maximum

        def search(jobs_list):
            job_ids = [j.get("job_id") for j in jobs_list if name == j.get("settings").get("name")]
            return (False, None) if len(job_ids) == 0 else (True, self.get_by_id(job_ids[0]))

        target_url = f"{self.base_uri}/list?limit={limit}"
        response = self.client.api("GET", target_url)
        jobs = response.get("jobs", list())

        found, job = search(jobs)
        if found:
            return job

        while response.get("has_more", False):
            offset += limit
            response = self.client.api("GET", f"{target_url}&offset={offset}")
            jobs = response.get("jobs", list())

            found, job = search(jobs)
            if found:
                return job

        return None

    def list_n(self, offset: int = 0, limit: int = 25, expand_tasks: bool = False):
        limit = min(25, limit)
        offset = max(0, offset)

        target_url = f"{self.base_uri}/list?offset={offset}&limit={limit}&expand_tasks={expand_tasks}"
        response = self.client.api("GET", target_url)
        return response.get("jobs", list())

    def list(self, expand_tasks: bool = False):
        offset = 0  # Start with zero
        limit = 100  # Our default maximum

        target_url = f"{self.base_uri}/list?limit={limit}&expand_tasks={expand_tasks}"
        response = self.client.api("GET", target_url)
        all_jobs = response.get("jobs", list())

        while response.get("has_more", False):
            offset += limit
            page_token = response.get('next_page_token')
            response = self.client.api("GET", f"{target_url}&page_token={page_token}")
            all_jobs.extend(response.get("jobs", list()))

        return all_jobs

    def delete_by_id(self, job_id):
        self.client.api("POST", f"{self.client.endpoint}/api/2.0/jobs/delete", job_id=job_id)

    def delete_by_name(self, job_names, success_only: bool) -> None:
        if type(job_names) == dict:
            job_names = list(job_names.keys())
        elif type(job_names) == list:
            job_names = job_names
        elif type(job_names) == str:
            job_names = [job_names]
        else:
            raise TypeError(f"Unsupported type: {type(job_names)}")

        # Get a list of all jobs
        jobs = self.list()

        s = "s" if len(jobs) != 1 else ""
        self.client.vprint(f"Found {len(jobs)} job{s}.")

        assert type(success_only) == bool, f"Expected \"success_only\" to be of type \"bool\", found \"{success_only}\"."
        self.client.vprint(f"...deleting successful jobs only: {success_only}")

        deleted = 0

        for job_name in job_names:
            for job in jobs:
                if job_name == job.get("settings").get("name"):
                    job_id = job.get("job_id")

                    runs = self.client.runs().list_by_job_id(job_id)
                    s = "s" if len(runs) != 1 else ""
                    self.client.vprint(f"Found {len(runs)} run{s} for job {job_id}")
                    delete_job = True

                    for run in runs:
                        state = run.get("state")
                        result_state = state.get("result_state", None)
                        life_cycle_state = state.get("life_cycle_state", None)

                        if success_only and life_cycle_state != "TERMINATED":
                            delete_job = False
                            self.client.vprint(f""" - The job "{job_name}" was not "TERMINATED" but "{life_cycle_state}", this job must be deleted manually""")
                        if success_only and result_state != "SUCCESS":
                            delete_job = False
                            self.client.vprint(f""" - The job "{job_name}" was not "SUCCESS" but "{result_state}", this job must be deleted manually""")

                    if delete_job:
                        self.client.vprint(f"...Deleting job #{job_id}, \"{job_name}\"")
                        for run in runs:
                            run_id = run.get("run_id")
                            self.client.vprint(f"""   - Deleting run #{run_id}""")
                            self.client.runs().delete(run_id)

                        self.delete_by_id(job_id)
                        deleted += 1

        self.client.vprint(f"...deleted {deleted} jobs")
        return None

    def update_schedule(self, *,
                        _job_id: Optional[str],
                        _paused: Optional[bool],
                        _quartz_cron_expression: Optional[str],
                        _timezone_id: Optional[str]) -> Dict[str, Any]:

        paused = None if _paused is None else ("PAUSED" if _paused else "UNPAUSED")

        job = self.get_by_id(_job_id)
        settings = job.get("settings")
        schedule = settings.get("schedule")

        payload = {
            "job_id": _job_id,
            "new_settings": {
                "schedule": {
                    "timezone_id": _timezone_id or schedule.get("timezone_id"),
                    "quartz_cron_expression": _quartz_cron_expression or schedule.get("quartz_cron_expression"),
                    "pause_status": paused or schedule.get("pause_status"),
                }
            }
        }
        self.client.api("POST", f"{self.base_uri}/update", payload)
        return self.get_by_id(_job_id)

    def update_continuous(self, *, _job_id: str, _paused: bool) -> Dict[str, Any]:
        payload = {
            "job_id": _job_id,
            "new_settings": {
                "continuous": {
                    "pause_status": "PAUSED" if _paused else "UNPAUSED"
                }
            }
        }
        self.client.api("POST", f"{self.base_uri}/update", payload)
        return self.get_by_id(_job_id)

    def update_trigger(self, *,
                       _job_id: str,
                       _paused: Optional[bool],
                       _url: Optional[str],
                       _min_time_between_triggers_seconds: Optional[int],
                       _wait_after_last_change_seconds: Optional[int]) -> Dict[str, Any]:

        paused = None if _paused is None else ("PAUSED" if _paused else "UNPAUSED")

        job = self.get_by_id(_job_id)
        settings = job.get("settings")
        trigger = settings.get("trigger")
        file_arrival = trigger.get("file_arrival")

        payload = {
            "job_id": _job_id,
            "new_settings": {
                "trigger": {
                    "pause_status": paused or trigger.get("pause_status"),
                    "file_arrival": {
                        "url": _url or file_arrival.get("url"),
                        "min_time_between_triggers_seconds": _min_time_between_triggers_seconds or file_arrival.get("min_time_between_triggers_seconds"),
                        "wait_after_last_change_seconds": _wait_after_last_change_seconds or file_arrival.get("wait_after_last_change_seconds"),
                    }
                }
            }
        }
        self.client.api("POST", f"{self.base_uri}/update", payload)
        return self.get_by_id(_job_id)
