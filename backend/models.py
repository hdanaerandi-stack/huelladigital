from datetime import datetime
import json

from database import db


# ============================================================
# USUARIOS
# ============================================================

class Usuario(db.Model):

    __tablename__ = "usuarios"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(120),
        nullable=False
    )

    correo = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    telefono = db.Column(
        db.String(20),
        nullable=True
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    rol = db.Column(
        db.String(30),
        nullable=False,
        default="dueno"
    )

    cedula_profesional = db.Column(
        db.String(50),
        nullable=True
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    fecha_registro = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


    def to_dict(self):

        return {
            "id": self.id,
            "nombre": self.nombre,
            "correo": self.correo,
            "telefono": self.telefono,
            "rol": self.rol,
            "cedula_profesional": self.cedula_profesional,
            "activo": self.activo,
            "fecha_registro": (
                self.fecha_registro.isoformat()
                if self.fecha_registro
                else None
            )
        }


# ============================================================
# VERIFICACIÓN PROFESIONAL DEL VETERINARIO
# ============================================================

class VerificacionVeterinario(db.Model):

    __tablename__ = "verificaciones_veterinario"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        unique=True,
        index=True
    )


    estado = db.Column(
        db.String(30),
        nullable=False,
        default="Pendiente"
    )


    revisado_por = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True
    )


    motivo = db.Column(
        db.String(500),
        nullable=True
    )


    fecha_solicitud = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


    fecha_revision = db.Column(
        db.DateTime,
        nullable=True
    )


    def to_dict(self):

        return {

            "id":
                self.id,

            "usuario_id":
                self.usuario_id,

            "estado":
                self.estado,

            "revisado_por":
                self.revisado_por,

            "motivo":
                self.motivo or "",

            "fecha_solicitud":
                (
                    self.fecha_solicitud.isoformat()
                    if self.fecha_solicitud
                    else None
                ),

            "fecha_revision":
                (
                    self.fecha_revision.isoformat()
                    if self.fecha_revision
                    else None
                )

        }


# ============================================================
# CÓDIGOS DE RECUPERACIÓN DE CONTRASEÑA
# ============================================================

class PasswordReset(db.Model):

    __tablename__ = "password_resets"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    metodo = db.Column(
        db.String(20),
        nullable=False
    )

    destino = db.Column(
        db.String(150),
        nullable=False
    )

    codigo_hash = db.Column(
        db.String(255),
        nullable=False
    )

    expira_en = db.Column(
        db.DateTime,
        nullable=False
    )

    usado = db.Column(
        db.Boolean,
        default=False
    )

    creado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


    def to_dict(self):

        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "metodo": self.metodo,
            "destino": self.destino,
            "expira_en": (
                self.expira_en.isoformat()
                if self.expira_en
                else None
            ),
            "usado": self.usado,
            "creado_en": (
                self.creado_en.isoformat()
                if self.creado_en
                else None
            )
        }
        
        
        # ============================================================
# FOTOS DE LAS MASCOTAS
# ============================================================

class FotoMascota(db.Model):

    __tablename__ = "fotos_mascotas"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    mascota_id = db.Column(
        db.Integer,
        db.ForeignKey("mascotas.id"),
        nullable=False,
        index=True
    )

    archivo = db.Column(
        db.String(255),
        nullable=False
    )

    portada = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    orden = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    fecha_subida = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def to_dict(self):

        return {
            "id": self.id,
            "mascota_id": self.mascota_id,
            "archivo": self.archivo,
            "url": self.archivo,
            "portada": bool(self.portada),
            "orden": self.orden,
            "fecha_subida": (
                self.fecha_subida.isoformat()
                if self.fecha_subida
                else None
            )
        }

# ============================================================
# MASCOTAS
# ============================================================

class Mascota(db.Model):


    temperatura = db.Column(
        db.Float,
        nullable=True
    )

    rasgos = db.Column(
        db.String(255),
        nullable=True
    )


    __tablename__ = "mascotas"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    nombre = db.Column(
        db.String(120),
        nullable=False
    )

    especie = db.Column(
        db.String(80),
        nullable=False
    )

    raza = db.Column(
        db.String(120),
        nullable=True
    )

    edad = db.Column(
        db.Float,
        nullable=True
    )

    peso = db.Column(
        db.Float,
        nullable=True
    )
    
    temperatura = db.Column(
        db.Float,
        nullable=True
    )

    rasgos = db.Column(
        db.String(255),
        nullable=True
    )

    sexo = db.Column(
        db.String(30),
        nullable=True
    )

    esterilizacion = db.Column(
        db.String(30),
        nullable=True
    )

    microchip = db.Column(
        db.String(100),
        nullable=True
    )

    huella_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    foto = db.Column(
        db.String(255),
        nullable=True
    )

    fecha_registro = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    actualizado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def to_dict(self):

        return {
                        
            "id": self.id,
            "usuario_id": self.usuario_id,
            "nombre": self.nombre,
            "name": self.nombre,
            "especie": self.especie,
            "species": self.especie,
            "raza": self.raza or "",
            "breed": self.raza or "",
            "edad": self.edad,
            "age": self.edad,
            "peso": self.peso,
            "weight": self.peso,
                        "temperatura": self.temperatura,
            "temperature": self.temperatura,

            "rasgos": self.rasgos or "",
            "traits": self.rasgos or "",
            "sexo": self.sexo or "",
            "sex": self.sexo or "",
            "esterilizacion": self.esterilizacion or "",
            "sterilization": self.esterilizacion or "",
            "microchip": self.microchip or "",
            "huella_id": self.huella_id,
            "huellaId": self.huella_id,
            "foto": self.foto or "",
            "photo": self.foto or "",
            "fecha_registro": (
                self.fecha_registro.isoformat()
                if self.fecha_registro
                else None
            ),
            "actualizado_en": (
                self.actualizado_en.isoformat()
                if self.actualizado_en
                else None
            )
        }


# ============================================================
# DATOS PERSISTENTES DE MÓDULOS POR MASCOTA
# ============================================================

class DatosModuloMascota(db.Model):

    __tablename__ = "datos_modulo_mascota"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    mascota_id = db.Column(
        db.Integer,
        db.ForeignKey("mascotas.id"),
        nullable=False,
        index=True
    )

    modulo = db.Column(
        db.String(60),
        nullable=False,
        index=True
    )

    datos_json = db.Column(
        db.Text,
        nullable=False,
        default="{}"
    )

    actualizado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "usuario_id",
            "mascota_id",
            "modulo",
            name="uq_usuario_mascota_modulo"
        ),
    )
# ============================================================
# MEMBRESÍAS DE USUARIOS
# ============================================================
class Membresia(db.Model):

    __tablename__ = "membresias"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        unique=True,
        index=True
    )

    plan_id = db.Column(
        db.String(30),
        nullable=False
    )

    nombre_plan = db.Column(
        db.String(100),
        nullable=False
    )

    precio = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    moneda = db.Column(
        db.String(10),
        nullable=False,
        default="MXN"
    )

    duracion_dias = db.Column(
        db.Integer,
        nullable=False,
        default=30
    )

    max_mascotas = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    permisos_json = db.Column(
        db.Text,
        nullable=False,
        default="{}"
    )

    beneficios_json = db.Column(
        db.Text,
        nullable=False,
        default="[]"
    )

    metodo_pago = db.Column(
        db.String(50),
        nullable=True
    )

    referencia_pago = db.Column(
        db.String(120),
        nullable=True
    )

    estado_pago = db.Column(
        db.String(30),
        nullable=False,
        default="Pendiente"
    )

    estado = db.Column(
        db.String(30),
        nullable=False,
        default="Activa"
    )

    modo = db.Column(
        db.String(30),
        nullable=False,
        default="sandbox"
    )

    fecha_inicio = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    fecha_expiracion = db.Column(
        db.DateTime,
        nullable=False
    )

    creada_en = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    actualizada_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def to_dict(self):

        try:
            permisos = json.loads(
                self.permisos_json or "{}"
            )
        except Exception:
            permisos = {}

        try:
            beneficios = json.loads(
                self.beneficios_json or "[]"
            )
        except Exception:
            beneficios = []

        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "plan_id": self.plan_id,
            "name": self.nombre_plan,
            "nombre_plan": self.nombre_plan,
            "price": self.precio,
            "currency": self.moneda,
            "days": self.duracion_dias,
            "maxPets": self.max_mascotas,
            "permissions": permisos,
            "features": beneficios,
            "paymentMethod": self.metodo_pago,
            "paymentReference": self.referencia_pago,
            "paymentStatus": self.estado_pago,
            "status": self.estado,
            "mode": self.modo,
            "start": (
                self.fecha_inicio.isoformat()
                if self.fecha_inicio
                else None
            ),
            "expiry": (
                self.fecha_expiracion.isoformat()
                if self.fecha_expiracion
                else None
            )
        }
        
        
        # ============================================================
# PRODUCTOS DEL PROVEEDOR
# ============================================================

class ProductoProveedor(db.Model):

    __tablename__ = "productos_proveedor"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    proveedor_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    nombre = db.Column(
        db.String(160),
        nullable=False
    )

    categoria = db.Column(
        db.String(80),
        nullable=False,
        default="Otro"
    )

    descripcion = db.Column(
        db.Text,
        nullable=True
    )

    precio = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    stock = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    estado = db.Column(
        db.String(30),
        nullable=False,
        default="Activo"
    )

    imagen = db.Column(
        db.String(255),
        nullable=True
    )

    creado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    actualizado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


    def to_dict(self):

        return {

            "id": self.id,

            "proveedor_id":
                self.proveedor_id,

            "nombre":
                self.nombre,

            "categoria":
                self.categoria,

            "descripcion":
                self.descripcion or "",

            "precio":
                float(self.precio or 0),

            "stock":
                int(self.stock or 0),

            "estado":
                self.estado,

            "imagen":
                self.imagen or "",

            "creado_en":
                (
                    self.creado_en.isoformat()
                    if self.creado_en
                    else None
                ),

            "actualizado_en":
                (
                    self.actualizado_en.isoformat()
                    if self.actualizado_en
                    else None
                )

        }


# ============================================================
# PEDIDOS DE LA TIENDA
# ============================================================

class Pedido(db.Model):

    __tablename__ = "pedidos"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    numero = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True
    )

    comprador_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    mascota_id = db.Column(
        db.Integer,
        db.ForeignKey("mascotas.id"),
        nullable=True,
        index=True
    )

    cliente_nombre = db.Column(
        db.String(160),
        nullable=False
    )

    telefono = db.Column(
        db.String(30),
        nullable=True
    )

    correo = db.Column(
        db.String(160),
        nullable=True
    )

    direccion = db.Column(
        db.Text,
        nullable=False
    )

    metodo_pago = db.Column(
        db.String(60),
        nullable=False
    )

    tipo_entrega = db.Column(
        db.String(60),
        nullable=False
    )

    notas = db.Column(
        db.Text,
        nullable=True
    )

    subtotal = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    envio = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    total = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    estado = db.Column(
        db.String(40),
        nullable=False,
        default="Pendiente"
    )

    creado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    actualizado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


    def to_dict(self):

        return {

            "id":
                self.id,

            "numero":
                self.numero,

            "comprador_id":
                self.comprador_id,

            "mascota_id":
                self.mascota_id,

            "cliente_nombre":
                self.cliente_nombre,

            "telefono":
                self.telefono or "",

            "correo":
                self.correo or "",

            "direccion":
                self.direccion,

            "metodo_pago":
                self.metodo_pago,

            "tipo_entrega":
                self.tipo_entrega,

            "notas":
                self.notas or "",

            "subtotal":
                float(
                    self.subtotal or 0
                ),

            "envio":
                float(
                    self.envio or 0
                ),

            "total":
                float(
                    self.total or 0
                ),

            "estado":
                self.estado,

            "creado_en":
                (
                    self.creado_en.isoformat()
                    if self.creado_en
                    else None
                ),

            "actualizado_en":
                (
                    self.actualizado_en.isoformat()
                    if self.actualizado_en
                    else None
                )

        }


# ============================================================
# DETALLE DE PRODUCTOS DE CADA PEDIDO
# ============================================================

class DetallePedido(db.Model):

    __tablename__ = "detalles_pedido"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=False,
        index=True
    )

    producto_id = db.Column(
        db.Integer,
        db.ForeignKey("productos_proveedor.id"),
        nullable=False,
        index=True
    )

    proveedor_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    nombre_producto = db.Column(
        db.String(160),
        nullable=False
    )

    precio_unitario = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    cantidad = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    subtotal = db.Column(
        db.Float,
        nullable=False,
        default=0
    )


    def to_dict(self):

        return {

            "id":
                self.id,

            "pedido_id":
                self.pedido_id,

            "producto_id":
                self.producto_id,

            "proveedor_id":
                self.proveedor_id,

            "nombre_producto":
                self.nombre_producto,

            "precio_unitario":
                float(
                    self.precio_unitario or 0
                ),

            "cantidad":
                int(
                    self.cantidad or 0
                ),

            "subtotal":
                float(
                    self.subtotal or 0
                )

        }
        
        
        # ============================================================
# VINCULACIÓN VETERINARIO - MASCOTA
# ============================================================

class VinculoVeterinarioMascota(db.Model):

    __tablename__ = "vinculos_veterinario_mascota"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    veterinario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )


    propietario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )


    mascota_id = db.Column(
        db.Integer,
        db.ForeignKey("mascotas.id"),
        nullable=False,
        index=True
    )


    estado = db.Column(
        db.String(30),
        nullable=False,
        default="Pendiente"
    )


    fecha_solicitud = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


    fecha_vinculacion = db.Column(
        db.DateTime,
        nullable=True
    )


    creado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


    actualizado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


    __table_args__ = (

        db.UniqueConstraint(
            "veterinario_id",
            "mascota_id",
            name="uq_veterinario_mascota"
        ),

    )


    def to_dict(self):

        return {

            "id":
                self.id,

            "veterinario_id":
                self.veterinario_id,

            "propietario_id":
                self.propietario_id,

            "mascota_id":
                self.mascota_id,

            "estado":
                self.estado,

            "fecha_solicitud":
                (
                    self.fecha_solicitud.isoformat()
                    if self.fecha_solicitud
                    else None
                ),

            "fecha_vinculacion":
                (
                    self.fecha_vinculacion.isoformat()
                    if self.fecha_vinculacion
                    else None
                )

        }
        
        
  # ============================================================
# PERFIL COMERCIAL DEL PROVEEDOR
# ============================================================

class PerfilProveedor(db.Model):

    __tablename__ = "perfiles_proveedor"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    proveedor_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        unique=True,
        index=True
    )


    nombre_comercial = db.Column(
        db.String(150),
        nullable=False,
        default="Mi comercio Huella"
    )


    categoria = db.Column(
        db.String(100),
        nullable=True
    )


    telefono = db.Column(
        db.String(30),
        nullable=True
    )


    correo = db.Column(
        db.String(150),
        nullable=True
    )


    ubicacion = db.Column(
        db.String(180),
        nullable=True
    )


    direccion = db.Column(
        db.String(255),
        nullable=True
    )


    descripcion = db.Column(
        db.Text,
        nullable=True
    )


    logo = db.Column(
        db.Text,
        nullable=True
    )


    horario_semana = db.Column(
        db.String(80),
        nullable=True,
        default="09:00 - 18:00"
    )


    horario_sabado = db.Column(
        db.String(80),
        nullable=True,
        default="10:00 - 15:00"
    )


    horario_domingo = db.Column(
        db.String(80),
        nullable=True,
        default="Cerrado"
    )


    entrega_domicilio = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )


    recoger_tienda = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )


    pago_electronico = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )


    notificaciones = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )


    creado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


    actualizado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


    def to_dict(self):

        return {

            "id":
                self.id,

            "proveedor_id":
                self.proveedor_id,

            "nombre":
                self.nombre_comercial,

            "nombre_comercial":
                self.nombre_comercial,

            "categoria":
                self.categoria or "",

            "telefono":
                self.telefono or "",

            "correo":
                self.correo or "",

            "ubicacion":
                self.ubicacion or "",

            "direccion":
                self.direccion or "",

            "descripcion":
                self.descripcion or "",

            "logo":
                self.logo or "",

            "horarioSemana":
                self.horario_semana or "",

            "horarioSabado":
                self.horario_sabado or "",

            "horarioDomingo":
                self.horario_domingo or "",

            "entrega":
                bool(
                    self.entrega_domicilio
                ),

            "recoger":
                bool(
                    self.recoger_tienda
                ),

            "pagoElectronico":
                bool(
                    self.pago_electronico
                ),

            "notificaciones":
                bool(
                    self.notificaciones
                ),

            "creado_en":
                (
                    self.creado_en.isoformat()
                    if self.creado_en
                    else None
                ),

            "actualizado_en":
                (
                    self.actualizado_en.isoformat()
                    if self.actualizado_en
                    else None
                )

        }      