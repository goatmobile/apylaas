import signal

signal.signal(signal.SIGUSR1, lambda a, b: 2)

import asyncio
import asyncio
import os
import websockets


CONNECTIONS = set()


async def register(websocket):
    print("New connection", websocket)
    CONNECTIONS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        CONNECTIONS.remove(websocket)


async def main():
    print("Running websocket server")
    async with websockets.serve(register, os.getenv("HOST", "0.0.0.0"), 5678):

        def signal_handler(sig, frame):
            print(f"Sending refresh to {len(CONNECTIONS)} clients")
            websockets.broadcast(CONNECTIONS, "reload")

        signal.signal(signal.SIGUSR1, signal_handler)
        while True:
            await asyncio.sleep(10000)


if __name__ == "__main__":
    asyncio.run(main())
