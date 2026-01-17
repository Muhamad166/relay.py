import asyncio
import json
import websockets
import os
import uuid

PORT = int(os.environ.get("PORT", 10000))

# client_id -> {"ws": websocket, "name": str}
clients = {}


async def broadcast_user_list():
    users = [
        {"id": cid, "name": info["name"]}
        for cid, info in clients.items()
    ]
    msg = json.dumps({"type": "users", "users": users})
    await asyncio.gather(*[
        info["ws"].send(msg)
        for info in clients.values()
    ])


async def send_to(client_id, data):
    if client_id in clients:
        await clients[client_id]["ws"].send(json.dumps(data))


async def handler(ws, path):
    client_id = str(uuid.uuid4())
    name = None
    try:
        # أول رسالة لازم تكون join
        join_raw = await ws.recv()
        join = json.loads(join_raw)
        if join.get("type") != "join" or "name" not in join:
            await ws.close()
            return

        name = join["name"]
        clients[client_id] = {"ws": ws, "name": name}
        print(f"{name} joined as {client_id}")

        # أرسل له الـ id تبعه
        await ws.send(json.dumps({
            "type": "welcome",
            "id": client_id,
            "name": name
        }))

        # حدّث قائمة المستخدمين للجميع
        await broadcast_user_list()

        # استقبل باقي الرسائل
        async for raw in ws:
            try:
                data = json.loads(raw)
            except:
                continue

            t = data.get("type")

            # رسالة نصية
            if t == "message":
                to_id = data.get("to")
                text = data.get("text", "")
                if to_id in clients:
                    await send_to(to_id, {
                        "type": "message",
                        "from": client_id,
                        "from_name": name,
                        "text": text
                    })

            # تذكير (إشعار بسيط)
            elif t == "reminder":
                to_id = data.get("to")
                if to_id in clients:
                    await send_to(to_id, {
                        "type": "reminder",
                        "from": client_id,
                        "from_name": name
                    })

            # رسالة صوتية (audio_base64)
            elif t == "voice":
                to_id = data.get("to")
                audio = data.get("audio", "")
                if to_id in clients:
                    await send_to(to_id, {
                        "type": "voice",
                        "from": client_id,
                        "from_name": name,
                        "audio": audio
                    })

    finally:
        if client_id in clients:
            print(f"{name} left")
            del clients[client_id]
            await broadcast_user_list()


async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Server running on port {PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
