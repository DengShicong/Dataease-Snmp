import schedule as schedule
from pysnmp.hlapi import *
import pymysql
import time
from datetime import datetime

# 提供的IP地址


class Connection:
# SNMP数据收集函数

    def __init__(self):
        self.smysql_host = "10.10.10.244"
        self.mysql_user = "yourUsername"
        self.mysql_password = "yourDbPassword"
        self.mysql_db = "yourDbName"
        self.mysql_table = "connect"

    ips_by_device_type = {
        'OmniSwitch': ['10.10.10.200'],
    }

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
    def insert_into_mysql(connection, table, ip, connect_num,user_num, pps):
        with connection.cursor() as cursor:
            # 检查该IP是否已经存在于数据库中
            cursor.execute(f"SELECT COUNT(*) FROM `{table}` WHERE `ip` = %s", (ip,))
            exists = cursor.fetchone()[0] > 0

            if exists:
                # 如果存在，更新name和data_update字段
                sql = f"UPDATE `{table}` SET  `connect_num`= %s, `user_num` = %s, `pps` = %s WHERE `ip` = %s"
                cursor.execute(sql, ( connect_num,user_num,pps,ip))
            else:
                # 如果不存在，插入新行
                sql = f"INSERT INTO `{table}` (`ip`, `connect_num`, `user_num`,`pps`) VALUES (%s,%s,%s,%s)"
                cursor.execute(sql, (ip,connect_num,user_num,pps))

        connection.commit()

    # 主逻辑
    def job(self):
        community = "public"  # SNMP community字符串
        connect_num_oid = '.1.3.6.1.4.1.58819.5.2.4'
        user_num_oid = '.1.3.6.1.4.1.58819.3.2.2'
        pps_oid = '.1.3.6.1.4.1.58819.4.2.2'
        # 数据库信息


        # 建立数据库连接
        connection = pymysql.connect(host=self.smysql_host, user=self.mysql_user, password=self.mysql_password,
                                     db=self.mysql_db)

        try:
            for device_type, ips in self.ips_by_device_type.items():
                for ip in ips:
                    if ip:
                        connect_num = Connection.get_snmp_data(ip, community, connect_num_oid)
                        user_num = Connection.get_snmp_data(ip, community, user_num_oid)
                        pps = Connection.get_snmp_data(ip, community, pps_oid)
                        # 如果是首次运行，data_create和data_update时间相同
                        Connection.insert_into_mysql(connection, self.mysql_table, ip, connect_num, user_num, pps)
                        print(f"Data for device with IP {ip} updated in MySQL database successfully.")
                    else:
                        print(f"Failed to get sysName for device with IP {ip}")

        finally:
            connection.close()


