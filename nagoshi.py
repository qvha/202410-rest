#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler

import os
import sys
import ssl
import json
import argparse
import subprocess

verbose=False

###################################################################################################
#
#  0. Various utilities
#
###################################################################################################
def write2tty(verbose, message):
  if verbose: 
    print(message)


def getJSONfrom(command):
  """command is a command line, that should spit out a json on stdout upon invocation"""
  write2tty(verbose, "getJSONfrom "+command )
  try:
    p=subprocess.Popen( [command], 
                        stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
                        universal_newlines=True, shell=True )
    p.wait()
  except subprocess.CalledProcessError as e:
    sys.stderr.write( e.msg+"\n"+e.output  +"\n")
    return {} 
  except OSError as e:
    sys.stderr.write(e.strerror+" with "+e.filename+"\n")
    return {}
    
  try:
    payload=json.loads(p.stdout.read()) 
  except json.decoder.JSONDecodeError as e:
    sys.stderr.write( e.msg+" line:column {}:{}\n".format(e.lineno,e.colno) )
    return {}

  return payload


###################################################################################################
#
#  1. the webserver, to receive commands from tcs+
#
###################################################################################################
class MultiThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  pass

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global verbose
        write2tty(verbose, self.path)
        try:
            # a default page is served, whatever page is actually requested
            if self.path.endswith(".html"):
              self.send_response(200)
              self.send_header('Content-type',    'text/html')
              self.end_headers()
              with open("sample.html",'r') as f:
                self.wfile.write(f.read().encode("utf-8"))
              return

            elif self.path=="/api/v1/getAllStatus":
              payload=getJSONfrom("./getAllStatus.sh")        
              serialized=json.dumps(payload, ensure_ascii=False).encode("utf-8")
              # send back the payload a json in the BODY of the HTTP response
              self.send_response(200)
              self.send_header('Content-type',    'application/json')
              self.end_headers()
              self.wfile.write ( serialized )
              write2tty(verbose, serialized )
              return

            elif self.path=="/api/v1/healthcheck" or self.path=="/api/v1/healtcheck":
              payload=getJSONfrom("./getHealthCheck.sh")        
              serialized=json.dumps(payload, ensure_ascii=False).encode("utf-8")
              # send back the payload a json in the BODY of the HTTP response
              self.send_response(200)
              self.send_header('Content-type',    'application/json')
              self.end_headers()
              self.wfile.write ( serialized )
              write2tty(verbose, serialized )
              return

            else:   #fall back
                self.send_error(404,"Don't know what to do with " + self.path)
                return

        except IOError:
            self.send_error(404,'IO error while processing ' + self.path)



###################################################################################################
#
#  2. Everybody deserves an init
#
###################################################################################################
def init():
  parser = argparse.ArgumentParser(description="command line relay in http",
           epilog="(c) 2024 HA Quoc Viet" )
  parser.add_argument("--verbose",  "-v", action="store_true", default=False)
  parser.add_argument("--no-ssl",   "-n", action="store_true", default=False,
           help="deactivate the SSL certificate exchange, do pure HTTP transaction. Defaults do use SSL")
  parser.add_argument("--httpport", "-p", action="store", default=8080, type=int,
           help="Optional port. Only valid if --no-ssl is specified. Uses 443 with SSL otherwise. "
                "Defaults to 8080")
  parser.add_argument("--interface","-i", action="store", default="0.0.0.0",
           help="IP of local interface to bind to, to serve requests. Defaults to 0.0.0.0 (all)" )
  
  # some sanity checks
  if not os.path.exists("./cert.pem") or \
     not os.path.exists("./key.pem"):
     sys.stderr.write("SSL certification files (key.pem, cert.pem), signed from a legitimate third-party "
           "authority, are required.")
     sys.exit(1)

  args = parser.parse_args()

  # positionning code-wide constants
  global verbose ; verbose=args.verbose

  # some sanity checks
  if not os.path.exists("./getHealthCheck.sh"):
    sys.stderr.write("Could not find getHealthCheck.sh in the current folder, exiting.\n")
    sys.exit(1)
  if not os.path.exists("./getAllStatus.sh"):
    sys.stderr.write("Could not find getAllStatus.sh in the current folder, exiting.\n")
    sys.exit(1)

  return args


###################################################################################################
#
#  3. Main routine. the http server
#
###################################################################################################
def serve_http(args):
  print('Starting command server http port {port} ...'.format(port=args.httpport) )
  server = MultiThreadedHTTPServer((args.interface, args.httpport), MyHandler)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    sys.stderr.write("^C received, shutting down command server.\n")
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
  print('Starting command server on https port 443 ...' )
  SSLserver = MultiThreadedHTTPServer((args.interface, 443), MyHandler)
  ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  ssl_context.load_cert_chain("./cert.pem", "./key.pem")
  SSLserver.socket = ssl_context.wrap_socket( SSLserver.socket, server_side=True)
  try:
    SSLserver.serve_forever()
  except KeyboardInterrupt:
    sys.stderr.write("^C received, shutting down command server.\n")
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
