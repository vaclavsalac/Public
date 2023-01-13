## Create & Run Docker container with simple Python web server

### Prerequisites

1. Install [Docker](https://www.docker.com).

2. Create folder, where you put all files we are going to create.


### Necessary files

1. Create index page (index.html):
  ```
  <!DOCTYPE html>
  <html>
    <body>
      Hello World
    </body>
  </html>
  ```
  
2. Create simple python web server (server.py):
  ```
  #!/usr/bin/python3
  from http.server import BaseHTTPRequestHandler, HTTPServer
  import time
  import json
  from socketserver import ThreadingMixIn
  import threading
  
  hostName = "0.0.0.0"
  serverPort = 80
  
  class Handler(BaseHTTPRequestHandler):
      def do_GET(self):
          # curl http://<ServerIP>/index.html
          if self.path == "/":
              # Respond with the file contents.
              self.send_response(200)
              self.send_header("Content-type", "text/html")
              self.end_headers()
              content = open('index.html', 'rb').read()
              self.wfile.write(content)
          else:
              self.send_response(404)
          return
          
  class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
      """Handle requests in a separate thread."""
      
  if __name__ == "__main__":
      print("Server started.")
      webServer = ThreadedHTTPServer((hostName, serverPort), Handler)
      
      try:
          webServer.serve_forever()
          
      except KeyboardInterrupt:
          pass
          
      webServer.server_close()
      print("Server stopped.")
  ```

3. Create dockerfile (dockerfile):
  ```
  FROM python:3
  ADD index.html index.html
  ADD server.py server.py
  EXPOSE 8000
  ENTRYPOINT ["python3", "server.py"]
  ```
 
### Docker part
 
1. In the terminal, navigate to the folder you created.

2. Run: ``docker build -f dockerfile . -t python_web_server``
 
3. Run: ``docker run --rm -p 8000:80 --name python_web_server python_web_server``
