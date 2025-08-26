from db import get_db_connection

def init_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create courses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            teacher_name VARCHAR(100) NOT NULL,
            course_name VARCHAR(100) NOT NULL,
            course_code VARCHAR(50) NOT NULL,
            tutorial_time VARCHAR(20) NULL,
            lab_time VARCHAR(20) NULL,
            tutorials_per_week INT DEFAULT 0,
            labs_per_week INT DEFAULT 0
        )
    """)
    
    # Create routine table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routine_table (
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
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_tables()