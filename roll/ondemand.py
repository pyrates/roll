import inspect
from functools import wraps


def preprocessors(func):
    return getattr(func, '__before__', None)


def signed(func):
    if getattr(func, '__signature__', None) is None:
        func.__signature__ = inspect.signature(func, follow_wrapped=True)
    return func


def before(*funcs):
    def persist_preprocessors(func):
        if preprocessors(func) is not None:
            raise RuntimeError(
                f'{func} is already annotated with `before` functions.')
        func.__before__ = [signed(f) for f in funcs]
        return signed(func)
    return persist_preprocessors


async def process(func, request, response):

    async def func_args(s, **route_vars):
        for name, param in s.parameters.items():
            if param.kind != param.VAR_KEYWORD:
                if name == 'request':
                    yield name, request
                elif name == 'response':
                    yield name, response
                elif name in request.__namespace__:
                    member = getattr(request, name)
                    if inspect.iscoroutine(member):
                        yield name, await member
                    else:
                        yield name, member
                elif name in route_vars:
                    yield name, route_vars.pop(name)
            else:
                for name, value in route_vars.items():
                    yield name, value

    async def apply(func):
        s = func.__signature__
        args = dict([f async for f in func_args(s, **request.route.vars)])
        bound = s.bind(**args)
        return await func(*bound.args, **bound.kwargs)

    preprocs = preprocessors(func)
    if preprocs is not None:
        for preproc in preprocs:
            await apply(preproc)

    await apply(func)
