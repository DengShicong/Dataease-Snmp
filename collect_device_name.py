
from pysnmp.hlapi import *
import pymysql

from datetime import datetime

class CollectDeviceName:


    def __init__(self):
        self.mysql_host = "db ip address"
        self.mysql_user = "root"
        self.mysql_password = "your passwd"
        self.mysql_db = "yourDatabaseName"
        self.mysql_table = "assets_asset"
        self.community = "public"  # SNMP community字符串

    ips_by_device_type = {
        'OmniSwitch': ['10.10.10.68', '10.10.10.226', '10.10.10.227','10.10.10.181','10.10.10.152','10.10.10.241'],
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

    # MySQL数据库插入函数
    # 数据库插入函数
    def insert_into_mysql(connection, table, ip, name, data_create, data_update):
        with connection.cursor() as cursor:
            # 检查该IP是否已经存在于数据库中
            cursor.execute(f"SELECT COUNT(*) FROM `{table}` WHERE `ip` = %s", (ip,))
            exists = cursor.fetchone()[0] > 0

            if exists:
                # 如果存在，更新name和data_update字段
                sql = f"UPDATE `{table}` SET `name` = %s, `data_update` = %s WHERE `ip` = %s"
                cursor.execute(sql, (name, data_update, ip))
            else:
                # 如果不存在，插入新行
                sql = f"INSERT INTO `{table}` (`ip`, `name`, `data_create`, `data_update`) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (ip, name, data_create, data_update))

        connection.commit()

    # 主逻辑
    def job(self):

        # 建立数据库连接

            connection = pymysql.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_password,
                                         db=self.mysql_db)
            try:
                for device_type, ips in self.ips_by_device_type.items():
                    for ip in ips:
                        name = CollectDeviceName.get_snmp_data(ip, self.community, '.1.3.6.1.2.1.1.5.0')
                        if name:
                            data_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            # 使用类名调用静态方法
                            CollectDeviceName.insert_into_mysql(connection, self.mysql_table, ip, name, data_update,data_update)

                            print(f"Data for device with IP {ip} updated in MySQL database successfully.")
                        else:
                            print(f"Failed to get sysName for device with IP {ip}")

            finally:
                connection.close()


