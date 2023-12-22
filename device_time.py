import schedule as schedule
from pysnmp.hlapi import *
import pymysql
import time
from datetime import datetime

class DeviceTime:

    def __init__(self):
        # 连接数据库
        # 数据库信息
        self.smysql_host = "10.10.10.244"
        self.mysql_user = "root"
        self.mysql_password = "Password123@mysql"
        self.mysql_db = "ale"
        self.mysql_table = "device_time"

    # 提供的IP地址
    ips_by_device_type = {
        'OmniSwitch': ['10.10.10.181', '10.10.10.152', '10.10.10.241','10.10.10.68','10.10.10.226','10.10.10.227','10.10.10.56'],
    }

    # SNMP数据收集函数
    def get_snmp_data(host, community, oid):
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((host, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            print(f"Error: {errorIndication}")
            return None
        elif errorStatus:
            print(f"SNMP Error: {errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1][0] if errorIndex else '?'}")
            return None
        else:
            for varBind in varBinds:
                return str(varBind[1])

    # MySQL数据库插入函数
    # 数据库插入函数
    def convert_timeticks_to_dhms(timeticks):
        # 将 TimeTicks 转换为总秒数
        seconds = int(timeticks) / 100

        # 计算天数、小时数、分钟数和秒数
        days = seconds // (24 * 3600)
        seconds = seconds % (24 * 3600)
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        return f"{int(days)}天 {int(hours)}小时 {int(minutes)}分钟 {int(seconds)}秒"

    def insert_into_mysql(connection, table, ip, name, sys_time):
        with connection.cursor() as cursor:
            # 检查该IP是否已经存在于数据库中
            cursor.execute(f"SELECT COUNT(*) FROM `{table}` WHERE `ip` = %s", (ip,))
            exists = cursor.fetchone()[0] > 0

            # 转换 TimeTicks 数据为日时分秒
            sysUpTime_dhms = DeviceTime.convert_timeticks_to_dhms(sys_time)

            if exists:
                # 如果存在，更新 name 和 sysUpTime 字段
                sql = f"UPDATE `{table}` SET `name` = %s, `sys_time`= %s WHERE `ip` = %s"
                cursor.execute(sql, (name, sysUpTime_dhms, ip))
            else:
                # 如果不存在，插入新行
                sql = f"INSERT INTO `{table}` (`ip`, `name`, `sys_time`) VALUES (%s, %s, %s)"
                cursor.execute(sql, (ip, name, sysUpTime_dhms))

        connection.commit()
    # 主逻辑
    def job(self):
        community = "public"  # SNMP community字符串
        sys_time_oid = '.1.3.6.1.2.1.1.3.0'
        name_oid = '.1.3.6.1.2.1.1.5.0' # sysName的OID



        # 建立数据库连接
        connection = pymysql.connect(host=self.smysql_host, user=self.mysql_user, password=self.mysql_password,
                                     db=self.mysql_db)

        try:
            for device_type, ips in self.ips_by_device_type.items():
                for ip in ips:
                    sys_time = DeviceTime.get_snmp_data(ip, community, sys_time_oid)
                    name = DeviceTime.get_snmp_data(ip, community, name_oid)
                    # 获取设备的sysName
                    if ip:
                        # 如果是首次运行，data_create和data_update时间相同
                        DeviceTime.insert_into_mysql(connection, self.mysql_table, ip, name,sys_time)
                        print(f"Data for device with IP {ip} updated in MySQL database successfully.")
                    else:
                        print(f"Failed to get sysName for device with IP {ip}")

        finally:
            connection.close()

        # 安排任务每五秒执行一次
