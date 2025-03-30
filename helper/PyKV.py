import sqlite3
import json

class PyKV:
    def __init__(self):
        self.filename = None
        self.db = None

    def open(self, filename):
        self.filename = filename
        self.db = sqlite3.connect(filename)
        cursor = self.db.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS kv_pairs (key TEXT PRIMARY KEY, value TEXT)")
        self.db.commit()
        cursor.close()

    def close(self):
        if self.db:
            self.db.close()
            self.db = None

    def get(self, key):
        cursor = self.db.cursor()
        cursor.execute("SELECT value FROM kv_pairs WHERE key = ?", (key,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return False
        else:
            return False

    def get_kv(self, key):
        cursor = self.db.cursor()
        cursor.execute("SELECT value FROM kv_pairs WHERE key = ?", (key,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            try:
                return {"key": key, "value": json.loads(row[0])}
            except json.JSONDecodeError:
                return False
        else:
            return False

    def put(self, key, value):
        value_str = json.dumps(value)
        cursor = self.db.cursor()
        cursor.execute("INSERT OR REPLACE INTO kv_pairs (key, value) VALUES (?, ?)", (key, value_str))
        self.db.commit()
        cursor.close()

    def search(self, searchString):
        results = []
        cursor = self.db.cursor()
        cursor.execute("SELECT key, value FROM kv_pairs WHERE value LIKE ?", ('%' + searchString + '%',))
        rows = cursor.fetchall()
        for row in rows:
            key, value_str = row
            try:
                results.append({"key": key, "value": json.loads(value_str)})
            except json.JSONDecodeError:
                pass
        cursor.close()
        return results

    def search_json(self, valueKey, searchString):
        results = []
        cursor = self.db.cursor()
        cursor.execute("SELECT key, value FROM kv_pairs")
        rows = cursor.fetchall()
        for row in rows:
            key, value_str = row
            try:
                value = json.loads(value_str)
                value_key_components = valueKey.split('.')
                curr_value = value
                for value_key_component in value_key_components:
                    if isinstance(curr_value, dict) and value_key_component in curr_value:
                        curr_value = curr_value[value_key_component]
                    else:
                        curr_value = None
                        break
                if curr_value is not None and searchString in str(curr_value):
                    results.append({"key": key, "value": value})
            except json.JSONDecodeError:
                pass
        cursor.close()
        return results

    def search_key(self, searchString):
        results = []
        cursor = self.db.cursor()
        cursor.execute("SELECT key, value FROM kv_pairs WHERE key LIKE ?", ('%' + searchString + '%',))
        rows = cursor.fetchall()
        for row in rows:
            key, value_str = row
            try:
                results.append({"key": key, "value": json.loads(value_str)})
            except json.JSONDecodeError:
                pass # Or handle error
        cursor.close()
        return results

    def list_keys(self):
        results = []
        cursor = self.db.cursor()
        cursor.execute("SELECT key FROM kv_pairs")
        rows = cursor.fetchall()
        for row in rows:
            results.append(row[0])
        cursor.close()
        return results

    def delete(self, key):
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM kv_pairs WHERE key = ?", (key,))
        self.db.commit()
        cursor.close()