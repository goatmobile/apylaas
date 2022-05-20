import argparse
import importlib
import inspect
import io
import json
import logging
import os
import subprocess
import sys
import textwrap
import time
import traceback

from dataclasses import dataclass
from typing import *
from types import *

import flask
import werkzeug
import waitress
from flask import request, render_template, Flask
from flask.views import View
from jinja2 import StrictUndefined
from pathlib import Path

from apylaas.transformers import default_input_to_python, default_type_to_html

PROJECT_ROOT = Path(__file__).resolve().parent
IS_EDITABLE_INSTALL = (PROJECT_ROOT / "local_install").exists()


@dataclass
class CallableItem:
    arg_types: Dict[str, Tuple[str, type]]
    fn: Callable
    return_type: str


@dataclass
class UncallableItem:
    fn: Callable
    reason: str


DEBUG = os.getenv("DEBUG", "off").lower() in {"1", "on", "yes", "true"}


def is_callable(value):
    return isinstance(value, CallableItem)


def type_name(type) -> str:
    if hasattr(type, "__name__"):
        return type.__name__

    return str(type).lstrip("typing.")


def to_signature(item: CallableItem) -> str:
    args = []
    for arg_name, (arg_type, _, inferred, name) in item.arg_types.items():
        if inferred:
            args.append(f"{arg_name}")
        else:
            args.append(f"{arg_name}: {type_name(arg_type)}")

    ret = f" -> {type_name(item.return_type)}"
    if item.return_type is inspect._empty:
        ret = ""

    if hasattr(item.fn, "__name__"):
        name = item.fn.__name__
    else:
        name = str(item.fn)
    return f"{name}({', '.join(args)}){ret}"


def user_error(msg, exc):
    return flask.Response(
        response=json.dumps(
            {
                "message": msg,
                "exception": str(exc),
            }
        ),
        status=400,
    )


TransformerFn = Callable[[int, int], int]
TypeTransformer = Tuple[Any, Callable[[int, int], int]]


class DictWithFallbacks:
    def __init__(self, dictionary=None, fallbacks=None):
        super().__init__()
        if fallbacks is None:
            fallbacks = []
        self.fallbacks = fallbacks

        if dictionary is None:
            dictionary = {}
        self.dictionary = dictionary

    def get(self, key):
        if key in self.dictionary:
            return self.dictionary[key]

        for fallback in self.fallbacks:
            result = fallback(key)
            if result is not None:
                return result

        return None

    def __str__(self):
        keys = ", ".join([str(x) for x in self.dictionary.keys()])
        fns = ", ".join([str(x) for x in self.fallbacks])
        return f"options(keys={keys}, fns={fns})"


def init_logger(name: Optional[str] = None, time: bool = True) -> logging.Logger:
    """
    Create a logger instance for the current module
    """
    if name is None:
        name = __name__

    logger = logging.getLogger(name)

    # Log all messages
    logger.setLevel(logging.INFO)

    # Set up a handler to print to stderr
    handler = logging.StreamHandler()
    parts = []
    if time:
        parts.append("%(asctime)s")
    parts.append("%(levelname)-1s")

    formatter = logging.Formatter(
        fmt=f"[{' '.join(parts)}] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.handlers[0].flush = sys.stderr.flush
    return logger


class App:
    app: flask.Flask
    input_to_python: DictWithFallbacks
    type_to_html: DictWithFallbacks

    def __init__(
        self,
        module: Union[str, ModuleType],
        ignore_hidden: bool = True,
        input_to_python: Optional[List[Union[TransformerFn, TypeTransformer]]] = None,
        type_to_html: Optional[List[Union[TransformerFn, TypeTransformer]]] = None,
        logger: logging.Logger = None,
    ):
        self.input_to_python = DictWithFallbacks()
        self.type_to_html = DictWithFallbacks()

        if logger is None:
            self.log = init_logger()
        else:
            self.log = logger

        def _add_resolver(list, target):
            if list is not None:
                for item in list:
                    if isinstance(item, tuple):
                        target.dictionary[item[0]] = item[1]
                    elif callable(item):
                        target.fallbacks.append(item)
                    else:
                        raise RuntimeError(
                            f"Object {item} was not a 2 element tuple or a callable"
                        )

        _add_resolver(default_input_to_python(), self.input_to_python)
        _add_resolver(input_to_python, self.input_to_python)
        _add_resolver(default_type_to_html(), self.type_to_html)
        _add_resolver(type_to_html, self.type_to_html)

        self.module = module
        self.ignore_hidden = ignore_hidden
        module, methods, error = self.search_module()
        self.app = self.make_app(module, methods, error)

    def get_method_item(self, signature, fn):
        arg_types = {}
        errors = []
        for name, param in signature.parameters.items():
            input_html = self.type_to_html.get(param.annotation)
            if param.annotation is inspect._empty:
                annotation = str
                inferred = True
                if input_html is None:
                    input_html = "text"
            elif input_html is None:
                annotation = None
                inferred = None
                errors.append(param.annotation)
            else:
                annotation = param.annotation
                inferred = False

            arg_types[name] = (annotation, input_html, inferred, type_name(annotation))

        if len(errors) > 0:
            return UncallableItem(
                fn=fn,
                reason=f"Missing transformer for param types: {', '.join([str(x) for x in errors])}",
            )

        return CallableItem(
            arg_types=arg_types, return_type=signature.return_annotation, fn=fn
        )

    def search_module(
        self,
    ) -> Tuple[ModuleType, Dict[str, CallableItem], Optional[Exception]]:
        module = self.module
        if isinstance(module, str):
            name = module
            print(f"Searching module {name}")
            should_patch_sys_path = name.endswith(".py")
            if should_patch_sys_path:
                module_path = Path(name).resolve()
                sys.path.append(str(module_path.parent))
                name = module_path.stem
            try:
                module = importlib.import_module(name)
                module = importlib.reload(module)
            except ImportError as e:
                logging.error(e)
                return (None, {}, e)

            if should_patch_sys_path:
                sys.path.remove(str(module_path.parent))
        else:
            name = module.__name__

        # Hack to get around the fact that modules don't unload delete attributes
        # https://docs.python.org/3/library/importlib.html#importlib.reload
        code = [f"import {name}", "import json", f"print(json.dumps(dir({name})))"]
        output = subprocess.check_output(
            [
                sys.executable,
                "-c",
                "; ".join(code),
            ],
            encoding="utf-8",
        )
        module_dir = json.loads(output)

        if self.ignore_hidden:
            module_dir = [x for x in module_dir if not x.startswith("_")]

        result = {}
        for item_name in module_dir:
            value = getattr(module, item_name)
            if not callable(value):
                continue
            if getattr(value, "__module__", None) != module.__name__:
                continue

            try:
                signature = inspect.signature(value)
            except ValueError as e:
                print("Failed on", item_name, e)
                result[item_name] = UncallableItem(fn=value, reason=str(e))
                continue

            result[item_name] = self.get_method_item(signature, value)

        return module, result, None

    def serve(
        self,
        host: str = "0.0.0.0",
        port: int = 5000,
        reload: bool = True,
        _flask_debug: bool = False,
    ) -> NoReturn:
        if _flask_debug:
            print("Running flask development server")
            self.app.run(host=host, port=port, debug=True)
        else:
            print(f"Serving at {host}:{port}")
            wsgi_app = self.wsgi_app(
                reload=reload,
            )

            if reload:
                print(f"Reloading module {self.module} on each request")

            waitress.serve(wsgi_app, host=host, port=port)

    def make_app(
        self,
        module: ModuleType,
        methods: Dict[str, CallableItem],
        error: Optional[Exception],
    ) -> Flask:
        app = Flask(__name__)
        app.jinja_env.undefined = StrictUndefined
        app.jinja_env.filters.update(
            {"is_callable": is_callable, "to_signature": to_signature}
        )

        self.log.info(f"Making app for functions: {', '.join(methods.keys())}")

        def index():
            if module is None:
                return render_template(
                    "bad_module.html",
                    title="Error importing module",
                    error=error,
                    is_editable=IS_EDITABLE_INSTALL,
                )

            return render_template(
                "index.html",
                title=f"index of {module.__name__}",
                module=module,
                methods=methods,
                is_editable=IS_EDITABLE_INSTALL,
                any_uncallable=any(isinstance(m, UncallableItem) for m in methods),
            )

        app.route("/")(index)
        app.route("/index")(index)

        this = self

        class ApiView(View):
            methods = ["GET", "POST"]

            def dispatch_request(self, name):
                item = methods[name]
                if request.method == "GET":
                    raw_data = request.args
                else:
                    # need to pull out data from both form and files
                    raw_data = dict(request.form)
                    # need to add bytes for files
                    for k, v in request.files.items():
                        raw_data[k] = v

                data = {}
                for arg_name, (arg_type, _, inferred, name) in item.arg_types.items():
                    if arg_name in raw_data:
                        transformer = this.input_to_python.get(arg_type)
                        try:
                            data[arg_name] = transformer(raw_data[arg_name])
                        except Exception as e:
                            traceback.print_exc()
                            return user_error(
                                msg="Error transforming user data to Python format",
                                exc=e,
                            )

                error = None
                start_time = time.time_ns()
                try:
                    return_value = item.fn(**data)
                except Exception as e:
                    traceback.print_exc()
                    error = e
                end_time = time.time_ns()
                if error is not None:
                    response = user_error(msg="Error during user function", exc=error)
                else:
                    response = flask.Response(str(return_value))
                response.headers["X-Execution-Time-Ms"] = json.dumps(
                    (end_time - start_time) / 1000 / 1000
                )
                return response

        app.add_url_rule("/api/<name>", view_func=ApiView.as_view("api_view"))

        class UIView(View):
            methods = ["GET"]

            def dispatch_request(self, name):

                item = methods.get(name)
                if item is None:
                    return (
                        render_template(
                            "method-404.html",
                            title=name,
                            fn_name=name,
                            is_editable=IS_EDITABLE_INSTALL,
                        ),
                        404,
                    )

                help = (
                    textwrap.dedent(item.fn.__doc__.rstrip())
                    if item.fn.__doc__ is not None
                    else None
                )
                return render_template(
                    "form.html",
                    module=module,
                    title=name,
                    fn_name=name,
                    args=item.arg_types,
                    help=help,
                    is_editable=IS_EDITABLE_INSTALL,
                )

        app.add_url_rule("/<name>", view_func=UIView.as_view("ui_view"))

        return app

    def wsgi_app(self, reload: bool = True):
        _app = self.app

        if reload:

            def _wsgi_app(env, start_response):
                nonlocal _app
                if env.get("REQUEST_URI", "").startswith("/static"):
                    return _app(env, start_response)

                module, methods, error = self.search_module()
                _app = self.make_app(module, methods, error)
                return _app(env, start_response)

        else:
            return self.app

        return _wsgi_app


class RelativePathFilter(logging.Filter):
    def filter(self, record):
        path = Path(record.pathname).resolve()
        record.relativepath = str(path.relative_to(PROJECT_ROOT))
        return True


def main():
    parser = argparse.ArgumentParser(description="Run any Python library as a service")
    parser.add_argument(
        "-l", "--library", help="Python library / module to serve", required=True
    )
    parser.add_argument(
        "-i",
        "--ignore-hidden",
        action="store_true",
        help="Skip functions that start with an underscore",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Don't re-index the library / module on every request",
    )
    args = parser.parse_args()

    server = App(module=args.library, ignore_hidden=args.ignore_hidden)
    server.serve(
        _flask_debug=DEBUG,
        reload=not args.no_reload,
        host=os.getenv("HOST", "0.0.0.0"),
        port=os.getenv("PORT", "5000"),
    )
