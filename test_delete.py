# -*- coding: utf-8 -*-
"""
Created on Sun Jul 20 19:53:47 2025

@author: ikram
"""

import sqlite3
from datetime import date


conn = sqlite3.connect('college_users.db') 
cursor = conn.cursor()
today = date.today().isoformat()
cursor.execute("DELETE FROM orders WHERE DATE(order_time) < ?", (today,))
conn.commit()
conn.close()

print("تم حذف الطلبات بنجاح.")
