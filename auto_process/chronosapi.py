import datetime
import json
import re
import requests

from dataadmin import settings

chronos_dic = {
    "name": None,                    # Name of job, required.
    "description": None,             # Description of job. no need.
    "command": None,                 # Command to execute, required.
    "parents": None,                 # An array of parent jobs for a dependent job.
                                     # If specified, schedule must not be specified.
    "owner": None,                   # Email address(es) to send job failure notifications.
                                     # Use comma-separated list for multiple addresses.
    "ownerName": None,               # Name of the individual responsible for the job.
    "schedule": None,                # ISO 8601 repeating schedule for this job.
                                     # If specified, parents must not be specified.
    "executor": None,                # Mesos executor. By default Chronos uses the Mesos command executor.
    "epsilon": "PT30M",              # If Chronos misses the scheduled run time for any reason,
                                     # it will still run the job if the time is within this interval.
    "async": False,                  # Whether the job runs in the background or not

    "disabled": False,               # If set to true, this job will not be run.
    "concurrent": False,             # If set to true, this job may execute concurrently (multiple instances).
    "cpus": 0.1,                     # Amount of Mesos CPUs for this job.
    "mem": 128,                      # Amount of Mesos Memory (in MB) for this job.
    "disk": 256,                     # Amount of Mesos disk (in MB) for this job.
    "scheduleTimeZone": None,        # The time zone for the given schedule, specified in the tz database format.

}


class MissingParameters(Exception):
    pass


class ChronosAPIError(Exception):
    pass


def varify_paramters(f):
    def wrapper(self, dic):
        chronos = {k: v for k, v in dic.items() if dic[k] is not None}
        if f.__name__ in ["searching_job", "deleting_job", "killing_all_tasks", "manual_start_job"]:
            if chronos["name"]:
                return f(self, chronos)
            else:
                raise MissingParameters("Missing parameters!")
        else:
            if all([chronos["name"], chronos["owner"], chronos["command"]]):
                res = re.match(r"^[\w-]+(\.[\w-]+)*@[\w-]+(\.[\w-]+)+$", chronos["owner"])
                if res:
                    return f(self, chronos)
                else:
                    raise ValueError("owner must be an email address")
            else:
                raise MissingParameters("Missing parameters!")

    return wrapper


class Chronos:
    def __init__(self, name):
        self.url = settings.CHRONOS[name]["url"]
        # self.url = os.environ["CHRONOS"]["name"]

    def listing_jobs(self):
        """
        A job listing.
        :return:{"status_code": 200, "content":"[{},{}...{}]"}
        """
        url = "{}{}".format(self.url, "scheduler/jobs")
        return self._request(method="get", url=url)

    def describing_dependency_graph(self):
        """
        :return:
        """
        url = "{}{}".format(self.url, "scheduler/graph/dot")
        return self._request(method="get", url=url)

    @varify_paramters
    def searching_job(self, dic):
        """
        Get the job definition according to the job name.
        :return:{"status_code": 200, "content":"[{...}]"}
        """
        url = "{}scheduler/jobs/search?name={}".format(self.url, dic["name"])
        return self._request(method="get", url=url)

    @varify_paramters
    def deleting_job(self, dic):
        """
        delete the job according to the job name.
        :return: {'status_code': 204, 'content': 'success'}
        """
        url = "{}scheduler/job/{}".format(self.url, dic["name"])
        return self._request(method="delete", url=url)

    @varify_paramters
    def killing_all_tasks(self, dic):
        """
        Killing tasks for a job
        :return:{'status_code': 204, 'content': 'success'}
        """
        url = "{}scheduler/task/kill/{}".format(self.url, dic["name"])
        return self._request(method="delete", url=url)

    @varify_paramters
    def manual_start_job(self, dic):
        """
        Manually start a job
        :return: {"status_code": 204, "content":"[{...}]"}
        """
        url = "{}scheduler/job/{}".format(self.url, dic["name"])
        return self._request(method="put", url=url)

    @varify_paramters
    def adding_scheduled_job(self, dic):
        """
        Manually add a job
        :return: {'status_code': 204, 'content': 'success'}
        """
        if "schedule" not in dic:
            dic["schedule"] = "R1//P"
        url = "{}{}".format(self.url, "scheduler/iso8601")
        return self._request(method="post", url=url, dic=dic)

    @varify_paramters
    def adding_dependent_job(self, dic):
        """
        Manually add a job with parents field. parents must be a list
        :return:
        """
        if dic["parents"] and isinstance(dic["parents"], list):
            url = "{}{}".format(self.url, "scheduler/dependency")
            return self._request(method="post", url=url, dic=dic)
        else:
            raise MissingParameters("Missing parents field and it must be a list!")

    def _request(self, method=None, url=None, dic=None):
        if method == "get":
            resp = requests.get(url=url)
        elif method == "post":
            resp = requests.post(url=url, json=dic)
        elif method == "delete":
            resp = requests.delete(url=url, json=dic)
        else:
            resp = requests.put(url=url, json=dic)
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(reponse):
        status_code = reponse.status_code
        content = reponse.text
        if content:
            try:
                content = json.loads(content)
            except Exception:
                pass
        if status_code >= 400:
            if status_code == 500:
                content = "wrong parameters"
            raise ChronosAPIError("The API returned status code %d, content: %s; Maybe wrong parameters!"
                                  % (status_code, content))
        content = "success" if not content else content
        return {"status_code": status_code, "content": content}

    def __str__(self):
        resp = self.listing_jobs()
        return "{}".format([i["name"] for i in resp["content"]])


if __name__ == '__main__':
    chronos = Chronos("default")
    # 输出全部任务名称
    print(chronos)
    # 任务列表
    # res = chronos.listing_jobs()
    # print(res)
    # 任务关系结构
    # res = chronos.describing_dependency_graph()
    # print(res)
    # 模糊查找任务
    # chronos_dic["name"] = "test1"
    # res = chronos.searching_job(chronos_dic)
    # print(res)
    # 添加一个任务
    chronos_dic["name"] = "xxxx"
    chronos_dic["owner"] = "xxxx@qq.com"
    chronos_dic["command"] = "ls"
    res = chronos.adding_scheduled_job(chronos_dic)
    print(res)
    # 针对现有任务添加一个依赖关系的任务
    # chronos_dic["name"] = "xxxx_child"
    # chronos_dic["owner"] = "xxxx@qq.com"
    # chronos_dic["command"] = "sleep 15"
    # chronos_dic["parents"] = ["test1"]
    # res = chronos.adding_dependent_job(chronos_dic)
    # print(res)
    # 手动启动任务
    # chronos_dic["name"] = "xxxx"
    # res = chronos.manual_start_job(chronos_dic)
    # print(res)
    # 终止正在运行的任务
    # chronos_dic["name"] = "xxxx"
    # res = chronos.killing_all_tasks(chronos_dic)
    # print(res)
    # 删除任务
    # chronos_dic["name"] = "xxxx"
    # res = chronos.deleting_job(chronos_dic)
    # print(res)
    # chronos_dic["name"] = "xxxx_child"
    # res = chronos.deleting_job(chronos_dic)
    # print(res)
