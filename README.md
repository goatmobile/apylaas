# Any Python Library As A Service (`apylaas`)

`apylaas` lets you host Python libraries behind a web service with a JSON API and a simple web UI. This can be useful for remotely executing Python code with some inputs or debugging code outside of a terminal. Read [this post](https://goatmobile.github.io/blog/posts/apylaas/) for details.

## Installation

```bash
pip install apylaas
```

## Usage

```bash
apylaas --help

apylaas --library some_module
```

### Details

```bash
cat <<EOF > something.py
def say_hello(name: str) -> str:
    return f"Hello {name}!"
EOF

apylaas --library something

# Visit http://localhost:5000/say_hello
# or use the API directly (both GET and POST are accepted)
curl -X POST -d '{"name": "someone"}' http://localhost:5000/say_hello
curl 'http://localhost:5000/say_hello?name=someone'
```

See [`examples/basic.py`](examples/basic.py) for a simple demo of hosting a function that takes in and returns strings. See [`examples/classifier.py`](examples/classifier.py) for a simple PyTorch model server.
