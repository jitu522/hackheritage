from flask import render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import re
from db import get_db_connection, WEEK_DAYS

def init_time_slots_routes(app):
    @app.route("/time-slots", methods=["GET", "POST"])
    def time_slots():
        if "branch" not in session:
            return redirect(url_for("select_details"))

        if request.method == "POST":
            branch = session["branch"].lower()
            sem = session["semester"]
            year = session["year"]

            start_time = request.form["start_time"]
            end_time = request.form["end_time"]
            slot_duration = int(request.form["slot_duration"])
            break_start = request.form["break_start"]
            break_end = request.form["break_end"]
            start_day = request.form.get("start_day", "Monday")
            end_day = request.form.get("end_day", "Friday")

            session["start_day"] = start_day
            session["end_day"] = end_day

            routine_table = re.sub(r'\W+', '_', f"{branch}_{sem}_{year}_routine".lower())
            session["routine_table"] = routine_table

            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {routine_table} (
                    day VARCHAR(20),
                    time_slot VARCHAR(100),
                    slot_start TIME,
                    slot_end TIME,
                    teacher_name VARCHAR(100) DEFAULT NULL,
                    course_code VARCHAR(50) DEFAULT NULL,
                    is_lab BOOLEAN DEFAULT FALSE,
                    classroom VARCHAR(20) DEFAULT NULL,
                    PRIMARY KEY (day, slot_start)
                ) 
            """)

            cur.execute(f"DELETE FROM {routine_table}")

            fmt = "%H:%M"
            start_dt = datetime.strptime(start_time, fmt)
            end_dt = datetime.strptime(end_time, fmt)
            break_s = datetime.strptime(break_start, fmt)
            break_e = datetime.strptime(break_end, fmt)

            s_idx = WEEK_DAYS.index(start_day)
            e_idx = WEEK_DAYS.index(end_day)
            if s_idx <= e_idx:
                days_range = WEEK_DAYS[s_idx:e_idx + 1]
            else:
                days_range = WEEK_DAYS[s_idx:] + WEEK_DAYS[:e_idx + 1]

            for day in days_range:
                current = start_dt
                while current < end_dt:
                    next_slot = current + timedelta(minutes=slot_duration)
                    slot_label = f"{current.strftime('%H:%M')} - {next_slot.strftime('%H:%M')}"

                    if break_s <= current < break_e:
                        cur.execute(
                            f"INSERT INTO {routine_table} (day, time_slot, slot_start, slot_end) VALUES (%s, %s, %s, %s)",
                            (day, "BREAK", current.time(), next_slot.time())
                        )
                    else:
                        cur.execute(
                            f"INSERT INTO {routine_table} (day, time_slot, slot_start, slot_end) VALUES (%s, %s, %s, %s)",
                            (day, slot_label, current.time(), next_slot.time())
                        )

                    current = next_slot

            conn.commit()
            cur.close()
            conn.close()

            return redirect(url_for("assign_courses"))

        return render_template("time_slots.html", week_days=WEEK_DAYS)