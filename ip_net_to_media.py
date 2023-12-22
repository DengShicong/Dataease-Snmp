import schedule as schedule
from pysnmp.hlapi import *
import pymysql
import time
from datetime import datetime
import chardet

class AP:

    def __init__(self):
        self.mysql_host = "10.10.10.244"
        self.mysql_user = "root"
        self.mysql_password = "Password123@mysql"
        self.mysql_db = "ale"
        self.mysql_table = "ip_net_to_media"
    # 提供的IP地址
    ips_by_device_type = {
        'AP': ['10.10.10.181', '10.10.10.241', '10.10.10.152'],
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
                # 尝试手动转换IpAddress到字符串
                try:
                    # 将varBind[1]视为包含四个字节的IpAddress对象
                    ip_address = '.'.join(str(x) for x in varBind[1].asOctets())
                    return ip_address
                except AttributeError:
                    # 如果asOctets不存在，打印变量绑定并返回None
                    print(f"Unexpected data type for varBind: {varBind}")
                    return None
        # MySQL数据库插入函数
    # 数据库插入函数
    def insert_into_mysql(connection, table, ip, data_create, data_update):
        with connection.cursor() as cursor:
            # 检查该IP是否已经存在于数据库中
            cursor.execute(f"SELECT COUNT(*) FROM `{table}` WHERE `ip` = %s", (ip,))
            exists = cursor.fetchone()[0] > 0

            if exists:
                # 如果存在，更新name和data_update字段
                sql = f"UPDATE `{table}` SET  `data_update` = %s WHERE `ip` = %s"
                cursor.execute(sql, (data_update, ip))
            else:
                # 如果不存在，插入新行
                sql = f"INSERT INTO `{table}` (`ip`, `data_create`, `data_update`) VALUES (%s, %s, %s)"
                cursor.execute(sql, (ip,data_create, data_update))

        connection.commit()

    # 主逻辑
    def job(self):
        community = "public"  # SNMP community字符串
        atNetAddress_oid = '.1.3.6.1.2.1.3.1.1.3.17.1.'  # sysName的OID

        # 数据库信息


        # 建立数据库连接
        connection = pymysql.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_password, db=self.mysql_db)

        try:
            for device_type, ips in self.ips_by_device_type.items():
                for ip in ips:
                    for i in range(0, 255):  # 从0到254
                        oid = f"{atNetAddress_oid}10.10.10.{i}"  # 构建完整的OID
                        ip_name = AP.get_snmp_data(ip, community, oid)
                        if ip_name:
                            data_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            AP.insert_into_mysql(connection, self.mysql_table, ip_name, data_update, data_update)
                            print(f"Data for device with IP {ip_name} updated in MySQL database successfully.")
                        else:
                            print(f"Failed to get data for OID {oid}")

        finally:
            connection.close()

