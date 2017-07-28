import pytest
from mock import Mock

import asyncio

import qth
import qth_registrar


@pytest.fixture("module")
def port():
    # A port which is likely to be free for the duration of tests...
    return 11223


@pytest.fixture("module")
def hostname():
    return "localhost"


@pytest.fixture("module")
def event_loop():
    return asyncio.get_event_loop()


@pytest.yield_fixture(scope="module")
def server(event_loop, port):
    mosquitto = event_loop.run_until_complete(asyncio.create_subprocess_exec(
        "mosquitto", "-p", str(port),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        loop=event_loop))

    try:
        yield
    finally:
        mosquitto.terminate()
        event_loop.run_until_complete(mosquitto.wait())


@pytest.fixture
async def client(server, hostname, port, event_loop):
    c = qth.Client("test-client",
                   host=hostname, port=port,
                   loop=event_loop)
    try:
        yield c
    finally:
        await c.close()


@pytest.fixture
async def reg(server, hostname, port, event_loop):
    r = qth_registrar.QthRegistrar(load_time=0.1,
                                   host=hostname, port=port,
                                   loop=event_loop)
    try:
        yield r
    finally:
        await r.close()



@pytest.mark.asyncio
async def test_registration(reg, client, event_loop):
    # Wait for (empty) root directory listing to be posted
    on_ls_event = asyncio.Event(loop=event_loop)
    on_ls = Mock(side_effect=lambda *_: on_ls_event.set())
    await client.watch_property("meta/ls/", on_ls)
    await asyncio.wait_for(on_ls_event.wait(), 5.0, loop=event_loop)
    on_ls.assert_called_once_with("meta/ls/", {
        "meta": [{"behaviour": "DIRECTORY",
                  "description": "A subdirectory.",
                  "client_id": None}],
    })
   
    # Registrations should appear
    on_ls_event.clear()
    on_ls.reset_mock()
    await client.register("test", qth.EVENT_ONE_TO_MANY, "A test event.")
    await asyncio.wait_for(on_ls_event.wait(), 5.0, loop=event_loop)
    on_ls.assert_called_once_with("meta/ls/", {
        "test": [{"behaviour": "EVENT-1:N",
                  "description": "A test event.",
                  "client_id": "test-client"}],
        "meta": [{"behaviour": "DIRECTORY",
                  "description": "A subdirectory.",
                  "client_id": None}],
    })
    
    # Unchanged registrations should not be resent
    on_ls_event.clear()
    on_ls.reset_mock()
    await client.publish_registration()
    await asyncio.sleep(0.1, loop=event_loop)
    assert on_ls.mock_calls == []
    
    # If many registrations are made in quick succession not every one should
    # result in a published message
    on_ls_event.clear()
    on_ls.reset_mock()
    on_ls_many = Mock()
    await client.watch_property("meta/ls/many/", on_ls_many)
    
    NUM_REGISTRATIONS = 20
    coros = []
    for i in range(NUM_REGISTRATIONS):
        coros.append(client.register("many/{}".format(i),
                                     qth.EVENT_ONE_TO_MANY,
                                     "An example."))
    done, pending = await asyncio.wait(coros, loop=event_loop)
    assert len(pending) == 0
    
    await asyncio.sleep(0.1, loop=event_loop)
    
    # Top level should have changed exactly once
    assert len(on_ls.mock_calls) == 1
    on_ls.assert_called_once_with("meta/ls/", {
        "test": [{"behaviour": "EVENT-1:N",
                  "description": "A test event.",
                  "client_id": "test-client"}],
        "many": [{"behaviour": "DIRECTORY",
                  "description": "A subdirectory.",
                  "client_id": None}],
        "meta": [{"behaviour": "DIRECTORY",
                  "description": "A subdirectory.",
                  "client_id": None}],
    })
    
    # Bottom level should have updated several times though the actual number
    # will vary. Note that though it is possible this test might fail due to
    # unfortunate timing, it should be unlikely in practice.
    assert 2 <= len(on_ls_many.mock_calls) < NUM_REGISTRATIONS
    on_ls_many.assert_called_with("meta/ls/many/", {
        str(i): [{"behaviour": "EVENT-1:N",
                  "description": "An example.",
                  "client_id": "test-client"}]
        for i in range(NUM_REGISTRATIONS)
    })
