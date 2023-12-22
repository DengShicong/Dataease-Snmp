import time
from concurrent import futures
from collect_device_name import CollectDeviceName
from connect import Connection
from device_time import DeviceTime
from esr_health import EsrHealth
from temperatrue import TEMP
from through_out import Through
from vlan_through_out import VlanThroughOut

# 初始化对象
collector = CollectDeviceName()
connection = Connection()
deviceTime = DeviceTime()
esrHealth = EsrHealth()
temp = TEMP()
through_out = Through()
vlanThroughOut = VlanThroughOut()


# 定义任务执行函数
def run_task(task_func):
    while True:
        try:
            task_func()
        except Exception as e:
            print(f"Error executing {task_func.__name__}: {e}")
        time.sleep(10)


# 创建线程池并分配任务
def main():
    with futures.ThreadPoolExecutor(max_workers=7) as executor:
        tasks = [
            collector.job,
            connection.job,
            deviceTime.job,
            esrHealth.collect_data_and_update_db,
            temp.job,
            through_out.job,
            vlanThroughOut.job
        ]

        # 提交任务到线程池
        future_to_task = {executor.submit(run_task, task): task for task in tasks}

        # 等待所有任务完成
        for future in futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                future.result()
            except Exception as e:
                print(f"Task {task.__name__} generated an exception: {e}")


if __name__ == "__main__":
    main()