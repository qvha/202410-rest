#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler

import os
import sys
import ssl
import json
import time
import random
import select
import argparse


class MultiThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  def __init__(self,A, B, ack):
    self.ack=ack
    super(MultiThreadedHTTPServer,self).__init__(A, B)

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(self.path)
        try:
            if self.path.endswith("sample.html"):
                f = open("sample.html",'r')
                self.send_response(200)
                self.send_header('Content-type',    'text/html')
                self.end_headers()
                self.wfile.write(f.read().encode('utf-8'))
                f.close()

            else:   #fall back
                self.send_error(404,"Don't know what to do with " + self.path)
                print("unknown request")

        except IOError:
            self.send_error(404,"IO error while processing " + self.path)
            print("IO error")


    def do_POST(self):
        print("Processing "+ self.path)
        try:
            if self.path.endswith("api/v1/cctv/events/active"):
                self.send_response(200)
                self.send_header('Content-type',    'text/html')
                self.end_headers()

                if self.server.ack:
                  message="ACK"
                else:
                  token=random.randint(0,5)
                  if token==0:
                    message="ACK"
                  elif token==1:
                    message="NACK"
                  else:
                    time.sleep(16)
                    message="ACK"
                self.wfile.write(message.encode('utf-8'))
                # retrieve the json
                length=int( self.headers.get('content-length') )
                payload=json.loads( self.rfile.read(length) )
                print(payload)

            else:   #fall back
                self.send_error(404,"Don't know what to do with " + self.path)
                print("received request on " + self.path )
                length=int( self.headers.get('content-length') )
                payload=json.loads( self.rfile.read(length) )
                print(payload)
                self.send_response(200)
                self.send_header('Content-type',    'text/html')
                self.end_headers()

        except IOError:
            self.send_error(404,"IO error while processing " + self.path)
            print("IO error")
       

#############
def getSSLcontext(certfile, keyfile):
  context=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
  context.load_cert_chain(certfile, keyfile)
  context.set_ciphers( "ECDH+AES:DHE+AES:!eNULL:!SHA1:!aDSS" )
  return context


def write2tty(verbose, message):
  if verbose: print(message)


###################################################################################################
#
#  2. Everybody deserves an init
#
###################################################################################################
def init():
  parser = argparse.ArgumentParser(description="json receiver",
           epilog="(c) 2024 HA Quoc Viet" )
  parser.add_argument("--verbose",  "-v", action="store_true", default=False,
           help="currently unused")
  parser.add_argument("--no-ssl",   "-s", action="store_true", default=False)
  parser.add_argument("--ack",      "-a", action="store_true", default=False,
           help="always reply ACK, with no random wait")
  parser.add_argument("--httpport", "-p", action="store", default=8080, type=int)
  parser.add_argument("--interface","-i", action="store", default="0.0.0.0",
           help="IP of local interface to bind to, to serve requests. Defaults to 0.0.0.0 (all)" )

  args = parser.parse_args()

  if not args.no_ssl:   # if SSL is required
    # check for certificate files
    if not os.path.exists("./cert.pem") or not os.path.exists("./key.pem"):
      sys.stderr.write( "Could not find ./cert.pem or ./key.pem. They could be generated with "
               "openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem\n")
      sys.exit(1)

  return args


###################################################################################################
#
#  3. Main routine. the http server
#
###################################################################################################
def serve_http(args):
  print('Listening on port {port} ...'.format(port=args.httpport) )
  server = MultiThreadedHTTPServer((args.interface, args.httpport), MyHandler, args.ack)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    sys.stderr.write("^C received, shutting down.\n")
    server.socket.close()
  except:
    sys.stderr.write("Could not start serving. Check root access. "
                     "Check occupied ports with netstat -an.\n" ) 



###################################################################################################
#
#  3bis. alternative main routine. the https server
#
###################################################################################################
def serve_https(args):
  print('Starting JSON receiver on port 443 ...' )
  SSLserver = MultiThreadedHTTPServer((args.interface, 443), MyHandler, args.ack)
  ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  ssl_context.load_cert_chain("./cert.pem", "./key.pem")
  SSLserver.socket = ssl_context.wrap_socket( SSLserver.socket, server_side=True)
  try:
    SSLserver.serve_forever()
  except KeyboardInterrupt:
    sys.stderr.write("^C received, shutting down.\n")
    SSLserver.socket.close()
  except:
    sys.stderr.write("Could not start serving. Check root access. "
                     "Check occupied ports with netstat -an.\n" ) 


if __name__ == '__main__':
  args=init()
  if args.no_ssl:
    serve_http(args)
  else:
    serve_https(args)
