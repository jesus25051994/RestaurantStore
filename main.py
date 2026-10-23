from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime
import uuid

# 1. Configuración de Supabase (¡Pon tus datos reales aquí!)
SUPABASE_URL = "https://hlbjtodafnvnobfbzien.supabase.co"
SUPABASE_KEY = "sb_publishable_1wTYMhh-31D5lEgF1PoSDg_KsK9TLjf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Inicializar FastAPI
app = FastAPI()

# 3. Configurar CORS (Esto permite que trabajes en Local sin problemas)
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

# --- RUTAS DE PRODUCTOS ---
@app.get("/productos")
def obtener_menu():
    try:
        respuesta = supabase.table("productos").select("*").eq("disponible", True).execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/productos")
def obtener_todos_productos():
    try:
        respuesta = supabase.table("productos").select("*").order("categoria").execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/productos")
async def crear_producto(
    nombre: str = Form(...), precio: float = Form(...), categoria: str = Form(...),
    descripcion: str = Form(""), imagen: UploadFile = File(None)
):
    try:
        url_imagen = ""
        if imagen and imagen.filename:
            extension = imagen.filename.split('.')[-1]
            nombre_archivo = f"{uuid.uuid4()}.{extension}"
            file_bytes = await imagen.read()
            supabase.storage.from_("menu").upload(
                path=nombre_archivo, file=file_bytes, file_options={"content-type": imagen.content_type}
            )
            url_imagen = supabase.storage.from_("menu").get_public_url(nombre_archivo)
        
        nuevo_producto = {
            "nombre": nombre, "precio": precio, "categoria": categoria,
            "descripcion": descripcion, "url_imagen": url_imagen, "disponible": True
        }
        respuesta = supabase.table("productos").insert(nuevo_producto).execute()
        return {"mensaje": "Producto creado", "producto": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/productos/{producto_id}")
async def actualizar_producto(
    producto_id: str, nombre: str = Form(...), precio: float = Form(...),
    categoria: str = Form(...), descripcion: str = Form(""), imagen: UploadFile = File(None)
):
    try:
        datos = {"nombre": nombre, "precio": precio, "categoria": categoria, "descripcion": descripcion}
        if imagen and imagen.filename:
            extension = imagen.filename.split('.')[-1]
            nombre_archivo = f"{uuid.uuid4()}.{extension}"
            file_bytes = await imagen.read()
            supabase.storage.from_("menu").upload(
                path=nombre_archivo, file=file_bytes, file_options={"content-type": imagen.content_type}
            )
            datos["url_imagen"] = supabase.storage.from_("menu").get_public_url(nombre_archivo)
            
        respuesta = supabase.table("productos").update(datos).eq("id", producto_id).execute()
        return {"mensaje": "Producto actualizado", "producto": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/productos/{producto_id}/estado")
def cambiar_estado_producto(producto_id: str, estado: dict):
    try:
        respuesta = supabase.table("productos").update({"disponible": estado["disponible"]}).eq("id", producto_id).execute()
        return {"mensaje": "Estado actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- RUTAS DE EXTRAS ---
@app.get("/modificadores")
def get_modificadores():
    try:
        response = supabase.table("modificadores").select("*").eq("grupo", "Extras").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/modificadores")
def crear_extra(extra: Extra):
    try:
        nuevo_modificador = {"nombre": extra.nombre, "precio_extra": extra.precio_extra, "grupo": extra.grupo}
        respuesta = supabase.table("modificadores").insert(nuevo_modificador).execute()
        return {"mensaje": "Extra creado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- RUTAS DE PEDIDOS (COCINA Y POS) ---
@app.post("/pedidos")
def crear_pedido(pedido: Pedido):
    try:
        nuevo_pedido = {
            "mesa": pedido.mesa, "mesero": pedido.mesero, "detalle_pedido": pedido.detalle_pedido,
            "total": pedido.total, "estado": "pendiente"
        }
        respuesta = supabase.table("pedidos").insert(nuevo_pedido).execute()
        return {"mensaje": "Pedido enviado a cocina", "datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pedidos/pendientes")
def obtener_pedidos_pendientes():
    try:
        respuesta = supabase.table("pedidos").select("*").eq("estado", "pendiente").order("created_at").execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/pedidos/{pedido_id}/estado")
def actualizar_estado_pedido(pedido_id: str, estado_data: dict):
    try:
        respuesta = supabase.table("pedidos").update({"estado": estado_data["estado"]}).eq("id", pedido_id).execute()
        return {"mensaje": "Pedido completado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- NUEVAS RUTAS PARA LA CUENTA ---

@app.get("/cuenta/{mesa}")
def obtener_cuenta_mesa(mesa: str):
    """Suma todos los pedidos de una mesa que aún NO han sido pagados"""
    try:
        # Buscamos todo lo de esa mesa que no esté 'pagado' (puede estar 'pendiente' o 'completado' por cocina)
        respuesta = supabase.table("pedidos").select("*").eq("mesa", mesa).neq("estado", "pagado").execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/cuenta/{mesa}/pagar")
def cobrar_mesa(mesa: str):
    """Marca todos los pedidos activos de la mesa como 'pagado' para limpiar la cuenta"""
    try:
        respuesta = supabase.table("pedidos").update({"estado": "pagado"}).eq("mesa", mesa).neq("estado", "pagado").execute()
        return {"mensaje": f"Mesa cobrada con éxito"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- RUTAS DE NOTIFICACIONES (LLAMAR AL MESERO) ---
class Notificacion(BaseModel):
    mesa: str
    mensaje: str = "Solicita la cuenta"

@app.post("/notificaciones")
def llamar_mesero(notif: Notificacion):
    try:
        nueva_alerta = {"mesa": notif.mesa, "mensaje": notif.mensaje, "leido": False}
        supabase.table("notificaciones").insert(nueva_alerta).execute()
        return {"mensaje": "Mesero notificado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/notificaciones/{notif_id}/leido")
def marcar_notificacion_leida(notif_id: str):
    try:
        supabase.table("notificaciones").update({"leido": True}).eq("id", notif_id).execute()
        return {"mensaje": "Alerta atendida"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- RUTA PARA EL CORTE DE CAJA (DASHBOARD GERENCIAL) ---
@app.get("/pedidos_dia")
def obtener_pedidos_del_dia():
    try:
        # 1. Obtener la fecha exacta del inicio del día (00:00:00)
        hoy = datetime.now()
        inicio_dia = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 2. Convertir a formato ISO para que Supabase lo entienda
        inicio_dia_iso = inicio_dia.isoformat()

        # 3. Pedir a Supabase todos los registros desde el inicio del día hasta este momento
        respuesta = supabase.table("pedidos").select("*").gte("created_at", inicio_dia_iso).execute()
        
        # 4. Devolver la lista al Frontend (corte.html)
        return respuesta.data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
