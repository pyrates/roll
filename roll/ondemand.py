import inspect
import functools
from .io import Request, Response
from .http import Cookies, Files, Form, Query


def ondemand(func):
    func.__ondemand_signature__ = inspect.signature(func)

    @functools.wraps(func)
    async def ondemand_wrapper(request, response, **kwargs):
        signature = func.__ondemand_signature__
        to_bind = {}
        for name, param in signature.parameters.items():
            if param.annotation is Request:
                to_bind[name] = request
            elif param.annotation is Response:
                to_bind[name] = response
            elif param.annotation is Cookies:
                to_bind[name] = request.cookies
            elif param.annotation is Files:
                await request.load_body()
                to_bind[name] = request.files
            elif param.annotation is Form:
                await request.load_body()
                to_bind[name] = request.form
            elif param.annotation is Query:
                await request.load_body()
                to_bind[name] = request.query
            elif name in request.route.vars:
                to_bind[name] = request.route.vars[name]

        bound = signature.bind(**to_bind)
        return await func(*bound.args, **bound.kwargs)

    return ondemand_wrapper
