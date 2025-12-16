import os
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN DE LA BASE DE DATOS (NUBE) ---
# Pega aquí el enlace que copiaste de Neon. ¡Que quede dentro de las comillas!
DATABASE_URL = "psql 'postgresql://neondb_owner:npg_lWMe56tsiFzJ@ep-fancy-morning-ad7g2g9d-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'"

def obtener_db_connection():
    try:
        # Nos conectamos a la nube usando el enlace
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print("❌ Error conectando a la base de datos:", e)
        return None

# --- FUNCIONES DEL BOT ---
def obtener_respuesta_inteligente(mensaje_usuario):
    conn = obtener_db_connection()
    if not conn:
        return "Error de conexión con la memoria."
    
    try:
        cur = conn.cursor()
        # Primero intentamos instalar la extensión de trigramas por si no está
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        except:
            conn.rollback() # Si falla (por permisos), seguimos igual
        
        # Búsqueda inteligente
        query = """
        SELECT respuesta, similarity(keywords, %s) as coincidencia
        FROM conocimientos
        ORDER BY coincidencia DESC
        LIMIT 1;
        """
        cur.execute(query, (mensaje_usuario,))
        resultado = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if resultado and resultado[1] > 0.05:
            return resultado[0]
        else:
            return "Lo siento, no tengo información sobre eso. ¿Podrías preguntar de otra forma?"
            
    except Exception as e:
        print("Error en búsqueda:", e)
        if conn: conn.close()
        return "Error técnico."

def guardar_historial(pregunta, respuesta):
    conn = obtener_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        query = "INSERT INTO historial_consultas (pregunta, respuesta) VALUES (%s, %s)"
        cur.execute(query, (pregunta, respuesta))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("No se pudo guardar historial:", e)

# --- RUTA DEL CHAT ---
@app.route('/chat', methods=['POST'])
def chat():
    datos = request.json
    mensaje = datos.get('mensaje', '').lower()
    respuesta_final = ""

    # 1. Saludos
    saludos = ['hola', 'buen dia', 'buenas', 'que tal']
    if any(p in mensaje for p in saludos):
        respuesta_final = "¡Hola! 👋 Soy UniBot. ¿En qué puedo ayudarte?"
    else:
        # 2. Búsqueda
        respuesta_final = obtener_respuesta_inteligente(mensaje)

    # 3. Guardar
    guardar_historial(mensaje, respuesta_final)
    
    return jsonify({"respuesta": respuesta_final})

if __name__ == '__main__':
    # Esto permite que Render nos asigne el puerto automáticamente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)