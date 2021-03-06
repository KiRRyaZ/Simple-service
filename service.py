import asyncio
from collections import OrderedDict
from functools import partial
from json import dumps, JSONDecodeError
import time

from aiohttp import web

from task import Task, Status


TASKS_IN_PROCESS_NUM = 4
CORO_NUM = 4
HOST = '127.0.0.1'
PORT = 8080


def _defalt_serializer(obj):
    if isinstance(obj, Status):
        return obj.name
    elif isinstance(obj, Task):
        json_task = obj.__dict__.copy()
        json_task.pop('resp_body')
        return json_task
    return str(obj)


def _log_task(action, id=None, time_=None):
    id_str = "" if id is None else f"#{id}"
    time_str = f" - {time_:.5f}" if time_ else ""
    print(f"{time.asctime()} {action:9} Task{id_str}{time_str}")


async def get_handler(request):
    _log_task("GET")
    if 'id' in request.query:
        try:
            key = int(request.query['id'])
            data = request.app['tasks'] \
                          .get(key, {
                                'error': 'There is no task with such ID'
                              })
        except ValueError:
            data = {
                "error": "ID must be a number"
            }
    else:
        data = list(request.app['tasks'].values())[-10:]
    return web.json_response(
        data,
        dumps=partial(dumps, default=_defalt_serializer)
    )


async def post_handler(request):
    try:
        data = await request.json()
        if 'url' in data:
            new_task = Task(data['url'])
            _log_task("POST", new_task.id)
            app['tasks'][new_task.id] = new_task
            await request.app['working_queue'].put(new_task)
            data = {'id': new_task.id}
        else:
            data = {'error': "You need to specify an url"}
    except JSONDecodeError:
        data = {'error': "You need to post a valid JSON"}
    return web.json_response(data)


async def task_handler(app):
    while True:
        task = await app['working_queue'].get()
        _log_task("START", task.id)
        start = time.time()
        await task()        
        end = time.time()
        if task.status == Status.Error:
            _log_task("EXCEPTION", task.id)
        else:
            _log_task("READY", task.id, end-start)


async def run_service(app):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    print("Start site")
    await site.start()


async def main(app):
    app['tasks'] = OrderedDict()
    app['working_queue'] = asyncio.Queue(TASKS_IN_PROCESS_NUM)
    handlers = [
        task_handler(app) for _ 
        in range(CORO_NUM) # number of coroutines can be adjusted
    ]
    await asyncio.gather(
        run_service(app),
        *handlers
    )


if __name__ == '__main__':
    app = web.Application()
    routes = [
        web.get('/', get_handler),
        web.post('/', post_handler)
    ]
    app.add_routes(routes)
    asyncio.run(main(app))