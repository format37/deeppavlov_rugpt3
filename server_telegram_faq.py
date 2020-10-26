import asyncio
from aiohttp import web

WEBHOOK_PORT = 8081
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

async def call_test(request):
	return web.Response(text='ok',content_type="text/html")

async def call_talk(request):
	question = request.rel_url.query['question']	
	return web.Response(text=question,content_type="text/html")

app = web.Application()
app.router.add_route('GET', '/test', call_test)
app.router.add_route('GET', '/question', call_talk)

web.run_app(
    app,
    host=WEBHOOK_LISTEN,
    port=WEBHOOK_PORT,
)