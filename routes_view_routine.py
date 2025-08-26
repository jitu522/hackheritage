from flask import render_template, redirect, url_for, session, Response
from db import get_db_connection, WEEK_DAYS
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
from datetime import datetime, timedelta

def format_time_range(start, end):
    """Convert TIME or timedelta values into HH:MM string ranges (works for MySQL & Postgres)."""
    if isinstance(start, timedelta):  # MySQL TIME often comes as timedelta
        start_time = (datetime.min + start).time()
        end_time = (datetime.min + end).time()
    else:  # Postgres returns datetime.time
        start_time = start
        end_time = end
    return f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

def init_view_routine_routes(app):
    @app.route("/view-routine")
    def view_routine():
        if "routine_table" not in session:
            return redirect(url_for("select_details"))

        routine_table = session["routine_table"]

        conn = get_db_connection()
        cur = conn.cursor()

        # Get time slots for headers
        cur.execute(f"""
            SELECT DISTINCT slot_start, slot_end 
            FROM {routine_table} 
            ORDER BY slot_start
        """)
        slots = cur.fetchall()
        slot_labels = [format_time_range(s[0], s[1]) for s in slots]

        # Get days in order
        start_day = session.get("start_day", "Monday")
        end_day = session.get("end_day", "Friday")
        s_idx = WEEK_DAYS.index(start_day)
        e_idx = WEEK_DAYS.index(end_day)
        days_range = WEEK_DAYS[s_idx:e_idx+1] if s_idx <= e_idx else WEEK_DAYS[s_idx:] + WEEK_DAYS[:e_idx+1]

        # Get all routine data
        cur.execute(f"""
            SELECT day, slot_start, slot_end, teacher_name, course_code, is_lab, classroom
            FROM {routine_table}
            ORDER BY day, slot_start
        """)
        rows = cur.fetchall()

        # Organize data for display
        routine = {day: {slot: "Free" for slot in slot_labels} for day in days_range}

        for day, start, end, teacher, code, is_lab, classroom in rows:
            slot_label = format_time_range(start, end)
            if teacher:
                display_text = f"{teacher}\n{code}"
                if is_lab:
                    display_text += " (Lab)"
                if classroom:
                    display_text += f"\nRoom: {classroom}"
                routine[day][slot_label] = display_text
            elif routine[day][slot_label] == "Free":
                # Check if this is a break slot
                cur.execute(f"""
                    SELECT 1 FROM {routine_table}
                    WHERE day = %s AND slot_start = %s AND time_slot = 'BREAK'
                """, (day, start))
                if cur.fetchone():
                    routine[day][slot_label] = "Break"

        # Prepare table rows for HTML
        table_rows = [[day] + [routine[day][slot] for slot in slot_labels] for day in days_range]

        cur.close()
        conn.close()

        return render_template(
            "view_routine.html",
            slot_labels=slot_labels,
            table_rows=table_rows,
            branch=session.get("branch"),
            semester=session.get("semester"),
            year=session.get("year")
        )

    @app.route("/download-routine")
    def download_routine():
        if "routine_table" not in session:
            return redirect(url_for("select_details"))

        # Create a PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        elements = []

        # Add title
        styles = getSampleStyleSheet()
        title = Paragraph(
            f"Routine for {session.get('branch')} - Semester {session.get('semester')} - {session.get('year')}",
            styles['Title']
        )
        elements.append(title)

        routine_table = session["routine_table"]
        conn = get_db_connection()
        cur = conn.cursor()

        # Get time slots
        cur.execute(f"""
            SELECT DISTINCT slot_start, slot_end 
            FROM {routine_table} 
            ORDER BY slot_start
        """)
        slots = cur.fetchall()
        slot_labels = [format_time_range(s[0], s[1]) for s in slots]

        # Days in order
        start_day = session.get("start_day", "Monday")
        end_day = session.get("end_day", "Friday")
        s_idx = WEEK_DAYS.index(start_day)
        e_idx = WEEK_DAYS.index(end_day)
        days_range = WEEK_DAYS[s_idx:e_idx+1] if s_idx <= e_idx else WEEK_DAYS[s_idx:] + WEEK_DAYS[:e_idx+1]

        # Get all routine data
        cur.execute(f"""
            SELECT day, slot_start, slot_end, teacher_name, course_code, is_lab, classroom
            FROM {routine_table}
            ORDER BY day, slot_start
        """)
        rows = cur.fetchall()

        routine = {day: {slot: "Free" for slot in slot_labels} for day in days_range}

        for day, start, end, teacher, code, is_lab, classroom in rows:
            slot_label = format_time_range(start, end)
            if teacher:
                display_text = f"{teacher}\n{code}"
                if is_lab:
                    display_text += " (Lab)"
                if classroom:
                    display_text += f"\nRoom: {classroom}"
                routine[day][slot_label] = display_text
            elif routine[day][slot_label] == "Free":
                cur.execute(f"""
                    SELECT 1 FROM {routine_table}
                    WHERE day = %s AND slot_start = %s AND time_slot = 'BREAK'
                """, (day, start))
                if cur.fetchone():
                    routine[day][slot_label] = "Break"

        cur.close()
        conn.close()

        # Prepare table data for PDF
        table_data = [['Day \\ Time'] + slot_labels]
        for day in days_range:
            row = [day]
            for slot in slot_labels:
                cell_content = routine[day][slot]
                if cell_content not in ("Free", "Break"):
                    parts = cell_content.split('\n')
                    simplified = f"{parts[0]} / {parts[1]}"
                    if len(parts) > 2:
                        simplified += f" / {parts[2]}"
                    cell_content = simplified
                row.append(cell_content)
            table_data.append(row)

        # Create PDF table
        pdf_table = Table(table_data)

        # Add style
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        pdf_table.setStyle(style)

        elements.append(pdf_table)
        doc.build(elements)

        buffer.seek(0)
        return Response(
            buffer,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment;filename=routine.pdf"}
        )
