from pysnmp.hlapi import *
import pymysql
import schedule
import time
from datetime import datetime

class EsrHealth:

    def __init__(self):
        self.mysql_host = "10.10.10.244"
        self.mysql_user = "yourUserName"
        self.mysql_password = "yourPassword"
        self.mysql_db = "yourDbName"
        self.mysql_table = "esr_health"

    ips_by_device_type = {
        'ESR': ['10.10.10.56']
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


    # 数据库插入和更新函数
    oids_info = {
        'cpu_usage': '.1.3.6.1.4.1.15227.1.3.1.1.1.0',
        'mem_usage': '.1.3.6.1.4.1.15227.1.3.1.1.2.0',
        'session_num': '.1.3.6.1.4.1.15227.1.3.1.1.3.0',
        'forward_rate': '.1.3.6.1.4.1.15227.1.3.1.1.5.0',
        'mem_total': '.1.3.6.1.4.1.15227.1.3.1.1.6.0',
        'mem_free': '.1.3.6.1.4.1.15227.1.3.1.1.7.0',
        'power_state': '.1.3.6.1.4.1.15227.1.3.1.1.8.0',
        'cpu_temperature': '.1.3.6.1.4.1.15227.1.3.1.1.11.0'
    }


    # 更新数据库表的函数
    def update_database_table(connection, table, ip, data):
        with connection.cursor() as cursor:
            # 构建更新的字段和值
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            values = list(data.values())

            # 更新数据或插入新数据
            sql = f"""INSERT INTO `{table}` (`ip`, {columns})
                      VALUES (%s, {placeholders})
                      ON DUPLICATE KEY UPDATE {', '.join(f'{col} = VALUES({col})' for col in data.keys())}"""

            cursor.execute(sql, [ip] + values)
        connection.commit()


    # 收集SNMP数据并更新数据库的任务
    def collect_data_and_update_db(self):
        # 数据库信息

        community = "public"
        # 建立数据库连接
        connection = pymysql.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_password, db=self.mysql_db)

        try:
            for device_type, ips in self.ips_by_device_type.items():
                for ip in ips:
                    # 对于每个IP，收集所有OIDs的数据
                    data = {}
                    for column, oid in self.oids_info.items():
                        data[column] = EsrHealth.get_snmp_data(ip, community, oid)

                    # 过滤掉任何None值，这些是未能成功获取的数据
                    data = {k: v for k, v in data.items() if v is not None}

                    # 如果有数据则更新数据库
                    if data:
                        EsrHealth.update_database_table(connection, self.mysql_table, ip, data)
                        print(f"Updated database for IP {ip} with data: {data}")
                    else:
                        print(f"No data collected for IP {ip}")

        finally:
            connection.close()

