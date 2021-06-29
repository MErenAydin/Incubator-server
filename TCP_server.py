import socket
from threading import Thread,Condition
import select
import psycopg2
import psycopg2.extras
import redis
from redis.client import parse_client_list


class socket_server(Thread):

    def __init__(self, ip = "127.0.0.1", port = 4096 ):
        Thread.__init__(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = ip
        self.port = port
        self.condition = Condition()
        try:
            self.socket.bind((self.ip, self.port))
            print("TCP socket opened on {}:{}".format(self.ip, self.port))
        except Exception as e:
            print(str(e))
    
    def run(self):
        try:
            self.socket.listen()
            print("TCP socket started to listen")
            while True:
                client, _address = self.socket.accept()
                print("TCP socket accepted a connection on {}".format(_address))
                handler = connection_handler(client ,self.condition)
                handler.start()
        except Exception as e:
            print(str(e))
        self.socket.close()

class connection_handler(Thread):

    def __init__(self, connection, condition):
        Thread.__init__(self, args=(condition,))
        self.connection = connection
        self.timeout = 5
        self.node_key = ""
        self.safe_start = True
        self.db_conn = psycopg2.connect(database="incubator", user='postgres', password='"|sJ7\\Be\\#f^#O1iy\'Po', host='127.0.0.1', port= '5432')
        self.users = object()
        self.node_id = 0
        self.node_name = "" 
        self.redis = redis.Redis(host='localhost', port=6379, db=0, password='zHRyp2n34Rgv6VTFgkrj')
        self.condition = condition

    def run(self):
        self.setup()
        redis_node = "Node-{}".format(self.node_id)
        redis_key = "Node-{}-settings".format(self.node_id)
        try:
            while True:
                if not self.safe_start:
                    break
                is_data_ready = select.select([self.connection], [], [], self.timeout)[0]
                if is_data_ready:
                    data = self.connection.recv(8)
                    if data != b'':
                        print("Data Received: {}".format(data))
                        self.redis.mset({redis_node: data})
                    else:
                        self.safe_start = False
                else:
                    #Timeout reached: Do stuff in here (send email etc.)
                    break
                
                if self.redis.exists(redis_key) > 0:
                    settings = self.redis.get(redis_key)
                    self.redis.delete(redis_key)
                    self.connection.send(settings)


        except Exception as e:
            print(e)
            self.connection.close()
            if self.redis.exists(redis_key) > 0:
                self.redis.delete(redis_key)
            if self.redis.exists(redis_node) > 0:
                self.redis.delete(redis_node)
            
        
        self.connection.close()
        if self.redis.exists(redis_key) > 0:
            self.redis.delete(redis_key)
        if self.redis.exists(redis_node) > 0:
            self.redis.delete(redis_node)

    def setup(self):
        cursor = self.db_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            is_data_ready = select.select([self.connection], [], [], self.timeout)[0]
            if is_data_ready:
                self.node_key = self.connection.recv(64).decode('utf-8')
                print("Node Key: {}".format(self.node_key))
                sql = """
                SELECT u.user_id, n.node_id, n.node_name FROM users u
                INNER JOIN usernode un ON u.user_id = un.user_id
                INNER JOIN nodes n ON n.node_id = un.node_id
                WHERE n.node_key = '{}'
                """.format(self.node_key)
                cursor.execute(sql)
                users = cursor.fetchall()
                if users is not None and len(users) > 0:
                    self.node_id = users[0]['node_id']
                    self.node_name = users[0]['node_name']
            else:
                self.safe_start = False
                self.db_conn.close()
                self.connection.close()
            cursor.close()
            
        except Exception as e:
            print(e)
            cursor.close()
            self.safe_start = False
