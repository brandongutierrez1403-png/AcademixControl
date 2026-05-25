import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 1. OBTENER LA URL DE CONEXIÓN DE RENDER
# Reemplaza esta cadena de texto por tu "External Connection URI" que te dio Render.
# Se recomienda usar os.environ por seguridad, pero puedes pegarla directo aquí para probar.
DATABASE_URL = os.environ.get('postgresql://academix_db_r3rb_user:rD2KWIPWfbGz1mEzoToh3LGzjFIHMfz8@dpg-d8a7n8ugvqtc73ck5iu0-a.oregon-postgres.render.com/academix_db_r3rb')

def conectar_db():
    # Nos conectamos a Postgres usando la URI de Render
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Tabla de Usuarios (En Postgres usamos SERIAL en lugar de AUTOINCREMENT)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Tabla de Tareas (Ajustada a la sintaxis de Postgres)
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
    print("✅ Base de datos PostgreSQL inicializada en la nube")

# Inicializamos las tablas al arrancar el servidor
init_db()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Datos incompletos"}), 400
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        # En Postgres se usa %s en lugar de ? para pasar parámetros
        cursor.execute('INSERT INTO users (email, password) VALUES (%s, %s)', 
                     (data['email'].lower().strip(), data['password']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "Usuario registrado"}), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "El correo ya existe"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = conectar_db()
    # Usamos RealDictCursor para que nos devuelva el resultado como un diccionario idéntico a sqlite.Row
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', 
                 (data['email'].lower().strip(), data['password']))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user:
        return jsonify({
            "status": "success",
            "user": {"id": user['id'], "email": user['email']}
        })
    return jsonify({"status": "error", "message": "Credenciales inválidas"}), 401

@app.route('/tasks', methods=['GET'])
def get_tasks():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Falta user_id"}), 400
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
        # RETURNING id nos ayuda a saber qué ID autogeneró Postgres de forma segura
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

@app.route('/tasks/<int:id>', methods=['PUT'])
def update_task(id):
    data = request.json
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tasks SET title=%s, subject=%s, teacher=%s, dueDate=%s, dueDateTime=%s, 
            reminderInterval=%s, description=%s, completed=%s WHERE id=%s''',
            (data.get('title'), data.get('subject'), data.get('teacher'), 
             data.get('dueDate'), data.get('dueDateTime'), data.get('reminderInterval'), 
             data.get('description'), data.get('completed'), id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id=%s', (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Modificación clave: app.run adaptado con puerto dinámico para Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)