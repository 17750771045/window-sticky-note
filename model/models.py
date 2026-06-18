import json
from model.database import db


class CategoryModel:
    MAX_COUNT = 50
    MAX_ITEMS = 1000

    @staticmethod
    def get_all():
        return db.fetchall("SELECT * FROM categories WHERE id > 0 ORDER BY sort_order")

    @staticmethod
    def get_by_id(cid):
        return db.fetchone("SELECT * FROM categories WHERE id=?", [cid])

    @staticmethod
    def add(name):
        count = db.fetchone("SELECT COUNT(*) as cnt FROM categories")
        if count["cnt"] >= CategoryModel.MAX_COUNT:
            return None
        sort_order = count["cnt"]
        cid = db.insert("categories", {"name": name, "sort_order": sort_order})
        return cid

    @staticmethod
    def update_name(cid, name):
        db.update("categories", {"name": name}, "id=?", [cid])

    @staticmethod
    def delete(cid):
        if cid <= 0:
            return
        db.execute("DELETE FROM categories WHERE id=?", [cid])

    @staticmethod
    def can_add_item(cid):
        count = db.fetchone(
            "SELECT COUNT(*) as cnt FROM notes WHERE category_id=? AND is_deleted=0", [cid]
        )
        return count["cnt"] < CategoryModel.MAX_ITEMS


class NoteModel:
    @staticmethod
    def get_all(category_id=None, include_deleted=False):
        sql = "SELECT * FROM notes"
        conditions = []
        params = []
        if not include_deleted:
            conditions.append("is_deleted=0")
        if category_id is not None and category_id > 0:
            conditions.append("category_id=?")
            params.append(category_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY updated_at DESC"
        return db.fetchall(sql, params)

    @staticmethod
    def get_by_id(nid):
        return db.fetchone("SELECT * FROM notes WHERE id=?", [nid])

    @staticmethod
    def add(title="", content="", note_type="text", file_path="", category_id=1):
        data = {
            "title": title,
            "content": content,
            "note_type": note_type,
            "file_path": file_path,
            "category_id": category_id,
        }
        nid = db.insert("notes", data)
        TimelineModel.log("create", "note", nid, "新建便签", "", json.dumps(data, ensure_ascii=False))
        return nid

    @staticmethod
    def update(nid, **kwargs):
        old = db.fetchone("SELECT * FROM notes WHERE id=?", [nid])
        if not old:
            return
        db.update("notes", kwargs, "id=?", [nid])
        TimelineModel.log(
            "modify", "note", nid,
            f"修改便签: {old.get('title', '')}",
            json.dumps(old, ensure_ascii=False),
            json.dumps({**old, **kwargs}, ensure_ascii=False),
        )

    @staticmethod
    def delete(nid):
        old = db.fetchone("SELECT * FROM notes WHERE id=?", [nid])
        db.soft_delete("notes", nid)
        if old:
            TimelineModel.log("delete", "note", nid, f"删除便签: {old.get('title', '')}",
                              json.dumps(old, ensure_ascii=False), "")

    @staticmethod
    def restore(nid):
        db.restore("notes", nid)
        TimelineModel.log("restore", "note", nid, "恢复便签", "", "")


class TodoModel:
    @staticmethod
    def get_all(category_id=None, include_deleted=False):
        sql = "SELECT * FROM todos"
        conditions = []
        params = []
        if not include_deleted:
            conditions.append("is_deleted=0")
        if category_id is not None and category_id > 0:
            conditions.append("category_id=?")
            params.append(category_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY sort_order, created_at"
        return db.fetchall(sql, params)

    @staticmethod
    def get_by_id(tid):
        return db.fetchone("SELECT * FROM todos WHERE id=?", [tid])

    @staticmethod
    def get_by_quadrant(quadrant, category_id=None):
        sql = "SELECT * FROM todos WHERE is_deleted=0 AND is_completed=0 AND quadrant=?"
        params = [quadrant]
        if category_id is not None and category_id > 0:
            sql += " AND category_id=?"
            params.append(category_id)
        sql += " ORDER BY sort_order"
        return db.fetchall(sql, params)

    @staticmethod
    def add(content, quadrant=1, priority=0, category_id=1, due_date=None):
        max_order = db.fetchone("SELECT MAX(sort_order) as mo FROM todos WHERE is_deleted=0")
        sort_order = (max_order["mo"] or 0) + 1
        data = {
            "content": content,
            "quadrant": quadrant,
            "priority": priority,
            "category_id": category_id,
            "due_date": due_date,
            "sort_order": sort_order,
        }
        tid = db.insert("todos", data)
        TimelineModel.log("create", "todo", tid, "新建待办", "", json.dumps(data, ensure_ascii=False))
        return tid

    @staticmethod
    def toggle_complete(tid):
        todo = db.fetchone("SELECT * FROM todos WHERE id=?", [tid])
        if not todo:
            return
        new_state = 0 if todo["is_completed"] else 1
        db.update("todos", {"is_completed": new_state}, "id=?", [tid])
        TimelineModel.log(
            "modify", "todo", tid,
            f"{'完成' if new_state else '取消完成'}待办: {todo['content']}",
            "", "",
        )

    @staticmethod
    def update_sort(tid, sort_order):
        db.update("todos", {"sort_order": sort_order}, "id=?", [tid])

    @staticmethod
    def update(tid, **kwargs):
        old = db.fetchone("SELECT * FROM todos WHERE id=?", [tid])
        if not old:
            return
        db.update("todos", kwargs, "id=?", [tid])
        TimelineModel.log("modify", "todo", tid, f"修改待办", "", "")

    @staticmethod
    def delete(tid):
        old = db.fetchone("SELECT * FROM todos WHERE id=?", [tid])
        db.soft_delete("todos", tid)
        if old:
            TimelineModel.log("delete", "todo", tid, f"删除待办: {old['content']}",
                              json.dumps(old, ensure_ascii=False), "")

    @staticmethod
    def restore(tid):
        db.restore("todos", tid)
        TimelineModel.log("restore", "todo", tid, "恢复待办", "", "")


class ReminderModel:
    @staticmethod
    def get_all(include_deleted=False):
        sql = "SELECT * FROM reminders"
        if not include_deleted:
            sql += " WHERE is_deleted=0"
        sql += " ORDER BY remind_time"
        return db.fetchall(sql)

    @staticmethod
    def get_upcoming(limit=20):
        return db.fetchall(
            "SELECT * FROM reminders WHERE is_deleted=0 AND is_triggered=0 "
            "ORDER BY remind_time LIMIT ?", [limit]
        )

    @staticmethod
    def add(title, remind_time, content="", repeat_type="none", is_lunar=False,
            is_important=False, interval_minutes=0, category_id=1):
        data = {
            "title": title,
            "content": content,
            "remind_time": remind_time,
            "repeat_type": repeat_type,
            "is_lunar": 1 if is_lunar else 0,
            "is_important": 1 if is_important else 0,
            "interval_minutes": interval_minutes,
            "category_id": category_id,
        }
        rid = db.insert("reminders", data)
        TimelineModel.log("create", "reminder", rid, "新建提醒", "", json.dumps(data, ensure_ascii=False))
        return rid

    @staticmethod
    def update(rid, **kwargs):
        old = db.fetchone("SELECT * FROM reminders WHERE id=?", [rid])
        if not old:
            return
        db.update("reminders", kwargs, "id=?", [rid])
        TimelineModel.log("modify", "reminder", rid, f"修改提醒: {old.get('title', '')}", "", "")

    @staticmethod
    def delete(rid):
        old = db.fetchone("SELECT * FROM reminders WHERE id=?", [rid])
        db.soft_delete("reminders", rid)
        if old:
            TimelineModel.log("delete", "reminder", rid, f"删除提醒: {old['title']}",
                              json.dumps(old, ensure_ascii=False), "")

    @staticmethod
    def restore(rid):
        db.restore("reminders", rid)
        TimelineModel.log("restore", "reminder", rid, "恢复提醒", "", "")


class TimelineModel:
    @staticmethod
    def log(action_type, target_type, target_id, detail, old_data="", new_data=""):
        db.insert("timeline", {
            "action_type": action_type,
            "target_type": target_type,
            "target_id": target_id,
            "detail": detail,
            "old_data": old_data,
            "new_data": new_data,
        })

    @staticmethod
    def get_all(target_type=None, action_type=None, keyword="", limit=200):
        sql = "SELECT * FROM timeline WHERE 1=1"
        params = []
        if target_type:
            sql += " AND target_type=?"
            params.append(target_type)
        if action_type:
            sql += " AND action_type=?"
            params.append(action_type)
        if keyword:
            sql += " AND detail LIKE ?"
            params.append(f"%{keyword}%")
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return db.fetchall(sql, params)


class LedgerModel:
    @staticmethod
    def get_all(year_month=None):
        sql = "SELECT * FROM ledger WHERE is_deleted=0"
        params = []
        if year_month:
            sql += " AND strftime('%Y-%m', ledger_date)=?"
            params.append(year_month)
        sql += " ORDER BY ledger_date DESC, created_at DESC"
        return db.fetchall(sql, params)

    @staticmethod
    def add(amount, ledger_type, category="", note="", ledger_date=""):
        from datetime import datetime
        if not ledger_date:
            ledger_date = datetime.now().strftime("%Y-%m-%d")
        lid = db.insert("ledger", {
            "amount": amount,
            "ledger_type": ledger_type,
            "category": category,
            "note": note,
            "ledger_date": ledger_date,
        })
        return lid

    @staticmethod
    def delete(lid):
        db.soft_delete("ledger", lid)

    @staticmethod
    def get_summary(year_month=None):
        sql = "SELECT ledger_type, SUM(amount) as total FROM ledger WHERE is_deleted=0"
        params = []
        if year_month:
            sql += " AND strftime('%Y-%m', ledger_date)=?"
            params.append(year_month)
        sql += " GROUP BY ledger_type"
        return db.fetchall(sql, params)


class QuickToolModel:
    MAX_TOOLS = 6

    @staticmethod
    def get_all():
        return db.fetchall("SELECT * FROM quick_tools ORDER BY sort_order")

    @staticmethod
    def add(name, tool_type, icon="", command=""):
        count = db.fetchone("SELECT COUNT(*) as cnt FROM quick_tools")
        if count["cnt"] >= QuickToolModel.MAX_TOOLS:
            return None
        sort_order = count["cnt"]
        return db.insert("quick_tools", {
            "name": name, "tool_type": tool_type,
            "icon": icon, "command": command, "sort_order": sort_order,
        })

    @staticmethod
    def delete(tid):
        db.execute("DELETE FROM quick_tools WHERE id=?", [tid])
