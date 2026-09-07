import sqlite3
p='c:/Users/pocha/Projects/GenerativeAIForBusiness/api/fraumatch_demo.db'
conn=sqlite3.connect(p)
cur=conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cur.fetchall())
conn.close()
