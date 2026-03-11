import importlib
modules = [
    'backend.database','backend.auth','backend.routers.auth',
    'backend.routers.drivers','backend.routers.users','backend.routers.admin'
]
for m in modules:
    importlib.import_module(m)
    print('OK', m)
print('done')
