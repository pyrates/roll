import inspect
from functools import wraps


def preprocessors(func):
    return getattr(func, '__before__', None)


def signature(func):
    if getattr(func, '__signature__', None) is None:
        func.__signature__ = inspect.signature(func, follow_wrapped=True)
    return func.__signature__


def signed(func):
    signature(func)
    return func


def before(*funcs):
    def persist_preprocessors(func):
        if preprocessors(func) is not None:
            raise RuntimeError(
                f'{func} is already annotated with `before` functions.')
        func.__before__ = [signed(f) for f in funcs]
        return signed(func)
    return persist_preprocessors


AWAITABLE = frozenset({'body', 'form', 'query', 'json'})


async def process(func, request, response):

    async def func_args(s, **route_params):
        for name, param in s.parameters.items():
            if param.kind != param.VAR_KEYWORD:
                if name == 'request':
                    yield name, request
                elif name == 'response':
                    yield name, response
                elif name in AWAITABLE:
                    # It is cached on the request itself.
                    yield name, await getattr(request, name)
                elif name in route_params:
                    yield name, route_params.pop(name)
            else:
                for name, value in route_params.items():
                    yield name, value

    async def apply(func):
        s = signature(func)
        args = dict([f async for f in func_args(s, **request.route.vars)])
        bound = s.bind(**args)
        return await func(*bound.args, **bound.kwargs)
    
    preprocs = preprocessors(func)
    if preprocs is not None:
        for preproc in preprocs:
            await apply(preproc)

    await apply(func)
