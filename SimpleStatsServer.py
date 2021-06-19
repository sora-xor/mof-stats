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
        if symbol == 'pswap':
            data = '{"id":1, "jsonrpc":"2.0", "method": "assets_totalSupply", "params":["0x0200050000000000000000000000000000000000000000000000000000000000"]}'
            response = requests.post(server, headers=headers, data=data)
            balance = json.loads(response.content)['result']['balance']
            
        
            tbcRewardsData = '{"id":1, "jsonrpc":"2.0", "method": "assets_freeBalance", "params":["cnTQ1kbv7PBNNQrEb1tZpmK7easBTbiFMQUUwfLf9LX66ND8u","0x0200050000000000000000000000000000000000000000000000000000000000"]}'
            tbcRewardsResponse = requests.post(server, headers=headers, data=tbcRewardsData)
            tbcRewardsBalance = json.loads(tbcRewardsResponse.content)['result']['balance']

            marketMakerData = '{"id":1, "jsonrpc":"2.0", "method": "assets_freeBalance", "params":["cnTQ1kbv7PBNNQrEb1tZpmK7fJT4Awahg1d8aoYoGGv2ATz7m","0x0200050000000000000000000000000000000000000000000000000000000000"]}'
            marketMakerResponse = requests.post(server, headers=headers, data=marketMakerData)
            marketMakerBalance = json.loads(marketMakerResponse.content)['result']['balance']

            balance = int(balance) - int(tbcRewardsBalance) - int(marketMakerBalance)
            balance = str(balance)

            balance = balance[:-18] + '.' + balance[-18:]
            self.write(balance)
        else:
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
