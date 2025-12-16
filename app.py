import os
from flask import Flask, request, jsonify
from flask_cors import CORS
# === CAMBIO IMPORTANTE: USAMOS LAS LIBRERÍAS NUEVAS ===
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# Obtener API Key de Render
groq_api_key = os.getenv("GROQ_API_KEY")

# Variable global para el cerebro
qa_chain = None

def iniciar_bot():
    global qa_chain
    try:
        print("🔄 Iniciando configuración del bot...")
        
        if not groq_api_key:
            print("❌ ERROR: Falta la GROQ_API_KEY en las variables de entorno.")
            return

        # 1. Configurar LLM (Groq)
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192"
        )

        # 2. Configurar Embeddings (Igual que en crear_memoria.py)
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # 3. Cargar la Memoria (ChromaDB)
        if os.path.exists("./chroma_db"):
            print("📂 Carpeta de memoria encontrada. Conectando...")
            vectorstore = Chroma(
                persist_directory="./chroma_db",
                embedding_function=embeddings
            )
            
            # Crear el recuperador (Retriever)
            retriever = vectorstore.as_retriever()

            # 4. Crear la cadena de preguntas y respuestas
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=False
            )
            print("✅ ¡Cerebro cargado y listo!")
        else:
            print("⚠️ ADVERTENCIA: No se encontró la carpeta 'chroma_db'. El bot no tendrá memoria.")

    except Exception as e:
        print(f"❌ Error crítico al iniciar: {str(e)}")

# Iniciamos el bot al arrancar la app
iniciar_bot()

@app.route('/chat', methods=['POST'])
def chat():
    global qa_chain
    data = request.json
    mensaje_usuario = data.get('mensaje')

    if not mensaje_usuario:
        return jsonify({"respuesta": "Por favor escribe algo."})

    if not qa_chain:
        # Si el cerebro falló al inicio, intentamos ver qué pasó
        return jsonify({"respuesta": "Error técnico: El cerebro del bot no pudo cargar. Revisa los Logs de Render para ver el error exacto."})

    try:
        # Generar respuesta
        print(f"📩 Pregunta recibida: {mensaje_usuario}")
        respuesta = qa_chain.invoke({"query": mensaje_usuario})
        return jsonify({"respuesta": respuesta['result']})
    except Exception as e:
        print(f"❌ Error al responder: {e}")
        return jsonify({"respuesta": "Lo siento, tuve un error interno al procesar tu pregunta."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
