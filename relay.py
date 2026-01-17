import asyncio
import json
import websockets
import os
import uuid

PORT = int(os.environ.get("PORT", 10000))

clients = {}  # client_id -> {"ws": websocket, "name": str, "in_call": False}

async def broadcast_user_list():
    users = [
        {"id": cid, "name": info["name"], "in_call": info["in_call"]}
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
        clients[client_id] = {"ws": ws, "name": name, "in_call": False}
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

            # طلب مكالمة
            elif t == "call_request":
                to_id = data.get("to")
                if to_id in clients:
                    await send_to(to_id, {
                        "type": "call_request",
                        "from": client_id,
                        "from_name": name
                    })

            # قبول مكالمة
            elif t == "call_accept":
                to_id = data.get("to")
                if to_id in clients:
                    clients[client_id]["in_call"] = True
                    clients[to_id]["in_call"] = True
                    await send_to(to_id, {
                        "type": "call_accept",
                        "from": client_id,
                        "from_name": name
                    })
                    await broadcast_user_list()

            # رفض مكالمة
            elif t == "call_reject":
                to_id = data.get("to")
                if to_id in clients:
                    await send_to(to_id, {
                        "type": "call_reject",
                        "from": client_id,
                        "from_name": name
                    })

            # إنهاء مكالمة
            elif t == "call_end":
                to_id = data.get("to")
                if to_id in clients:
                    clients[client_id]["in_call"] = False
                    clients[to_id]["in_call"] = False
                    await send_to(to_id, {
                        "type": "call_end",
                        "from": client_id,
                        "from_name": name
                    })
                    await broadcast_user_list()

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
