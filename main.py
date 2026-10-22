from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# 1. Configuración de Supabase (¡Reemplaza con tus datos!)
SUPABASE_URL = "https://hlbjtodafnvnobfbzien.supabase.co"
SUPABASE_KEY = "sb_publishable_1wTYMhh-31D5lEgF1PoSDg_KsK9TLjf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Inicializar FastAPI
app = FastAPI()

# --- CONFIGURACIÓN DE SEGURIDAD (CORS) ---
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://fanciful-khapse-2b0c3b.netlify.app"  # <--- TU NUEVO LINK PÚBLICO
]

# 3. Configurar CORS (Crucial para que la tablet HTML pueda hablar con Python sin bloqueos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Definir cómo debe verse un Pedido (Validación)
class Pedido(BaseModel):
    mesa: str
    mesero: str = "Tablet 1"
    detalle_pedido: list # Aquí vendrá el arreglo de sushis y cortes
    total: float

# --- ENDPOINTS (Las rutas de tu servidor) ---

@app.get("/")
def leer_raiz():
    return {"mensaje": "Bienvenido al servidor de OptiBiz"}

@app.get("/productos")
def obtener_menu():
    """Devuelve todos los productos disponibles para mostrarlos en la tablet"""
    try:
        respuesta = supabase.table("productos").select("*").eq("disponible", True).execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/modificadores")
def get_modificadores():
    # Traemos los modificadores buscando específicamente por grupo
    response = supabase.table("modificadores").select("*").eq("grupo", "Extras").execute()
    return response.data

@app.post("/pedidos")
def crear_pedido(pedido: Pedido):
    """Recibe la orden de la tablet y la guarda en Supabase"""
    try:
        nuevo_pedido = {
            "mesa": pedido.mesa,
            "mesero": pedido.mesero,
            "detalle_pedido": pedido.detalle_pedido,
            "total": pedido.total,
            "estado": "pendiente"
        }
        # Insertar en Supabase
        respuesta = supabase.table("pedidos").insert(nuevo_pedido).execute()
        
        # Al insertar, Supabase gritará por Realtime a la cocina automáticamente
        return {"mensaje": "Pedido enviado a cocina", "datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
