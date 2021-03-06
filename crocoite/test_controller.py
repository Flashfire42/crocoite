# Copyright (c) 2017–2018 crocoite contributors
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import asyncio

from yarl import URL
from aiohttp import web

import pytest

from .logger import Logger
from .controller import ControllerSettings, SinglePageController
from .devtools import Process
from .test_browser import loader

@pytest.mark.asyncio
async def test_controller_timeout ():
    """ Make sure the controller terminates, even if the site keeps reloading/fetching stuff """

    async def f (req):
        return web.Response (body="""<html>
<body>
<p>hello</p>
<script>
window.setTimeout (function () { window.location = '/' }, 250);
window.setInterval (function () { fetch('/').then (function (e) { console.log (e) }) }, 150);
</script>
</body>
</html>""", status=200, content_type='text/html', charset='utf-8')

    url = URL.build (scheme='http', host='localhost', port=8080)
    app = web.Application ()
    app.router.add_route ('GET', '/', f)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, url.host, url.port)
    await site.start()

    loop = asyncio.get_event_loop ()
    try:
        logger = Logger ()
        settings = ControllerSettings (idleTimeout=1, timeout=5)
        controller = SinglePageController (url=url, logger=logger,
                service=Process (), behavior=[], settings=settings)
        # give the controller a little more time to finish, since there are
        # hard-coded asyncio.sleep calls in there right now.
        # XXX fix this
        before = loop.time ()
        await asyncio.wait_for (controller.run (), settings.timeout*2)
        after = loop.time ()
        assert after-before >= settings.timeout
    finally:
        await runner.cleanup ()

@pytest.mark.asyncio
async def test_controller_idle_timeout ():
    """ Make sure the controller terminates, even if the site keeps reloading/fetching stuff """

    async def f (req):
        return web.Response (body="""<html>
<body>
<p>hello</p>
<script>
window.setInterval (function () { fetch('/').then (function (e) { console.log (e) }) }, 2000);
</script>
</body>
</html>""", status=200, content_type='text/html', charset='utf-8')

    url = URL.build (scheme='http', host='localhost', port=8080)
    app = web.Application ()
    app.router.add_route ('GET', '/', f)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, url.host, url.port)
    await site.start()

    loop = asyncio.get_event_loop ()
    try:
        logger = Logger ()
        settings = ControllerSettings (idleTimeout=1, timeout=60)
        controller = SinglePageController (url=url, logger=logger,
                service=Process (), behavior=[], settings=settings)
        before = loop.time ()
        await asyncio.wait_for (controller.run (), settings.timeout*2)
        after = loop.time ()
        assert settings.idleTimeout <= after-before <= settings.idleTimeout*2+3
    finally:
        await runner.cleanup ()

