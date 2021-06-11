import tornado.httpserver
import tornado.ioloop
import tornado.web

class getToken(tornado.web.RequestHandler):
    def get(self):
        self.write("hello")

application = tornado.web.Application([
    (r'/', getToken),
])

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application, ssl_options={
        "certfile": "fullchain.pem",
        "keyfile": "privkey.pem"
    })
    http_server.listen(443)
    tornado.ioloop.IOLoop.instance().start()
