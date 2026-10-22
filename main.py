from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import uuid

# 1. Configuración de Supabase (¡Pon tus datos aquí!)
SUPABASE_URL = "TU_URL_AQUI"
SUPABASE_KEY = "TU_KEY_AQUI"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Inicializar FastAPI
app = FastAPI()

# 3. Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Modelos de Datos
class Pedido(BaseModel):
    mesa: str
    mesero: str = "Tablet 1"
    detalle_pedido: list 
    total: float

class Extra(BaseModel):
    nombre: str
    precio_extra: float
    grupo: str = "Extras"

@app.get("/")
def leer_raiz():
    return {"mensaje": "Bienvenido al servidor de OptiBiz"}

@app.get("/productos")
def obtener_menu():
    try:
        respuesta = supabase.table("productos").select("*").eq("disponible", True).execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---> ¡ESTA ES LA RUTA QUE FALTABA PARA LEER LOS EXTRAS! <---
@app.get("/modificadores")
def get_modificadores():
    try:
        response = supabase.table("modificadores").select("*").eq("grupo", "Extras").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pedidos")
def crear_pedido(pedido: Pedido):
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
    descripcion: str = Form(""),
    imagen: UploadFile = File(None)
):
    try:
        url_imagen = ""
        if imagen:
            extension = imagen.filename.split('.')[-1]
            nombre_archivo = f"{uuid.uuid4()}.{extension}"
            file_bytes = await imagen.read()
            
            supabase.storage.from_("menu").upload(
                path=nombre_archivo,
                file=file_bytes,
                file_options={"content-type": imagen.content_type}
            )
            url_imagen = supabase.storage.from_("menu").get_public_url(nombre_archivo)
        
        nuevo_producto = {
            "nombre": nombre,
            "precio": precio,
            "categoria": categoria,
            "descripcion": descripcion,
            "url_imagen": url_imagen,
            "disponible": True
        }
        respuesta = supabase.table("productos").insert(nuevo_producto).execute()
        return {"mensaje": "Producto creado con éxito", "producto": respuesta.data[0]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---> Y ESTA ES LA RUTA PARA GUARDARLOS <---
@app.post("/modificadores")
def crear_extra(extra: Extra):
    try:
        nuevo_modificador = {
            "nombre": extra.nombre,
            "precio_extra": extra.precio_extra,
            "grupo": extra.grupo
        }
        respuesta = supabase.table("modificadores").insert(nuevo_modificador).execute()
        return {"mensaje": "Extra creado con éxito"}
    except Exception as e:
        print(f"⚠️ ERROR DE SUPABASE AL GUARDAR EXTRA: {e}") 
        raise HTTPException(status_code=500, detail=str(e))
