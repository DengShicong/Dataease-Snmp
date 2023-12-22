import schedule as schedule
from pysnmp.hlapi import *
import pymysql
import time
from datetime import datetime


class TEMP:

    def __init__(self):
        self.mysql_host = "10.10.10.244"
        self.mysql_user = "yourUserName"
        self.mysql_password = "yourPassword"
        self.mysql_db = "yourDbName"
        self.mysql_table = "temperatrue"

    # 提供的IP地址
    ips_by_device_type = {
        'OmniSwitch': ['10.10.10.68', '10.10.10.226', '10.10.10.227'],
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
    def insert_into_mysql(connection, table, ip, name,temperatrue, data_create, data_update):
        with connection.cursor() as cursor:
            # 检查该IP是否已经存在于数据库中
            cursor.execute(f"SELECT COUNT(*) FROM `{table}` WHERE `ip` = %s", (ip,))
            exists = cursor.fetchone()[0] > 0

            if exists:
                # 如果存在，更新name和data_update字段
                sql = f"UPDATE `{table}` SET  `temperatrue`= %s, `data_update` = %s WHERE `ip` = %s"
                cursor.execute(sql, ( temperatrue,data_update,ip))
            else:
                # 如果不存在，插入新行
                sql = f"INSERT INTO `{table}` (`ip`, `name`, `temperatrue`,`data_create`, `data_update`) VALUES (%s,%s,%s,%s,%s)"
                cursor.execute(sql, (ip,name,temperatrue,data_create, data_update))

        connection.commit()

    # 主逻辑
    def job(self):
        community = "public"  # SNMP community字符串
        temperatrue1 = '.1.3.6.1.4.1.6486.803.1.1.1.1.1.2.1.1.65'
        temperatrue2 = '.1.3.6.1.4.1.6486.801.1.1.1.1.1.2.1.1.65'
        name_oid = '.1.3.6.1.2.1.1.5.0'
        # 数据库信息


        # 建立数据库连接
        connection = pymysql.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_password, db=self.mysql_db)

        try:
            for device_type, ips in self.ips_by_device_type.items():
                for ip in ips:
                    if ip == '10.10.10.68':
                        temperatrue = TEMP.get_snmp_data(ip, community, temperatrue2)
                    else:
                        temperatrue = TEMP.get_snmp_data(ip, community, temperatrue1)

                    if ip:
                        name = TEMP.get_snmp_data(ip, community, name_oid)
                        data_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        # 如果是首次运行，data_create和data_update时间相同
                        TEMP.insert_into_mysql(connection, self.mysql_table, ip, name, temperatrue, data_update, data_update)
                        print(f"Data for device with IP {ip} updated in MySQL database successfully.")
                    else:
                        print(f"Failed to get sysName for device with IP {ip}")

        finally:
            connection.close()


