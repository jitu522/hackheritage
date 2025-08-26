from flask import redirect, url_for, session
from db import get_db_connection, WEEK_DAYS
import random
import math
from datetime import datetime, time, timedelta

def init_assign_courses_routes(app):
    @app.route("/assign-courses")
    def assign_courses():
        if "routine_table" not in session or "courses_table" not in session:
            return redirect(url_for("select_details"))

        routine_table = session["routine_table"]
        courses_table = session["courses_table"]

        conn = get_db_connection()
        cur = conn.cursor()

        # Clear previous assignments (keep breaks)
        cur.execute(f"""
            UPDATE {routine_table}
            SET teacher_name = NULL, course_code = NULL, is_lab = FALSE
            WHERE time_slot != 'BREAK'
        """)

        # Determine slot duration in minutes
        cur.execute(f"SELECT slot_start, slot_end FROM {routine_table} LIMIT 1")
        start_time, end_time = cur.fetchone()
        
        # Convert time objects to minutes for calculation
        def time_to_minutes(t):
            if isinstance(t, timedelta):
                return t.total_seconds() // 60
            elif isinstance(t, time):
                return t.hour * 60 + t.minute
            elif isinstance(t, datetime):
                return t.hour * 60 + t.minute
            else:
                # Handle string format if needed
                return 0

        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)
        slot_minutes = int(end_minutes - start_minutes)

        def hours_to_slots(hours):
            return int((hours * 60) / slot_minutes)

        # Placement logic
        def place_courses(course_list, even_distribution=False, force_unique_days=False):
            cur.execute(f"SELECT DISTINCT day FROM {routine_table} ORDER BY day")
            all_days = [row[0] for row in cur.fetchall()]
            used_days_for_labs = set() if force_unique_days else None

            for teacher, code, session_time, sessions_needed, is_lab in course_list:
                try:
                    hours = int(session_time.split()[0])
                except Exception:
                    continue

                required_slots = hours_to_slots(hours)
                if required_slots <= 0:
                    continue

                booked = 0
                attempts = 0
                max_attempts = len(all_days) * 4

                while booked < sessions_needed and attempts < max_attempts:
                    cur.execute(f"""
                        SELECT day, COUNT(*) AS class_count
                        FROM {routine_table}
                        WHERE teacher_name IS NOT NULL
                          AND time_slot != 'BREAK'
                        GROUP BY day
                    """)
                    day_counts = {row[0]: row[1] for row in cur.fetchall()}

                    sorted_days = sorted(all_days, key=lambda d: day_counts.get(d, 0))

                    if force_unique_days:
                        available_days = [d for d in sorted_days if d not in used_days_for_labs]
                        if not available_days:
                            used_days_for_labs.clear()
                            available_days = sorted_days
                        sorted_days = available_days

                    if not even_distribution:
                        random.shuffle(sorted_days)

                    placed_this_round = False

                    for day in sorted_days:
                        # NEW CHECK: limit 1 tutorial per day per teacher
                        if not is_lab:
                            cur.execute(f"""
                                SELECT COUNT(*)
                                FROM {routine_table}
                                WHERE day = %s
                                  AND teacher_name = %s
                                  AND is_lab = FALSE
                                  AND time_slot != 'BREAK'
                            """, (day, teacher))
                            tutorial_count = cur.fetchone()[0]
                            if tutorial_count > 0:
                                continue

                        cur.execute(f"""
                            SELECT slot_start
                            FROM {routine_table}
                            WHERE teacher_name IS NULL
                              AND time_slot != 'BREAK'
                              AND day = %s
                            ORDER BY slot_start
                        """, (day,))
                        slots_for_day = [s for (s,) in cur.fetchall()]

                        if not slots_for_day:
                            continue

                        # Convert times to minutes for comparison
                        def slot_to_minutes(slot):
                            if isinstance(slot, timedelta):
                                return slot.total_seconds() // 60
                            elif isinstance(slot, time):
                                return slot.hour * 60 + slot.minute
                            elif isinstance(slot, datetime):
                                return slot.hour * 60 + slot.minute
                            return 0

                        morning_slots = [s for s in slots_for_day if slot_to_minutes(s) < 12 * 60]
                        afternoon_slots = [s for s in slots_for_day if slot_to_minutes(s) >= 12 * 60]
                        random.shuffle(morning_slots)
                        random.shuffle(afternoon_slots)
                        slots_for_day = morning_slots + afternoon_slots

                        for i in range(0, max(0, len(slots_for_day) - required_slots + 1)):
                            consecutive = slots_for_day[i:i + required_slots]
                            all_consecutive = True
                            for j in range(len(consecutive) - 1):
                                time1_minutes = slot_to_minutes(consecutive[j])
                                time2_minutes = slot_to_minutes(consecutive[j + 1])
                                diff = time2_minutes - time1_minutes
                                if diff != slot_minutes:
                                    all_consecutive = False
                                    break
                            if not all_consecutive:
                                continue

                            time_label = f"{teacher} {code}" + (" LAB" if is_lab else "")
                            for s in consecutive:
                                cur.execute(f"""
                                    UPDATE {routine_table}
                                    SET teacher_name = %s,
                                        course_code  = %s,
                                        time_slot    = %s,
                                        is_lab       = %s
                                    WHERE day = %s
                                      AND slot_start = %s
                                """, (teacher, code, time_label, is_lab, day, s))

                            booked += 1
                            if force_unique_days:
                                used_days_for_labs.add(day)
                            placed_this_round = True
                            break

                        if booked >= sessions_needed or placed_this_round:
                            break

                    attempts += 1

        # Get active days
        cur.execute(f"SELECT DISTINCT day FROM {routine_table} WHERE time_slot != 'BREAK' ORDER BY day")
        active_days = [row[0] for row in cur.fetchall()]

        # Fetch labs
        cur.execute(f"""
            SELECT teacher_name, course_code, lab_time, labs_per_week, TRUE AS is_lab
            FROM {courses_table}
            WHERE lab_time IS NOT NULL AND labs_per_week > 0
        """)
        labs = cur.fetchall()
        labs.sort(key=lambda x: (hours_to_slots(int(x[2].split()[0])), x[3]), reverse=True)
        total_labs = sum([lab[3] for lab in labs])
        force_unique = total_labs <= len(active_days)

        # Fetch tutorials
        cur.execute(f"""
            SELECT teacher_name, course_code, tutorial_time, tutorials_per_week, FALSE AS is_lab
            FROM {courses_table}
            WHERE tutorial_time IS NOT NULL AND tutorials_per_week > 0
        """)
        tutorials = cur.fetchall()
        tutorials.sort(key=lambda x: x[3], reverse=True)

        # Place labs
        place_courses(labs, even_distribution=False, force_unique_days=force_unique)

        # ---- NEW STEP: Ensure ~50:50 split of labs before/after break ----
        for day in active_days:
            cur.execute(f"""
                SELECT slot_start, time_slot, is_lab
                FROM {routine_table}
                WHERE day = %s
                ORDER BY slot_start
            """, (day,))
            slots = cur.fetchall()

            break_index = next((i for i, (_, ts, _) in enumerate(slots) if ts == "BREAK"), None)
            if break_index is None:
                continue

            before_idx = range(0, break_index)
            after_idx = range(break_index + 1, len(slots))

            before_labs = [i for i in before_idx if slots[i][2] is True]
            after_labs = [i for i in after_idx if slots[i][2] is True]
            total_labs_day = len(before_labs) + len(after_labs)

            if total_labs_day <= 1:
                continue

            target_before = total_labs_day // 2
            target_after = total_labs_day - target_before

            if total_labs_day % 2 == 1:
                if random.choice([True, False]):
                    target_before += 1
                else:
                    target_after += 1

            while len(before_labs) > target_before:
                lab_idx = before_labs.pop()
                empty_after = [i for i in after_idx if slots[i][2] is False and slots[i][1] != "BREAK" and slots[i][1] is None]
                if not empty_after:
                    break
                new_idx = random.choice(empty_after)
                cur.execute(f"""
                    UPDATE {routine_table}
                    SET teacher_name = NULL, course_code = NULL, is_lab = FALSE, time_slot = NULL
                    WHERE day = %s AND slot_start = %s
                """, (day, slots[lab_idx][0]))
                cur.execute(f"""
                    UPDATE {routine_table}
                    SET teacher_name = %s, course_code = %s, is_lab = TRUE, time_slot = %s
                    WHERE day = %s AND slot_start = %s
                """, (teacher, code, f"{teacher} {code} LAB", day, slots[new_idx][0]))

            while len(after_labs) > target_after:
                lab_idx = after_labs.pop()
                empty_before = [i for i in before_idx if slots[i][2] is False and slots[i][1] != "BREAK" and slots[i][1] is None]
                if not empty_before:
                    break
                new_idx = random.choice(empty_before)
                cur.execute(f"""
                    UPDATE {routine_table}
                    SET teacher_name = NULL, course_code = NULL, is_lab = FALSE, time_slot = NULL
                    WHERE day = %s AND slot_start = %s
                """, (day, slots[lab_idx][0]))
                cur.execute(f"""
                    UPDATE {routine_table}
                    SET teacher_name = %s, course_code = %s, is_lab = TRUE, time_slot = %s
                    WHERE day = %s AND slot_start = %s
                """, (teacher, code, f"{teacher} {code} LAB", day, slots[new_idx][0]))

        # Place tutorials after labs are balanced
        place_courses(tutorials, even_distribution=True, force_unique_days=False)

        # ---- Compact days with break preservation and after-break swap ----
        for day in active_days:
            cur.execute(f"""
                SELECT slot_start, slot_end, teacher_name, course_code, is_lab, time_slot
                FROM {routine_table}
                WHERE day = %s
                ORDER BY slot_start
            """, (day,))
            rows = cur.fetchall()

            break_indices = [i for i, r in enumerate(rows) if r[5] == "BREAK"]

            segments = []
            start_idx = 0
            for b_idx in break_indices + [len(rows)]:
                if start_idx < b_idx:
                    segments.append(rows[start_idx:b_idx])
                if b_idx < len(rows):
                    segments.append([rows[b_idx]])
                start_idx = b_idx + 1

            new_rows = []
            after_break_flag = False
            for segment in segments:
                if len(segment) == 1 and segment[0][5] == "BREAK":
                    new_rows.extend(segment)
                    after_break_flag = True
                else:
                    classes = [r for r in segment if r[2] is not None]
                    frees = [r for r in segment if r[2] is None and r[5] != "BREAK"]
                    compacted_segment = classes + frees

                    if after_break_flag and compacted_segment and compacted_segment[0][4] is True:
                        for idx in range(1, len(compacted_segment)):
                            if compacted_segment[idx][4] is False and compacted_segment[idx][2] is not None:
                                compacted_segment[0], compacted_segment[idx] = compacted_segment[idx], compacted_segment[0]
                                break
                    after_break_flag = False

                    while len(compacted_segment) < len(segment):
                        compacted_segment.append((None, None, None, None, False, None))
                    new_rows.extend(compacted_segment)

            for old, new in zip(rows, new_rows):
                if new[5] == "BREAK":
                    continue
                elif new[2] is not None:
                    cur.execute(f"""
                        UPDATE {routine_table}
                        SET teacher_name = %s,
                            course_code = %s,
                            is_lab = %s,
                            time_slot = %s
                        WHERE day = %s AND slot_start = %s
                    """, (new[2], new[3],
                          new[4], f"{new[2]} {new[3]}" + (" LAB" if new[4] else ""),
                          day, old[0]))
                else:
                    cur.execute(f"""
                        UPDATE {routine_table}
                        SET teacher_name = NULL,
                            course_code = NULL,
                            is_lab = FALSE,
                            time_slot = NULL
                        WHERE day = %s AND slot_start = %s
                    """, (day, old[0]))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("classroom_assignment"))