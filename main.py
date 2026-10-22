from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import uuid

# 1. Configuración de Supabase
SUPABASE_URL = "https://hlbjtodafnvnobfbzien.supabase.co"
SUPABASE_KEY = "sb_publishable_1wTYMhh-31D5lEgF1PoSDg_KsK9TLjf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Inicializar FastAPI
app = FastAPI()

# 3. Configurar CORS (Usamos "*" para que no te bloquee al probar en local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Permite peticiones de Netlify y de tu compu local
    allow_credentials=False,  # Debe ser False cuando usamos "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Modelos de Datos (Validación)
class Pedido(BaseModel):
    mesa: str
    mesero: str = "Tablet 1"
    detalle_pedido: list 
    total: float

class Extra(BaseModel):
    nombre: str
    precio_extra: float
    grupo: str = "Extras"


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
    """Trae los modificadores buscando específicamente por grupo"""
    try:
        response = supabase.table("modificadores").select("*").eq("grupo", "Extras").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        respuesta = supabase.table("pedidos").insert(nuevo_pedido).execute()
        return {"mensaje": "Pedido enviado a cocina", "datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/productos")
async def crear_producto(
    nombre: str = Form(...),
    precio: float = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form(""),  # <--- Recibimos la descripción desde admin.html
    imagen: UploadFile = File(None)
):
    """Sube la foto a Storage y crea el producto en la base de datos"""
    try:
        url_imagen = ""
        if imagen:
            # 1. Generar un nombre único para la foto
            extension = imagen.filename.split('.')[-1]
            nombre_archivo = f"{uuid.uuid4()}.{extension}"
            
            # 2. Leer la imagen
            file_bytes = await imagen.read()
            
            # 3. Subir la imagen al bucket 'menu'
            supabase.storage.from_("menu").upload(
                path=nombre_archivo,
                file=file_bytes,
                file_options={"content-type": imagen.content_type}
            )
            
            # 4. Obtener el link público de la foto
            url_imagen = supabase.storage.from_("menu").get_public_url(nombre_archivo)
        
        # 5. Guardar el platillo en la base de datos (con descripción)
        nuevo_producto = {
            "nombre": nombre,
            "precio": precio,
            "categoria": categoria,
            "descripcion": descripcion,  # <--- Se guarda en tu nueva columna
            "url_imagen": url_imagen,
            "disponible": True
        }
        respuesta = supabase.table("productos").insert(nuevo_producto).execute()
        
        return {"mensaje": "Producto creado con éxito", "producto": respuesta.data[0]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/modificadores")
def crear_extra(extra: Extra):
    """Guarda un nuevo extra/modificador en la base de datos"""
    try:
        nuevo_modificador = {
            "nombre": extra.nombre,
            "precio_extra": extra.precio_extra,
            "grupo": extra.grupo
        }
        respuesta = supabase.table("modificadores").insert(nuevo_modificador).execute()
        return {"mensaje": "Extra creado con éxito"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
