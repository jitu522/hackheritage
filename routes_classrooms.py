from flask import render_template, request, redirect, url_for, session
from db import get_db_connection
import random

def init_classroom_routes(app):

    def assign_classrooms_for_multi_sessions(cur, routine_table, tutorial_rooms, lab_rooms):
        """Assign classrooms for multi-slot sessions."""

        # MySQL-compatible query (removed PostgreSQL-specific parts and ORDER BY RAND())
        cur.execute(f"""
            SELECT 
                day, 
                teacher_name, 
                course_code, 
                is_lab,
                MIN(slot_start) AS start_time, 
                MAX(slot_end) AS end_time,
                COUNT(*) AS session_count
            FROM {routine_table}
            WHERE teacher_name IS NOT NULL
            GROUP BY day, teacher_name, course_code, is_lab
            HAVING COUNT(*) > 1
        """)
        multi_sessions = cur.fetchall()

        # Shuffle results in Python instead of using RAND()
        random.shuffle(multi_sessions)

        for day, teacher, code, is_lab, start, end, count in multi_sessions:
            rooms = lab_rooms if is_lab else tutorial_rooms
            room = random.choice(rooms)

            # Use equality for slot boundaries (>= and <= can skip if multiple sessions overlap)
            cur.execute(f"""
                UPDATE {routine_table}
                SET classroom = %s
                WHERE day = %s
                  AND slot_start >= %s
                  AND slot_end <= %s
                  AND teacher_name = %s
                  AND course_code = %s
            """, (room, day, start, end, teacher, code))

    def assign_classrooms_for_single_sessions(cur, routine_table, tutorial_rooms, lab_rooms):
        """Assign classrooms for single-slot sessions."""

        # MySQL version (removed PostgreSQL-only syntax)
        cur.execute(f"""
            SELECT day, slot_start, slot_end, teacher_name, course_code, is_lab
            FROM {routine_table}
            WHERE teacher_name IS NOT NULL
              AND time_slot <> 'BREAK'
              AND classroom IS NULL
        """)
        single_sessions = cur.fetchall()

        # Shuffle to randomize instead of ORDER BY RAND()
        random.shuffle(single_sessions)

        for i, (day, start, end, teacher, code, is_lab) in enumerate(single_sessions):
            rooms = lab_rooms if is_lab else tutorial_rooms
            room = rooms[i % len(rooms)]

            cur.execute(f"""
                UPDATE {routine_table}
                SET classroom = %s
                WHERE day = %s
                  AND slot_start = %s
                  AND slot_end = %s
                  AND teacher_name = %s
                  AND course_code = %s
            """, (room, day, start, end, teacher, code))

    @app.route("/classroom-assignment", methods=["GET", "POST"])
    def classroom_assignment():
        if "routine_table" not in session:
            return redirect(url_for("select_details"))

        if request.method == "POST":
            tutorial_rooms = [room.strip() for room in request.form["tutorial_rooms"].split(",") if room.strip()]
            lab_rooms = [room.strip() for room in request.form["lab_rooms"].split(",") if room.strip()]

            if not tutorial_rooms or not lab_rooms:
                return render_template("classroom_assignment.html", 
                                       error="Please provide at least one classroom for each type")

            session["tutorial_rooms"] = tutorial_rooms
            session["lab_rooms"] = lab_rooms

            conn = get_db_connection()
            cur = conn.cursor()
            routine_table = session["routine_table"]

            # Clear any existing classroom assignments
            cur.execute(f"""
                UPDATE {routine_table}
                SET classroom = NULL
                WHERE teacher_name IS NOT NULL
            """)

            # Assign classrooms to multi-slot sessions first
            assign_classrooms_for_multi_sessions(cur, routine_table, tutorial_rooms, lab_rooms)

            # Then assign to single-slot sessions
            assign_classrooms_for_single_sessions(cur, routine_table, tutorial_rooms, lab_rooms)

            conn.commit()
            cur.close()
            conn.close()

            return redirect(url_for("view_routine"))

        return render_template("classroom_assignment.html")
