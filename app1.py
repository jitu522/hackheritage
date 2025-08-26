from flask import Flask

app = Flask(__name__)
app.secret_key = "your_secret_key_here_change_in_production"

# Import and register routes
from routes_select import init_select_routes
from routes_add_course import init_add_course_routes
from routes_view_courses import init_view_courses_routes
from routes_time_slots import init_time_slots_routes
from routes_assign_courses import init_assign_courses_routes
from routes_classrooms import init_classroom_routes
from routes_view_routine import init_view_routine_routes
from routes_exit import init_exit_routes

# Initialize routes
init_select_routes(app)
init_add_course_routes(app)
init_view_courses_routes(app)
init_time_slots_routes(app)
init_assign_courses_routes(app)
init_classroom_routes(app)
init_view_routine_routes(app)
init_exit_routes(app)

if __name__ == "__main__":
    app.run(debug=False)  # Set to False in production