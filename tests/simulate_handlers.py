import asyncio
import types
import sys
import os
# Ensure project root is on sys.path so local packages (handlers, storage, tasks) can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from types import SimpleNamespace

# Minimal test harness to simulate Update/Message objects
class FakeMessage:
    def __init__(self):
        self.text = None
        self.chat_id = 12345
        self.document = None
        self.photo = []

    async def reply_text(self, text):
        print("REPLY:", text)

class FakePhoto:
    def __init__(self, file_id="abc123"):
        self.file_id = file_id

    async def get_file(self):
        class FakeFile:
            async def download_to_drive(self, custom_path):
                print(f"Downloading to: {custom_path}")
                # create an empty file to simulate download
                with open(custom_path, 'wb') as f:
                    f.write(b'')
        return FakeFile()

class FakeDocument:
    def __init__(self, file_name="doc.pdf", mime_type="application/pdf"):
        self.file_name = file_name
        self.mime_type = mime_type

    async def get_file(self):
        class FakeFile:
            async def download_to_drive(self, custom_path):
                print(f"Downloading doc to: {custom_path}")
                with open(custom_path, 'wb') as f:
                    f.write(b'')
        return FakeFile()

# Monkeypatch modules that handlers import (simple stubs)
# Create parent packages first so submodules can be imported
sys.modules.setdefault('tasks', types.ModuleType('tasks'))
sys.modules.setdefault('tasks.queue_manager', types.ModuleType('tasks.queue_manager'))
import tasks.queue_manager as qmod
qmod.enqueue_job = lambda *args, **kwargs: SimpleNamespace(id='fakejob')

sys.modules.setdefault('storage', types.ModuleType('storage'))
sys.modules.setdefault('storage.rate_limiter', types.ModuleType('storage.rate_limiter'))
import storage.rate_limiter as rmod
class RateLimiter:
    def allow(self, chat_id):
        return True
    def remaining(self, chat_id):
        return 1
rmod.RateLimiter = RateLimiter

sys.modules.setdefault('storage.cache', types.ModuleType('storage.cache'))
import storage.cache as cmod
class Cache:
    def exists(self, h):
        return False
    def get(self, h):
        return None
cmod.Cache = Cache

# Now import handlers
from handlers import commands, files

async def test_start():
    update = SimpleNamespace(message=FakeMessage())
    await commands.start(update, SimpleNamespace(user_data={}))

async def test_photo():
    msg = FakeMessage()
    msg.photo = [FakePhoto('photo1')]
    update = SimpleNamespace(message=msg)
    await files.handle_photo(update, SimpleNamespace(user_data={}))

async def test_document():
    msg = FakeMessage()
    msg.document = FakeDocument('test.pdf', 'application/pdf')
    update = SimpleNamespace(message=msg)
    await files.handle_document(update, SimpleNamespace(user_data={}))

async def main():
    print('--- TEST: /start ---')
    await test_start()
    print('--- TEST: photo ---')
    await test_photo()
    print('--- TEST: document ---')
    await test_document()

if __name__ == '__main__':
    asyncio.run(main())
