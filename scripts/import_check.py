import sys
try:
    import backend.routers.auth
    import backend.routers.drivers
    import backend.routers.google_auth
    print('imports_ok')
except Exception as e:
    print('import_error', e)
    sys.exit(1)
