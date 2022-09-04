# cap

HTTP server tool. Just as HTTP clients tools are used to get HTTP
responses data from a web resources, this utility is used to get
HTTP requests data from some HTTP servers clients. Can be used to
analyze incoming HTTP requests data, and to simulate web applications
with static responses. Based on python uvicorn server framework.

### Requirements

Installed Python 3 interpreter. The interpreter must be accessible
from the console. Installed python pip package manager.

### Installation

`pip install -r requirements.txt`

### Usage

`cap --help` - view help page

`cap` - start servers described in default config file 'cap.yml'
with default logging level 'DEBUG', default output logging format
'[%(asctime)s: %(levelname)s] %(message)s'

`cap -c your_config_file.yml` - start servers described in
'your_config_file.yml' file and other default arguments

`cap -l ERROR` - start servers with 'ERROR' logging level
and other default arguments

`cap -f '%(asctime)s-%(levelname)s: %(message)s'` - start servers
with '%(asctime)s-%(levelname)s: %(message)s' logging format and
other default arguments

`cap -o log_file1.log log_file2.log` - start servers with additional
logging files 'log_file1.log' and 'log_file2.log' and other default
arguments (logging to console stay allowed)

### Configuration file

Configuration file is used to describe all HTTP servers
configurations. You can configure:
- HTTP server host, port, protocol (HTTP/HTTPS), base path, SSL certs
files, list of server request mappings and requests logging config
- HTTP request method, mapping, query parameters, body and response
to use for this request. These parameters will be used by servers.
If some HTTP request parameters equals to these configurations, server
will accept this request and use response described in request
parameters
- HTTP response status code, headers and body. These parameters are
used by servers to create HTTP response on some request
- general requests data logging config. This is a part of parameters
that manages viewing and saving all HTTP requests data. You can
configure logging request headers, body, how to view body (as bytes
or as text), saving body to file and others

By default used configuration file with name 'cap.yml'. Example of
configuration file content:

```yaml
servers:
  - alias: 'My custom https server'
    base_url: 'https://0.0.0.0:8443'
    requests_ids:
      - 'health'
      - 'payload'
    default_response_id: 'default'
    ssl_config:
      keyfile: /home/ssl-key.pem
      certfile: /home/ssl-cert.pem
  - base_url: 'http://0.0.0.0:8080'
    requests_ids:
      - 'health'
      - 'payload'

requests:
  health:
    method: 'GET'
    mapping: '/health'
    response_id: 'inform'
  payload:
    method: 'POST'
    mapping: '/login'
    response_id: 'payload'

responses:
  health:
    headers:
      content-type: 'application/json'
    status: 200
    body:
      data: '{"status": "server ok"}'
  payload:
    status: 400
    headers:
      content-type: 'application/json'
    body:
      file: "/home/login_failed.json"
  default:
    status: 404
    headers:
      content-type: 'application/json'
    body:
      data: '{"details": "Unknown url mapping"}'

request_log_config:
  headers_enabled: false,
  body_enabled: true
  body_as_file: true,
  body_files_folder: '/home/cap_requests_files'
  body_type: 'text'
  body_encoding: 'utf-16'
  log_file: '/home/cap_requests_files/requests.log'
```
