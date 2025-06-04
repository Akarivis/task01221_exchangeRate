import pymysql
from flask import Flask,request,jsonify
import json
import uuid
from dbutils.pooled_db import PooledDB
import redis
from Rate import fetch_rate_data

app = Flask(__name__)


Pool = PooledDB(
    creator=pymysql,#使用数据库连接的模块
    maxconnections=10,#最大连接数，0和none代表无限制
    mincached=2,#初始化时，创建的最少连接，0则不创建
    maxcached=3,#最多闲置连接，0和none代表无限制
    blocking=True,#连接池无连接时是否等待或阻塞
    setsession=[],#会话开始前的命令列表
    ping=0,
    host='localhost', port=3306, user='root', passwd='123456', charset='utf8', db='rpa'
)

def mysql_one(sql,token):
    # 连接数据库
    # conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='123456', charset='utf8', db='rpa')
    conn = Pool.connection()
    cursor = conn.cursor()
    cursor.execute(sql, token)
    result_token = cursor.fetchone()
    cursor.close()
    conn.close() #使用连接池时，变成把连接交还给连接池
    return result_token


@app.route("/index",methods = ["POST"])
def index():
    """
    请求的url中要携带/index?token=
    请求的格式要求：{"status":""}
    :return:
    """
    token = request.args.get("token")
    print(token)

    if not token:
        return jsonify({"message":"认证失败","data":{"id":0,"status":"login_fail"}})

    result_token = mysql_one("select ID from task01221_users where id = %s", [token])

    if not result_token:
        return jsonify({"message": "认证失败", "data": {"id": 0, "status": "login_fail"}})


    status = request.json.get("status")
    print(f"josn得到的数据是：{status}")
    if not status:
        return jsonify({"messages":"参数错误","data":{"id": 2, "status":"fail"}})


    tid = str(uuid.uuid4())
    task_dict = {"task_id" : tid,"status":status}
    REDIS_CONN_PARAM = {
        "host" : "127.0.0.1",
        "password" : "123456",
        "port" : 6379,
        "encoding" : "utf8"
    }
    conn_redis = redis.Redis(**REDIS_CONN_PARAM)
    conn_redis.lpush("spire_task_list",json.dumps(task_dict))

    return jsonify({"status":"success","task_id":tid,"message":"正在运行中！"})


if __name__ == '__main__':
    app.run(host="127.0.0.6",port=7890)

