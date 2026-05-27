import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Obtener la URL de conexión desde las variables de entorno de Render
DATABASE_URL = os.environ.get('DATABASE_URL')

def conectar_db():
    try:
        # Aseguramos que la URL use el formato correcto para psycopg2
        conn_str = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(conn_str)
    except Exception as e:
        print(f"Error crítico de conexión a DB: {e}")
        return None

def init_db():
    conn = conectar_db()
    if not conn: return
    cursor = conn.cursor()
    
    # Crear tablas necesarias para Academix
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            title TEXT NOT NULL,
            subject TEXT,
            teacher TEXT,
            dueDate TEXT,
            dueDateTime TEXT,
            reminderInterval INTEGER,
            description TEXT,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Base de datos inicializada correctamente")

# Inicializar tablas al arrancar
init_db()

# --- RUTAS ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (email, password) VALUES (%s, %s)', 
                     (data['email'].lower().strip(), data['password']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "Usuario registrado"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = conectar_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', 
                 (data['email'].lower().strip(), data['password']))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user:
        return jsonify({"status": "success", "user": {"id": user['id'], "email": user['email']}})
    return jsonify({"status": "error", "message": "Credenciales inválidas"}), 401

@app.route('/tasks', methods=['GET'])
def get_tasks():
    user_id = request.args.get('user_id')
    conn = conectar_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM tasks WHERE user_id = %s', (user_id,))
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.json
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (user_id, title, subject, teacher, dueDate, dueDateTime, 
                             reminderInterval, description, completed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0) RETURNING id''',
            (data.get('user_id'), data.get('title'), data.get('subject'), 
             data.get('teacher'), data.get('dueDate'), data.get('dueDateTime'), 
             data.get('reminderInterval'), data.get('description')))
        conn.commit()
        nuevo_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({"id": nuevo_id, "status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tasks/<int:id>', methods=['PUT', 'DELETE'])
def manage_task(id):
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'PUT':
        data = request.json
        cursor.execute('''UPDATE tasks SET title=%s, completed=%s WHERE id=%s''',
                       (data.get('title'), data.get('completed'), id))
    else:
        cursor.execute('DELETE FROM tasks WHERE id=%s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"})

# NOTA: Gunicorn se encargará de ejecutar esto en Render, 
# por lo que no es necesario el if __name__ == '__main__' con app.run aquí.