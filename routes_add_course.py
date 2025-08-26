from flask import render_template, request, redirect, url_for, session
from db import get_db_connection

def init_add_course_routes(app):
    @app.route("/add", methods=["GET", "POST"])
    def add_course():
        if "branch" not in session:
            return redirect(url_for("select_details"))

        courses_table = session["courses_table"]

        if request.method == "POST":
            teacher_name = request.form["teacher_name"]
            course_name = request.form["course_name"]
            course_code = request.form["course_code"]
            tutorial_time = request.form.get("tutorial_time", "").strip() or None
            lab_time = request.form.get("lab_time", "").strip() or None
            tutorials_per_week = int(request.form.get("tutorials_per_week", 0))
            labs_per_week = int(request.form.get("labs_per_week", 0))

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO {courses_table} 
                (teacher_name, course_name, course_code, tutorial_time, lab_time, tutorials_per_week, labs_per_week) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (teacher_name, course_name, course_code, tutorial_time, lab_time, tutorials_per_week, labs_per_week)
            )
            conn.commit()
            cur.close()
            conn.close()

            if "next" in request.form:
                return redirect(url_for("add_course"))
            elif "exit" in request.form:
                return redirect(url_for("view_courses"))

        return render_template(
            "teacher_information.html",
            branch=session["branch"],
            semester=session["semester"],
            year=session["year"]
        )