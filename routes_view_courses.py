from flask import render_template, redirect, url_for, session
from db import get_db_connection

def init_view_courses_routes(app):
    @app.route("/view-courses")
    def view_courses():
        if "branch" not in session:
            return redirect(url_for("select_details"))

        courses_table = session["courses_table"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"""
            SELECT teacher_name, course_name, course_code, tutorial_time, lab_time, tutorials_per_week, labs_per_week
            FROM {courses_table}
        """)
        courses = cur.fetchall()
        cur.close()
        conn.close()

        return render_template(
            "teacher_information_show.html",
            branch=session["branch"],
            semester=session["semester"],
            year=session["year"],
            courses=courses
        )