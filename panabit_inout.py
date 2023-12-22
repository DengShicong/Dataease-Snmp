import schedule as schedule
from pysnmp.hlapi import *
import pymysql
import time
from datetime import datetime

# 提供的IP地址
ips_by_device_type = {
    'OmniSwitch': ['10.10.10.200'],
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
        print(f"Error for host {host} and OID {oid}: {errorIndication}")
        return None
    elif errorStatus:
        print(f"SNMP Error: {errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1][0] if errorIndex else '?'}")
        return None
    else:
        for varBind in varBinds:
            # 这里直接将Counter32数据转换为字符串
            return str(varBind[1].prettyPrint())

# MySQL数据库插入函数
# 数据库插入函数
def insert_into_mysql(connection, table, ip,ifInOctets,ifOutOctets, data_create, data_update):
    with connection.cursor() as cursor:
        # 检查该IP是否已经存在于数据库中
        # ifOutOctets_kb = int(ifOutOctets) / 1024
        # ifInOctets_kb = int(ifInOctets) / 1024
        # ifInOctets_mb = int(ifInOctets_kb) / 1024
        # ifOutOctets_mb = int(ifOutOctets_kb) / 1024
        # ifInOctets_b = int(ifInOctets) / 8
        # ifOutOctets_b = int(ifOutOctets) / 8
        # ifOutOctets_kb = int(ifOutOctets_b) / 1024
        # ifInOctets_kb = int(ifInOctets_b) / 1024
        # ifInOctets_mb = int(ifInOctets_kb) / 1024
        # ifOutOctets_mb = int(ifOutOctets_kb) / 1024

        sql = f"INSERT INTO `{table}` (`ip`, `ifInOctets`,`ifOutOctets`, `data_create`, `data_update`) VALUES (%s,%s,%s, %s, %s)"
        cursor.execute(sql, (ip, ifInOctets,ifOutOctets, data_create, data_update))

    connection.commit()

# 主逻辑
def job():
    community = "public"  # SNMP community字符串
    ifInOctets_oid = '.1.3.6.1.2.1.2.2.1.10.1'
    ifOutOctets_oid = '.1.3.6.1.2.1.2.2.1.16.1'

    # 数据库信息
    mysql_host = "10.10.10.244"
    mysql_user = "root"
    mysql_password = "Password123@mysql"
    mysql_db = "ale"
    mysql_table = "panabit_inout"

    # 建立数据库连接
    connection = pymysql.connect(host=mysql_host, user=mysql_user, password=mysql_password, db=mysql_db)

    try:
        for device_type, ips in ips_by_device_type.items():
            for ip in ips:
                if ip:
                    ifInOctets = get_snmp_data(ip, community, ifInOctets_oid)
                    ifOutOctets = get_snmp_data(ip, community, ifOutOctets_oid)

                # 获取设备的sysName
                    if ip:
                        data_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # 如果是首次运行，data_create和data_update时间相同
                        insert_into_mysql(connection, mysql_table, ip, ifInOctets,ifOutOctets, data_update, data_update)
                        print(f"Data for device with IP {ip} updated in MySQL database successfully.")
                    else:
                        print(f"Failed to get sysName for device with IP {ip}")

    finally:
        connection.close()

    # 安排任务每五秒执行一次
schedule.every(10).seconds.do(job)

    # 运行调度任务
while True:
    schedule.run_pending()
    time.sleep(1)