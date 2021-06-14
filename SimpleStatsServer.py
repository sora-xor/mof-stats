import tornado.httpserver
import tornado.ioloop
import tornado.web
import requests
import json

server = "https://rpc.sora2.soramitsu.co.jp:/9933"

headers = {
    'Content-Type': 'application/json',
}

class getToken(tornado.web.RequestHandler):
    def get(self):
        self.write("hello")

class QtyHandler(tornado.web.RequestHandler):
    def get(self, symbol):
        data = '{"id":1, "jsonrpc":"2.0", "method": "assets_totalSupply", "params":["0x0200000000000000000000000000000000000000000000000000000000000000"]}'
        response = requests.post(server, headers=headers, data=data)
        balance = json.loads(response.content)['result']['balance']
        balance = balance[:-18] + '.' + balance[-18:]
        self.write(balance)

application = tornado.web.Application([
    (r'/', getToken),
    (r"/qty/([\d\w]+)", QtyHandler)
])

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application, ssl_options={
        "certfile": "fullchain.pem",
        "keyfile": "privkey.pem"
    })
    http_server.listen(443)
    tornado.ioloop.IOLoop.instance().start()
