from flask import Flask, request, jsonify, render_template_string, send_from_directory, render_template
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import secrets
import hashlib
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
CORS(app)

# Configuración de base de datos (ajustar con tus datos de SiteGround)
DB_CONFIG = {
    'host': 'localhost',         # o la IP de tu servidor MySQL
    'database': 'cuestionario',  # el nombre de tu base de datos
    'user': 'root',        # tu usuario de MySQL
    'password': ''    # tu contraseña de MySQL
}

def get_db_connection():
    """Crear conexión a la base de datos"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def generar_codigo_acceso():
    """Generar código único de acceso"""
    return f"PROF{secrets.randbelow(9999):04d}"

def verificar_codigo_acceso(codigo):
    """Verificar si el código de acceso es válido"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM profesores WHERE codigo_acceso = %s", (codigo,))
            profesor = cursor.fetchone()
            return profesor
        except Error as e:
            print(f"Error verificando código: {e}")
            return None
        finally:
            connection.close()
    return None

@app.route('/')
def index():
    """Página principal de login"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cuestionario - Acceso</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; }
            .container { border: 1px solid #ddd; padding: 30px; border-radius: 8px; }
            input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
            button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .error { color: red; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Acceso al Cuestionario</h2>
            <form id="loginForm">
                <input type="text" id="codigo" placeholder="Ingrese su código de acceso" required>
                <button type="submit">Ingresar</button>
                <div id="error" class="error"></div>
            </form>
        </div>
        
        <script>
        document.getElementById('loginForm').onsubmit = function(e) {
            e.preventDefault();
            const codigo = document.getElementById('codigo').value;
            
            fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({codigo: codigo})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    localStorage.setItem('token', data.token);
                    window.location.href = '/cuestionario';
                } else {
                    document.getElementById('error').textContent = data.message;
                }
            });
        }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    # Cambia 'codigo_acceso' por 'codigo'
    codigo = data.get('codigo')

    # Código único para el colegio
    if codigo == 'colegio2025':
        return jsonify({'success': True, 'token': 'colegio2025'})
    else:
        return jsonify({'success': False, 'message': 'Código incorrecto'})

@app.route('/api/preguntas', methods=['GET'])
def obtener_preguntas():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # Valida solo el token general
    if token != 'colegio2025':
        return jsonify({'success': False, 'message': 'Token inválido'})
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute('SELECT * FROM preguntas WHERE activa = 1 ORDER BY orden')
            preguntas = cursor.fetchall()
            for pregunta in preguntas:
                if pregunta['opciones']:
                    pregunta['opciones'] = json.loads(pregunta['opciones'])
            return jsonify({'success': True, 'preguntas': preguntas})
        except Error as e:
            print(f"Error obteniendo preguntas: {e}")
            return jsonify({'success': False, 'message': 'Error del servidor'})
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Error de conexión'})

@app.route('/api/respuestas', methods=['POST'])
def guardar_respuestas():
    data = request.get_json()
    respuestas = data.get('respuestas')
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    # Valida solo el token general
    if not token:
        return jsonify({'success': False, 'message': 'Token inválido'})

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Guarda las respuestas asociadas al colegio
            for pregunta_id, respuesta in respuestas.items():
                cursor.execute('''
                    INSERT INTO respuestas (colegio, pregunta_id, respuesta)
                    VALUES (%s, %s, %s)
                ''', (token, pregunta_id, respuesta))
            connection.commit()
            return jsonify({'success': True, 'message': 'Respuestas guardadas correctamente'})
        except Error as e:
            print(f"Error guardando respuestas: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Error guardando respuestas'})
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Error de conexión'})

# Función para agregar profesores (útil para administración)
@app.route('/admin/agregar_profesor', methods=['POST'])
def agregar_profesor():
    """Endpoint para agregar profesores (usar con cuidado en producción)"""
    data = request.get_json()
    nombre = data.get('nombre')
    email = data.get('email')
    codigo = generar_codigo_acceso()
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute('''
                INSERT INTO profesores (nombre, email, codigo_acceso) 
                VALUES (%s, %s, %s)
            ''', (nombre, email, codigo))
            connection.commit()
            
            return jsonify({
                'success': True, 
                'codigo': codigo,
                'message': f'Profesor agregado con código: {codigo}'
            })
            
        except Error as e:
            print(f"Error agregando profesor: {e}")
            return jsonify({'success': False, 'message': 'Error agregando profesor'})
        finally:
            connection.close()
    
    return jsonify({'success': False, 'message': 'Error de conexión'})

@app.route('/cuestionario')
def cuestionario():
    return render_template('cuestionario.html')

if __name__ == '__main__':
    app.run(debug=True)

# Asegúrate de tener instaladas las dependencias:
# pip install flask flask-cors mysql-connector-python