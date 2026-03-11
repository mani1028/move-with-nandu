import sqlite3, os
p='d:/projects/travel/nandu.db'
if not os.path.exists(p):
    print('NO_DB')
    raise SystemExit(0)
conn=sqlite3.connect(p)
cur=conn.cursor()
# list tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
rows=cur.fetchall()
print('TABLES:', [r[0] for r in rows])
for t in [r[0] for r in rows]:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        c=cur.fetchone()[0]
        print(f'{t}:', c)
    except Exception as e:
        print(f'{t}: ERROR', e)
conn.close()
