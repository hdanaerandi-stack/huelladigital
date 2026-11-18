
# ============================================================
# IMPORTS
# ============================================================

from flask import (
    Flask,
    jsonify,
    send_from_directory,
    request,
    session,
    redirect,
    url_for
)

from flask_socketio import (
    SocketIO,
    join_room,
    leave_room,
    emit
)

from pathlib import Path

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

import os
import re
import secrets
import uuid
import json
import stripe
import requests

from datetime import (
    datetime,
    timedelta
)

from dotenv import load_dotenv

import resend
import secrets

from twilio.rest import Client

from database import db

from models import (
    Usuario,
    PasswordReset,
    Mascota,
    FotoMascota,
    DatosModuloMascota,
    Membresia,
    VinculoVeterinarioMascota,
    ProductoProveedor,
    Pedido,
    DetallePedido,
    PerfilProveedor,
    VerificacionVeterinario
)


from bird import (
    Bird,
    APIError
)

from authlib.integrations.flask_client import OAuth

from ia_video import (
    preparar_proyecto_video,
    generar_video_ia
)



# ============================================================
# CARPETA PRINCIPAL
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


BACKEND_DIR = Path(__file__).resolve().parent


load_dotenv(
    BASE_DIR / ".env"
)
print("BASE_DIR REAL:")
print(BASE_DIR)

print("INDEX QUE FLASK ESTÃ USANDO:")
print(BASE_DIR / "index.html")





# ============================================================
# RESEND
# ============================================================

resend.api_key = os.environ.get(
    "RESEND_API_KEY"
)


EMAIL_FROM = os.environ.get(
    "EMAIL_FROM",
    "Huella <onboarding@resend.dev>"
)


# ============================================================
# BIRD
# ============================================================

BIRD_API_KEY = os.environ.get("BIRD_API_KEY", "").strip()

bird_client = (
    Bird(api_key=BIRD_API_KEY)
    if BIRD_API_KEY
    else None
)


# ============================================================
# STRIPE
# ============================================================

stripe.api_key = os.environ.get(
    "STRIPE_SECRET_KEY",
    ""
)


STRIPE_PUBLISHABLE_KEY = os.environ.get(
    "STRIPE_PUBLISHABLE_KEY",
    ""
)


# ============================================================
# TWILIO
# ============================================================

TWILIO_ACCOUNT_SID = os.environ.get(
    "TWILIO_ACCOUNT_SID",
    ""
)


TWILIO_AUTH_TOKEN = os.environ.get(
    "TWILIO_AUTH_TOKEN",
    ""
)


TWILIO_VERIFY_SERVICE_SID = os.environ.get(
    "TWILIO_VERIFY_SERVICE_SID",
    ""
)


TWILIO_PHONE_NUMBER = os.environ.get(
    "TWILIO_PHONE_NUMBER",
    ""
)


# ============================================================
# URL PÃšBLICA
# ============================================================

HUELLA_PUBLIC_URL = os.environ.get(
    "HUELLA_PUBLIC_URL",
    ""
).rstrip("/")


# ============================================================
# CLIENTE TWILIO
# ============================================================
def get_twilio_client():

    if (
        not TWILIO_ACCOUNT_SID
        or
        not TWILIO_AUTH_TOKEN
    ):

        return None

    return Client(
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN
    )


# ============================================================
# CLIENTE TWILIO GLOBAL
# ============================================================

twilio_client = get_twilio_client()

# ============================================================
# CREAR FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# SOCKET.IO
# ============================================================

socketio = SocketIO(
    app,
    cors_allowed_origins=[
        origen.strip()
        for origen in os.environ.get("HUELLA_ALLOWED_ORIGINS", "").split(",")
        if origen.strip()
    ]
)


# ============================================================
# OAUTH
# ============================================================

oauth = OAuth(app)


# ============================================================
# GOOGLE
# ============================================================

google = oauth.register(
    name="google",

    client_id=os.environ.get(
        "GOOGLE_CLIENT_ID"
    ),

    client_secret=os.environ.get(
        "GOOGLE_CLIENT_SECRET"
    ),

    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),

    client_kwargs={
        "scope": "openid email profile"
    }
)

# ============================================================
# GOOGLE
# ============================================================

google = oauth.register(

    name="google",

    client_id=os.environ.get(
        "GOOGLE_CLIENT_ID"
    ),

    client_secret=os.environ.get(
        "GOOGLE_CLIENT_SECRET"
    ),

    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),

    client_kwargs={
        "scope":
            "openid email profile"
    }

)


# ============================================================
# SEGURIDAD
# ============================================================

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(32)

# ============================================================
# BASE DE DATOS SQLITE
# ============================================================

DATABASE_PATH = BASE_DIR / "data" / "huella.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{DATABASE_PATH.as_posix()}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

db.init_app(app)

# ============================================================
# NORMALIZAR TELÃ‰FONO MÃ‰XICO
# ============================================================

def normalizar_telefono_mexico(
    valor
):

    texto = str(
        valor
        or
        ""
    ).strip()


    solo_digitos = re.sub(
        r"\D",
        "",
        texto
    )


    if (
        texto.startswith(
            "+52"
        )
        and
        len(
            solo_digitos
        )
        ==
        12
    ):

        return (
            "+"
            +
            solo_digitos
        )


    if (
        solo_digitos.startswith(
            "52"
        )
        and
        len(
            solo_digitos
        )
        ==
        12
    ):

        return (
            "+"
            +
            solo_digitos
        )


    if (
        len(
            solo_digitos
        )
        ==
        10
    ):

        return (
            "+52"
            +
            solo_digitos
        )


    return None


# ============================================================
# TELÃ‰FONO - ENVIAR CÃ“DIGO SMS
# ============================================================

@app.route(
    "/api/telefono/enviar-codigo",
    methods=["POST"]
)
def enviar_codigo_telefono():

    usuario_id = session.get(
        "usuario_id"
    )


    if not usuario_id:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    datos = (
        request.get_json(
            silent=True
        )
        or
        {}
    )


    telefono = normalizar_telefono_mexico(
        datos.get(
            "telefono"
        )
    )


    if not telefono:

        return jsonify({

            "ok":
                False,

            "mensaje":
                (
                    "Ingresa un telÃ©fono "
                    "mexicano vÃ¡lido de "
                    "10 dÃ­gitos."
                )

        }), 400


    client = get_twilio_client()


    if (
        not client
        or
        not TWILIO_VERIFY_SERVICE_SID
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                (
                    "Twilio Verify no estÃ¡ "
                    "configurado correctamente."
                )

        }), 500


    try:

        verification = (
            client
            .verify
            .v2
            .services(
                TWILIO_VERIFY_SERVICE_SID
            )
            .verifications
            .create(
                to=telefono,
                channel="sms"
            )
        )


        session[
            "telefono_verificacion"
        ] = telefono


        session[
            "telefono_verificado"
        ] = None


        return jsonify({

            "ok":
                True,

            "mensaje":
                "CÃ³digo enviado por SMS.",

            "telefono":
                telefono,

            "estado":
                verification.status

        }), 200


    except Exception as error:

        print(
            "ERROR TWILIO ENVIANDO CÃ“DIGO:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible enviar el cÃ³digo SMS."

        }), 500


# ============================================================
# TELÃ‰FONO - VERIFICAR CÃ“DIGO
# ============================================================

@app.route(
    "/api/telefono/verificar-codigo",
    methods=["POST"]
)
def verificar_codigo_telefono():

    usuario_id = session.get(
        "usuario_id"
    )


    if not usuario_id:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    datos = (
        request.get_json(
            silent=True
        )
        or
        {}
    )


    telefono = normalizar_telefono_mexico(
        datos.get(
            "telefono"
        )
    )


    codigo = str(
        datos.get(
            "codigo",
            ""
        )
    ).strip()


    if not telefono:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "El telÃ©fono no es vÃ¡lido."

        }), 400


    if not codigo:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Escribe el cÃ³digo recibido por SMS."

        }), 400


    telefono_solicitado = session.get(
        "telefono_verificacion"
    )


    if (
        telefono_solicitado
        !=
        telefono
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                (
                    "Primero solicita un cÃ³digo "
                    "para este nÃºmero."
                )

        }), 400


    client = get_twilio_client()


    if (
        not client
        or
        not TWILIO_VERIFY_SERVICE_SID
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                (
                    "Twilio Verify no estÃ¡ "
                    "configurado correctamente."
                )

        }), 500


    try:

        check = (
            client
            .verify
            .v2
            .services(
                TWILIO_VERIFY_SERVICE_SID
            )
            .verification_checks
            .create(
                to=telefono,
                code=codigo
            )
        )


        if (
            check.status
            !=
            "approved"
        ):

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "El cÃ³digo es incorrecto."

            }), 400


        session[
            "telefono_verificado"
        ] = telefono


        return jsonify({

            "ok":
                True,

            "mensaje":
                "TelÃ©fono verificado correctamente.",

            "telefono":
                telefono

        }), 200


    except Exception as error:

        print(
            "ERROR TWILIO VERIFICANDO CÃ“DIGO:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible verificar el cÃ³digo."

        }), 500

# ============================================================
# CHECKOUT - CONFIGURACIÃ“N
# ============================================================

@app.route(
    "/api/checkout/config",
    methods=["GET"]
)
def checkout_config():

    stripe_public_key = (
        os.environ
        .get(
            "STRIPE_PUBLISHABLE_KEY",
            ""
        )
        .strip()
    )


    public_url = (
        os.environ
        .get(
            "HUELLA_PUBLIC_URL",
            ""
        )
        .strip()
        .rstrip("/")
    )


    if not public_url:

        public_url = (
            request
            .host_url
            .rstrip("/")
        )


    print(
        "STRIPE PUBLIC CONFIGURADA:",
        bool(
            stripe_public_key
        )
    )


    print(
        "STRIPE PUBLIC TEST:",
        stripe_public_key.startswith(
            "pk_test_"
        )
    )


    return jsonify({

        "ok":
            True,

        "stripe_publishable_key":
            stripe_public_key,

        "public_url":
            public_url

    }), 200
    # ============================================================
# STRIPE - CREAR INTENTO DE PAGO
# ============================================================

@app.route(
    "/api/pagos/crear-intento",
    methods=["POST"]
)
def crear_intento_pago():

    # ========================================================
    # COMPROBAR SESIÃ“N
    # ========================================================

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "dueno":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil DueÃ±o"
        }), 403


    # ========================================================
    # COMPROBAR STRIPE
    # ========================================================

    if not stripe.api_key:

        return jsonify({
            "ok": False,
            "mensaje":
                "Stripe no estÃ¡ configurado en el servidor"
        }), 500


    # ========================================================
    # RECIBIR DATOS
    # ========================================================

    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    productos = datos.get(
        "productos",
        []
    )


    tipo_entrega = str(
        datos.get(
            "tipo_entrega",
            "EnvÃ­o estÃ¡ndar"
        )
    ).strip()


    # ========================================================
    # VALIDAR CARRITO
    # ========================================================

    if (
        not isinstance(
            productos,
            list
        )
        or
        not productos
    ):

        return jsonify({
            "ok": False,
            "mensaje":
                "El carrito estÃ¡ vacÃ­o"
        }), 400


    # ========================================================
    # VALIDAR ENTREGA
    # ========================================================

    if tipo_entrega not in [
        "EnvÃ­o estÃ¡ndar",
        "EnvÃ­o express"
    ]:

        return jsonify({
            "ok": False,
            "mensaje":
                "El tipo de entrega no es vÃ¡lido"
        }), 400


    # ========================================================
    # CALCULAR TOTAL DESDE SQLITE
    # NO CONFIAR EN EL PRECIO DEL HTML
    # ========================================================

    subtotal = 0.0

    proveedores = set()


    for item in productos:

        try:

            producto_id = int(
                item.get(
                    "producto_id"
                )
            )


            cantidad = int(
                item.get(
                    "cantidad",
                    1
                )
            )


        except (
            TypeError,
            ValueError
        ):

            return jsonify({
                "ok": False,
                "mensaje":
                    "Producto o cantidad no vÃ¡lidos"
            }), 400


        if cantidad <= 0:

            return jsonify({
                "ok": False,
                "mensaje":
                    "La cantidad debe ser mayor a cero"
            }), 400


        # ====================================================
        # BUSCAR PRODUCTO REAL
        # ====================================================

        producto = (
            ProductoProveedor.query
            .filter_by(
                id=producto_id,
                estado="Activo"
            )
            .first()
        )


        if not producto:

            return jsonify({
                "ok": False,
                "mensaje":
                    "Uno de los productos ya no estÃ¡ disponible"
            }), 404


        # ====================================================
        # VALIDAR STOCK
        # ====================================================

        stock_actual = int(
            producto.stock
            or
            0
        )


        if stock_actual < cantidad:

            return jsonify({
                "ok": False,
                "mensaje":
                    (
                        "No hay suficiente stock de "
                        +
                        producto.nombre
                    )
            }), 400


        # ====================================================
        # GUARDAR PROVEEDOR
        # ====================================================

        proveedores.add(
            producto.proveedor_id
        )


        # ====================================================
        # PRECIO REAL DE SQLITE
        # ====================================================

        precio = float(
            producto.precio
            or
            0
        )


        subtotal += (
            precio
            *
            cantidad
        )


    # ========================================================
    # UN SOLO PROVEEDOR POR PEDIDO
    # ========================================================

    if len(proveedores) > 1:

        return jsonify({
            "ok": False,
            "mensaje":
                (
                    "Cada pedido debe contener productos "
                    "de un solo proveedor"
                )
        }), 400


    # ========================================================
    # ENVÃO
    # ========================================================

    if subtotal >= 1000:

        envio = 0.0


    elif tipo_entrega == "EnvÃ­o express":

        envio = 149.0


    else:

        envio = 89.0


    # ========================================================
    # TOTAL
    # ========================================================

    subtotal = round(
        subtotal,
        2
    )


    envio = round(
        envio,
        2
    )


    total = round(
        subtotal
        +
        envio,
        2
    )


    # Stripe trabaja con centavos.

    total_centavos = int(
        round(
            total
            *
            100
        )
    )


    if total_centavos <= 0:

        return jsonify({
            "ok": False,
            "mensaje":
                "El total del pedido no es vÃ¡lido"
        }), 400


    # ========================================================
    # CREAR PAYMENT INTENT
    # ========================================================

    try:

        payment_intent = (
            stripe.PaymentIntent.create(

                amount=
                    total_centavos,

                currency=
                    "mxn",

                automatic_payment_methods={
                    "enabled": True
                },

                metadata={

                    "usuario_id":
                        str(
                            usuario_id
                        ),

                    "tipo_entrega":
                        tipo_entrega

                }

            )
        )


        return jsonify({

            "ok":
                True,

            "client_secret":
                payment_intent.client_secret,

            "payment_intent_id":
                payment_intent.id,

            "subtotal":
                subtotal,

            "envio":
                envio,

            "total":
                total

        }), 200


    except Exception as error:

        print("")
        print(
            "=========================================="
        )
        print(
            " ERROR CREANDO PAYMENT INTENT STRIPE"
        )
        print(
            "=========================================="
        )
        print(
            error
        )
        print("")


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible preparar el pago con tarjeta"

        }), 500

# ============================================================
# ESTADO
# ============================================================

@app.route(
    "/api/estado"
)
def estado():

    return jsonify({

        "ok":
            True,

        "aplicacion":
            "Huella",

        "backend":
            "Flask",

        "base_datos":
            "SQLite"

    })
# ============================================================
# REGISTRAR USUARIO
# ============================================================

@app.route(
    "/api/registro",
    methods=["POST"]
)
def registrar_usuario():

    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    # ========================================================
    # OBTENER DATOS
    # ========================================================

    nombre = str(
        datos.get(
            "nombre",
            ""
        )
    ).strip()


    correo = str(
        datos.get(
            "correo",
            ""
        )
    ).strip().lower()


    telefono = str(
        datos.get(
            "telefono",
            ""
        )
    ).strip()


    password = str(
        datos.get(
            "password",
            ""
        )
    )


    rol = str(
        datos.get(
            "rol",
            "dueno"
        )
    ).strip().lower()


    cedula = str(
        datos.get(
            "cedula_profesional",
            ""
        )
    ).strip()


    # ========================================================
    # VALIDAR NOMBRE
    # ========================================================

    if not nombre:

        return jsonify({

            "ok": False,

            "mensaje":
                "El nombre es obligatorio"

        }), 400


    if len(nombre) < 3:

        return jsonify({

            "ok": False,

            "mensaje":
                "Ingresa un nombre vÃ¡lido"

        }), 400


    # ========================================================
    # VALIDAR CORREO
    # ========================================================

    if not correo:

        return jsonify({

            "ok": False,

            "mensaje":
                "El correo electrÃ³nico es obligatorio"

        }), 400


    if "@" not in correo:

        return jsonify({

            "ok": False,

            "mensaje":
                "Ingresa un correo electrÃ³nico vÃ¡lido"

        }), 400


    # ========================================================
    # VALIDAR TELÃ‰FONO
    # ========================================================

    if telefono:

        if not telefono.isdigit():

            return jsonify({

                "ok": False,

                "mensaje":
                    "El telÃ©fono debe contener Ãºnicamente nÃºmeros"

            }), 400


        if len(telefono) != 10:

            return jsonify({

                "ok": False,

                "mensaje":
                    "El telÃ©fono debe contener 10 dÃ­gitos"

            }), 400


    # ========================================================
    # VALIDAR CONTRASEÃ‘A
    # ========================================================

    if not password:

        return jsonify({

            "ok": False,

            "mensaje":
                "La contraseÃ±a es obligatoria"

        }), 400


    if len(password) < 8:

        return jsonify({

            "ok": False,

            "mensaje":
                "La contraseÃ±a debe tener mÃ­nimo 8 caracteres"

        }), 400


    tiene_letra = any(

        caracter.isalpha()

        for caracter in password

    )


    tiene_numero = any(

        caracter.isdigit()

        for caracter in password

    )


    if (
        not tiene_letra
        or
        not tiene_numero
    ):

        return jsonify({

            "ok": False,

            "mensaje":
                "La contraseÃ±a debe incluir letras y nÃºmeros"

        }), 400


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    roles_permitidos = [

        "dueno",

        "veterinario",

        "proveedor",

        "administrador"

    ]


    if rol not in roles_permitidos:

        return jsonify({

            "ok": False,

            "mensaje":
                "Tipo de usuario no vÃ¡lido"

        }), 400


    # ========================================================
    # VALIDAR CÃ‰DULA PROFESIONAL
    # ========================================================

    if rol == "veterinario":

        # ----------------------------------------------------
        # LA CÃ‰DULA ES OBLIGATORIA
        # ----------------------------------------------------

        if not cedula:

            return jsonify({

                "ok": False,

                "mensaje":
                    (
                        "La cÃ©dula profesional es obligatoria "
                        "para registrarse como veterinario"
                    )

            }), 400


        # ----------------------------------------------------
        # SOLO NÃšMEROS
        # ----------------------------------------------------

        if not cedula.isdigit():

            return jsonify({

                "ok": False,

                "mensaje":
                    (
                        "La cÃ©dula profesional debe contener "
                        "solamente nÃºmeros"
                    )

            }), 400


        # ----------------------------------------------------
        # LONGITUD
        # ----------------------------------------------------

        if (
            len(cedula) < 6
            or
            len(cedula) > 12
        ):

            return jsonify({

                "ok": False,

                "mensaje":
                    (
                        "La cÃ©dula profesional debe tener "
                        "entre 6 y 12 dÃ­gitos"
                    )

            }), 400


        # ----------------------------------------------------
        # EVITAR CÃ‰DULA DUPLICADA
        # ----------------------------------------------------

        cedula_existente = (

            Usuario.query

            .filter_by(
                cedula_profesional=cedula
            )

            .first()

        )


        if cedula_existente:

            return jsonify({

                "ok": False,

                "mensaje":
                    (
                        "Esta cÃ©dula profesional ya se encuentra "
                        "registrada en otra cuenta de Huella"
                    )

            }), 409


    # ========================================================
    # COMPROBAR CORREO EXISTENTE
    # ========================================================

    usuario_existente = (

        Usuario.query

        .filter_by(
            correo=correo
        )

        .first()

    )


    if usuario_existente:

        return jsonify({

            "ok": False,

            "mensaje":
                "Ya existe una cuenta con este correo"

        }), 409


    # ========================================================
    # PROTEGER CONTRASEÃ‘A
    # ========================================================

    password_segura = (

        generate_password_hash(
            password
        )

    )


    # ========================================================
    # ESTADO INICIAL DE LA CUENTA
    # ========================================================
    #
    # DUEÃ‘O:
    # ACTIVO
    #
    # PROVEEDOR:
    # ACTIVO
    #
    # ADMINISTRADOR:
    # ACTIVO
    #
    # VETERINARIO:
    # INACTIVO HASTA VERIFICAR SU CÃ‰DULA
    # ========================================================

    activo_inicial = True


    if rol == "veterinario":

        activo_inicial = False


    # ========================================================
    # CREAR USUARIO
    # ========================================================

    nuevo_usuario = Usuario(

        nombre=nombre,

        correo=correo,

        telefono=(
            telefono
            if telefono
            else None
        ),

        password=password_segura,

        rol=rol,

        cedula_profesional=(

            cedula

            if rol == "veterinario"

            else None

        ),

        activo=activo_inicial

    )


    # ========================================================
    # GUARDAR EN SQLITE
    # ========================================================

    try:

        db.session.add(
            nuevo_usuario
        )


        db.session.commit()


        # ====================================================
        # RESPUESTA PARA VETERINARIO
        # ====================================================

        if rol == "veterinario":

            return jsonify({

                "ok": True,

                "mensaje":
                    (
                        "Solicitud de registro recibida. "
                        "La cuenta veterinaria quedÃ³ pendiente "
                        "de verificaciÃ³n de cÃ©dula profesional."
                    ),

                "pendiente_verificacion":
                    True,

                "usuario":
                    nuevo_usuario.to_dict()

            }), 201


        # ====================================================
        # RESPUESTA PARA LOS DEMÃS USUARIOS
        # ====================================================

        return jsonify({

            "ok": True,

            "mensaje":
                "Cuenta creada correctamente",

            "pendiente_verificacion":
                False,

            "usuario":
                nuevo_usuario.to_dict()

        }), 201


    # ========================================================
    # ERROR DE BASE DE DATOS
    # ========================================================

    except Exception as error:

        db.session.rollback()


        print("")

        print(
            "ERROR AL REGISTRAR USUARIO:"
        )

        print(
            error
        )

        print("")


        return jsonify({

            "ok": False,

            "mensaje":
                "No fue posible crear la cuenta"

        }), 500
   
# ============================================================
# INICIAR SESIÃ“N CON GOOGLE
# ============================================================

@app.route("/auth/google")
def iniciar_sesion_google():

    redirect_uri = url_for(
        "google_callback",
        _external=True
    )

    return google.authorize_redirect(
        redirect_uri
    )



# ============================================================
# GOOGLE CALLBACK
# ============================================================
@app.route("/auth/google/callback")
def google_callback():

    try:

        token = google.authorize_access_token()

        userinfo = token["userinfo"]

        correo = str(
            userinfo.get("email", "")
        ).strip().lower()

        nombre = str(
            userinfo.get(
                "name",
                "Usuario Huella"
            )
        ).strip()

        email_verificado = userinfo.get(
            "email_verified",
            False
        )


        # ====================================================
        # VALIDAR CORREO DE GOOGLE
        # ====================================================

        if not correo or not email_verificado:

            return redirect(
                "/?google_error=correo"
            )


        # ====================================================
        # BUSCAR USUARIO
        # ====================================================

        usuario = (
            Usuario.query
            .filter_by(
                correo=correo
            )
            .first()
        )


        # ====================================================
        # CREAR USUARIO SI NO EXISTE
        # ====================================================

        if not usuario:

            password_aleatoria = (
                secrets.token_urlsafe(32)
            )

            usuario = Usuario(

                nombre=nombre,

                correo=correo,

                telefono=None,

                password=
                    generate_password_hash(
                        password_aleatoria
                    ),

                rol="dueno",

                cedula_profesional=None,

                activo=True

            )

            db.session.add(
                usuario
            )

            db.session.commit()


        # ====================================================
        # COMPROBAR CUENTA ACTIVA
        # ====================================================

        if not usuario.activo:

            return redirect(
                "/?google_error=cuenta_desactivada"
            )


        # ====================================================
        # CREAR SESIÃ“N
        # ====================================================

        session.clear()

        session["usuario_id"] = (
            usuario.id
        )

        session["nombre"] = (
            usuario.nombre
        )

        session["correo"] = (
            usuario.correo
        )

        session["rol"] = (
            usuario.rol
        )


        # ====================================================
        # REDIRECCIONAR SEGÃšN ROL
        # ====================================================

        if usuario.rol == "veterinario":

            return redirect(
                "/perfiles/veterinario.html"
            )


        if usuario.rol == "proveedor":

            return redirect(
                "/perfiles/proveedor.html"
            )


        if usuario.rol == "administrador":

            return redirect(
                "/perfiles/administrador.html"
            )


        return redirect(
            "/perfiles/dueno.html"
        )


    except Exception as error:

        db.session.rollback()

        print(
            "ERROR LOGIN GOOGLE:",
            error
        )

        return redirect(
            "/?google_error=1"
        )
        

# ============================================================
# INICIAR SESIÃ“N
# ============================================================

@app.route(
    "/api/login",
    methods=["POST"]
)
def iniciar_sesion():

    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    correo = str(
        datos.get(
            "correo",
            ""
        )
    ).strip().lower()


    password = str(
        datos.get(
            "password",
            ""
        )
    )


    # ========================================================
    # VALIDAR CAMPOS
    # ========================================================

    if not correo:

        return jsonify({

            "ok": False,

            "mensaje":
                "Ingresa tu correo electrÃ³nico"

        }), 400


    if not password:

        return jsonify({

            "ok": False,

            "mensaje":
                "Ingresa tu contraseÃ±a"

        }), 400


    # ========================================================
    # BUSCAR USUARIO
    # ========================================================

    usuario = (
        Usuario.query
        .filter_by(
            correo=correo
        )
        .first()
    )


    if not usuario:

        return jsonify({

            "ok": False,

            "mensaje":
                "Correo o contraseÃ±a incorrectos"

        }), 401


    # ========================================================
    # COMPROBAR CONTRASEÃ‘A
    # ========================================================

    if not check_password_hash(

        usuario.password,

        password

    ):

        return jsonify({

            "ok": False,

            "mensaje":
                "Correo o contraseÃ±a incorrectos"

        }), 401


    # ========================================================
    # COMPROBAR CUENTA ACTIVA
    # ========================================================

    if not usuario.activo:

        return jsonify({

            "ok": False,

            "mensaje":
                "Esta cuenta se encuentra desactivada"

        }), 403


    # ========================================================
    # CREAR SESIÃ“N
    # ========================================================

    session.clear()


    session[
        "usuario_id"
    ] = usuario.id


    session[
        "nombre"
    ] = usuario.nombre


    session[
        "correo"
    ] = usuario.correo


    session[
        "rol"
    ] = usuario.rol


    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({

        "ok": True,

        "mensaje":
            "Inicio de sesiÃ³n correcto",

        "usuario":
            usuario.to_dict(),

        "rol":
            usuario.rol

    }), 200


# ============================================================
# CONSULTAR SESIÃ“N ACTUAL
# ============================================================

@app.route(
    "/api/sesion",
    methods=["GET"]
)
def consultar_sesion():

    usuario_id = session.get(
        "usuario_id"
    )


    if not usuario_id:

        return jsonify({

            "ok": False,

            "sesion": False,

            "mensaje":
                "No hay una sesiÃ³n iniciada"

        }), 401


    usuario = db.session.get(

        Usuario,

        usuario_id

    )


    if not usuario:

        session.clear()


        return jsonify({

            "ok": False,

            "sesion": False,

            "mensaje":
                "Usuario no encontrado"

        }), 404


    return jsonify({

        "ok": True,

        "sesion": True,

        "usuario":
            usuario.to_dict()

    })


    # ========================================================
    # CREAR SESIÃ“N
    # ========================================================

    session.clear()

    session["usuario_id"] = usuario.id
    session["nombre"] = usuario.nombre
    session["correo"] = usuario.correo
    session["rol"] = usuario.rol


    # ========================================================
    # RECUPERAR MEMBRESÃA DESDE SQLITE
    # ========================================================

    membresia_db = (
        Membresia.query
        .filter_by(
            usuario_id=usuario.id
        )
        .first()
    )


    membresia_usuario = None


    if membresia_db:

        # ====================================================
        # COMPROBAR VENCIMIENTO
        # ====================================================

        if (
            membresia_db.fecha_expiracion
            and
            datetime.now() > membresia_db.fecha_expiracion
        ):

            membresia_db.estado = "Vencida"

            db.session.commit()


        # ====================================================
        # PREPARAR MEMBRESÃA
        # ====================================================

        membresia_usuario = (
            membresia_db.to_dict()
        )

        membresia_usuario["db_id"] = (
            membresia_db.id
        )

        membresia_usuario["id"] = (
            membresia_db.plan_id
        )


        # ====================================================
        # GUARDAR EN LA SESIÃ“N DE FLASK
        # ====================================================

        session["membresia"] = (
            membresia_usuario
        )


    else:

        session.pop(
            "membresia",
            None
        )


    session.modified = True


    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({

        "ok":
            True,

        "mensaje":
            "Inicio de sesiÃ³n correcto",

        "usuario":
            usuario.to_dict(),

        "rol":
            usuario.rol,

        "membresia":
            membresia_usuario

    }), 200


# ============================================================
# SOLICITAR CÃ“DIGO DE RECUPERACIÃ“N
# CORREO + SMS
# ============================================================

@app.route(
    "/api/recuperacion/enviar-codigo",
    methods=["POST"]
)
def enviar_codigo_recuperacion():

    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    metodo = str(
        datos.get(
            "metodo",
            ""
        )
    ).strip().lower()


    # ========================================================
    # COMPROBAR QUÃ‰ MÃ‰TODO MANDA LA PÃGINA
    # ========================================================

    print(
        "METODO RECIBIDO:",
        metodo
    )


    contacto = str(
        datos.get(
            "contacto",
            ""
        )
    ).strip()


    # ========================================================
    # VALIDAR MÃ‰TODO
    # ========================================================

    if metodo not in [

        "correo",

        "sms",

        "whatsapp"

    ]:

        return jsonify({

            "ok": False,

            "mensaje":
                "MÃ©todo de recuperaciÃ³n no vÃ¡lido"

        }), 400


    if not contacto:

        return jsonify({

            "ok": False,

            "mensaje":
                "Ingresa tu correo o nÃºmero de telÃ©fono"

        }), 400


    # ========================================================
    # RECUPERACIÃ“N POR CORREO
    # RESEND
    # ========================================================

    if metodo == "correo":

        usuario = (
            Usuario.query
            .filter_by(
                correo=contacto.lower()
            )
            .first()
        )


        if not usuario:

            return jsonify({

                "ok": False,

                "mensaje":
                    "No se encontrÃ³ una cuenta con ese correo"

            }), 404


        # ====================================================
        # INVALIDAR CÃ“DIGOS ANTERIORES
        # ====================================================

        anteriores = (
            PasswordReset.query
            .filter_by(

                usuario_id=usuario.id,

                metodo="correo",

                usado=False

            )
            .all()
        )


        for registro in anteriores:

            registro.usado = True


        # ====================================================
        # GENERAR CÃ“DIGO
        # ====================================================

        codigo = str(

            secrets.randbelow(
                900000
            )
            + 100000

        )


        codigo_hash = (
            generate_password_hash(
                codigo
            )
        )


        expira_en = (

            datetime.utcnow()

            + timedelta(
                minutes=10
            )

        )


        nuevo_codigo = PasswordReset(

            usuario_id=
                usuario.id,

            metodo=
                "correo",

            destino=
                usuario.correo,

            codigo_hash=
                codigo_hash,

            expira_en=
                expira_en,

            usado=
                False

        )


        # ====================================================
        # GUARDAR CÃ“DIGO
        # ====================================================

        try:

            db.session.add(
                nuevo_codigo
            )

            db.session.commit()


        except Exception as error:

            db.session.rollback()


            print(
                "ERROR AL CREAR CÃ“DIGO:",
                error
            )


            return jsonify({

                "ok": False,

                "mensaje":
                    "No fue posible generar el cÃ³digo"

            }), 500


        # ====================================================
        # ENVIAR CORREO CON RESEND
        # ====================================================

        try:

            resend.Emails.send({

                "from":
                    EMAIL_FROM,

                "to": [
                    usuario.correo
                ],

                "subject":
                    "CÃ³digo de recuperaciÃ³n - Huella",

                "html": f"""
                    <div style="
                        font-family: Arial, sans-serif;
                        padding: 20px;
                    ">

                        <h2>
                            RecuperaciÃ³n de contraseÃ±a
                        </h2>

                        <p>
                            Hola {usuario.nombre}
                        </p>

                        <p>
                            Tu cÃ³digo de recuperaciÃ³n es:
                        </p>

                        <h1 style="
                            letter-spacing: 6px;
                            font-size: 32px;
                        ">
                            {codigo}
                        </h1>

                        <p>
                            Este cÃ³digo vence en 10 minutos.
                        </p>

                        <p>
                            Si no solicitaste este cambio,
                            puedes ignorar este correo.
                        </p>

                    </div>
                """

            })


            print(
                "Correo de recuperaciÃ³n enviado correctamente."
            )


        except Exception as error:

            print(
                "ERROR AL ENVIAR CORREO:",
                error
            )


            nuevo_codigo.usado = True

            db.session.commit()


            return jsonify({

                "ok": False,

                "mensaje":
                    "No fue posible enviar el correo de recuperaciÃ³n"

            }), 500


        return jsonify({

            "ok": True,

            "mensaje":
                "CÃ³digo enviado correctamente por correo",

            "expira_minutos":
                10

        }), 200


    # ========================================================
    # RECUPERACIÃ“N POR SMS
    # TWILIO VERIFY
    # ========================================================

    if metodo == "sms":

        # ====================================================
        # DEJAR SOLAMENTE NÃšMEROS
        # ====================================================

        telefono_digitos = "".join(

            caracter

            for caracter in contacto

            if caracter.isdigit()

        )


        # ====================================================
        # QUITAR +52 SI LO ESCRIBIERON
        # ====================================================

        if (

            telefono_digitos.startswith(
                "52"
            )

            and len(
                telefono_digitos
            ) == 12

        ):

            telefono_local = (
                telefono_digitos[2:]
            )


        else:

            telefono_local = (
                telefono_digitos
            )


        # ====================================================
        # VALIDAR 10 DÃGITOS
        # ====================================================

        if len(
            telefono_local
        ) != 10:

            return jsonify({

                "ok": False,

                "mensaje":
                    "El nÃºmero de telÃ©fono debe tener 10 dÃ­gitos"

            }), 400


        # ====================================================
        # BUSCAR USUARIO EN HUELLA
        # ====================================================

        usuario = (
            Usuario.query
            .filter_by(
                telefono=telefono_local
            )
            .first()
        )


        if not usuario:

            return jsonify({

                "ok": False,

                "mensaje":
                    "No se encontrÃ³ una cuenta con ese telÃ©fono"

            }), 404


        # ====================================================
        # FORMATO INTERNACIONAL PARA MÃ‰XICO
        # ====================================================

        telefono_twilio = (
            f"+52{telefono_local}"
        )


        # ====================================================
        # TWILIO GENERA Y ENVÃA EL CÃ“DIGO
        # ====================================================

        try:

            verificacion = (

                twilio_client

                .verify

                .v2

                .services(
                    TWILIO_VERIFY_SERVICE_SID
                )

                .verifications

                .create(

                    to=
                        telefono_twilio,

                    channel=
                        "sms"

                )

            )


            print(
                "SMS de recuperaciÃ³n solicitado correctamente."
            )


            print(
                "ESTADO TWILIO:",
                verificacion.status
            )


            return jsonify({

                "ok": True,

                "mensaje":
                    "CÃ³digo enviado correctamente por SMS",

                "estado":
                    verificacion.status

            }), 200


        except Exception as error:

            print("")
            print(
                "ERROR TWILIO RECUPERACIÃ“N:"
            )
            print(error)
            print("")


            return jsonify({

                "ok": False,

                "mensaje":
                    "No fue posible enviar el cÃ³digo por SMS"

            }), 500

    # ========================================================
    # RECUPERACIÃ“N POR WHATSAPP
    # TWILIO VERIFY
    # ========================================================

    if metodo == "whatsapp":

        # ====================================================
        # DEJAR SOLAMENTE NÃšMEROS
        # ====================================================

        telefono_digitos = "".join(

            caracter

            for caracter in contacto

            if caracter.isdigit()

        )


        # ====================================================
        # QUITAR 52 SI EL USUARIO LO ESCRIBIÃ“
        # ====================================================

        if (

            telefono_digitos.startswith("52")

            and

            len(telefono_digitos) == 12

        ):

            telefono_local = (
                telefono_digitos[2:]
            )

        else:

            telefono_local = (
                telefono_digitos
            )


        # ====================================================
        # VALIDAR NÃšMERO MEXICANO
        # ====================================================

        if len(telefono_local) != 10:

            return jsonify({

                "ok": False,

                "mensaje":
                    "El nÃºmero de telÃ©fono debe tener 10 dÃ­gitos"

            }), 400


        # ====================================================
        # BUSCAR CUENTA HUELLA
        # ====================================================

        usuario = (

            Usuario.query

            .filter_by(
                telefono=telefono_local
            )

            .first()

        )


        if not usuario:

            return jsonify({

                "ok": False,

                "mensaje":
                    "No se encontrÃ³ una cuenta con ese telÃ©fono"

            }), 404


        # ====================================================
        # FORMATO INTERNACIONAL
        # ====================================================

        telefono_twilio = (
            f"+52{telefono_local}"
        )


        # ====================================================
        # ENVIAR OTP POR WHATSAPP
        # ====================================================

        try:

            verificacion = (

                twilio_client

                .verify

                .v2

                .services(
                    TWILIO_VERIFY_SERVICE_SID
                )

                .verifications

                .create(

                    to=
                        telefono_twilio,

                    channel=
                        "whatsapp"

                )

            )


            print(
                "WHATSAPP DE RECUPERACIÃ“N ENVIADO"
            )

            print(
                "TELÃ‰FONO:",
                telefono_twilio
            )

            print(
                "ESTADO:",
                verificacion.status
            )


            return jsonify({

                "ok": True,

                "mensaje":
                    "CÃ³digo enviado correctamente por WhatsApp",

                "estado":
                    verificacion.status

            }), 200


        except Exception as error:

            print("")
            print(
                "ERROR TWILIO WHATSAPP:"
            )
            print(error)
            print("")


            return jsonify({

                "ok": False,

                "mensaje":
                    "No fue posible enviar el cÃ³digo por WhatsApp"

            }), 500


# ============================================================
# VALIDAR CÃ“DIGO Y CAMBIAR CONTRASEÃ‘A
# CORREO + SMS TWILIO VERIFY
# ============================================================

@app.route(
    "/api/recuperacion/cambiar-password",
    methods=["POST"]
)
def cambiar_password_recuperacion():

    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    metodo = str(
        datos.get(
            "metodo",
            ""
        )
    ).strip().lower()


    contacto = str(
        datos.get(
            "contacto",
            ""
        )
    ).strip()


    codigo = str(
        datos.get(
            "codigo",
            ""
        )
    ).strip()


    nueva_password = str(
        datos.get(
            "nueva_password",
            ""
        )
    ).strip()


    # ========================================================
    # VALIDAR CAMPOS
    # ========================================================

    if (
        not contacto
        or not codigo
        or not nueva_password
    ):

        return jsonify({

            "ok": False,

            "mensaje":
                "Completa todos los campos"

        }), 400


    # ========================================================
    # DETECTAR MÃ‰TODO SI EL FRONTEND NO LO ENVÃA
    # ========================================================

    if not metodo:

        if "@" in contacto:

            metodo = "correo"

        else:

            metodo = "sms"


    # ========================================================
    # VALIDAR CONTRASEÃ‘A
    # ========================================================

    if len(
        nueva_password
    ) < 8:

        return jsonify({

            "ok": False,

            "mensaje":
                "La contraseÃ±a debe tener mÃ­nimo 8 caracteres"

        }), 400


    if not any(

        caracter.isalpha()

        for caracter in nueva_password

    ):

        return jsonify({

            "ok": False,

            "mensaje":
                "La contraseÃ±a debe contener al menos una letra"

        }), 400


    if not any(

        caracter.isdigit()

        for caracter in nueva_password

    ):

        return jsonify({

            "ok": False,

            "mensaje":
                "La contraseÃ±a debe contener al menos un nÃºmero"

        }), 400


    # ========================================================
    # RECUPERACIÃ“N POR CORREO
    # ========================================================

    if metodo == "correo":

        usuario = (
            Usuario.query
            .filter_by(
                correo=contacto.lower()
            )
            .first()
        )


        if not usuario:

            return jsonify({

                "ok": False,

                "mensaje":
                    "No se encontrÃ³ una cuenta con ese correo"

            }), 404


        registro = (
            PasswordReset.query
            .filter_by(

                usuario_id=
                    usuario.id,

                metodo=
                    "correo",

                usado=
                    False

            )
            .order_by(
                PasswordReset.id.desc()
            )
            .first()
        )


        if not registro:

            return jsonify({

                "ok": False,

                "mensaje":
                    "No existe un cÃ³digo de recuperaciÃ³n activo"

            }), 400


        # ====================================================
        # COMPROBAR EXPIRACIÃ“N
        # ====================================================

        if (
            datetime.utcnow()
            > registro.expira_en
        ):

            registro.usado = True

            db.session.commit()


            return jsonify({

                "ok": False,

                "mensaje":
                    "El cÃ³digo ha expirado. Solicita uno nuevo"

            }), 400


        # ====================================================
        # COMPROBAR CÃ“DIGO
        # ====================================================

        if not check_password_hash(

            registro.codigo_hash,

            codigo

        ):

            return jsonify({

                "ok": False,

                "mensaje":
                    "El cÃ³digo ingresado es incorrecto"

            }), 400


        # ====================================================
        # CAMBIAR CONTRASEÃ‘A
        # ====================================================

        usuario.password = (
            generate_password_hash(
                nueva_password
            )
        )


        registro.usado = True


        try:

            db.session.commit()


        except Exception as error:

            db.session.rollback()


            print(
                "ERROR AL CAMBIAR CONTRASEÃ‘A:",
                error
            )


            return jsonify({

                "ok": False,

                "mensaje":
                    "No fue posible cambiar la contraseÃ±a"

            }), 500


        return jsonify({

            "ok": True,

            "mensaje":
                "ContraseÃ±a cambiada correctamente"

        }), 200


      # ========================================================
    # RECUPERACIÃ“N POR SMS O WHATSAPP
    # TWILIO VERIFY COMPRUEBA EL CÃ“DIGO
    # ========================================================

    if metodo in [
        "sms",
        "whatsapp"
    ]:

        # ====================================================
        # DEJAR SOLAMENTE NÃšMEROS
        # ====================================================

        telefono_digitos = "".join(

            caracter

            for caracter in contacto

            if caracter.isdigit()

        )


        # ====================================================
        # QUITAR +52 PARA BUSCAR EN LA BASE DE DATOS
        # ====================================================

        if (

            telefono_digitos.startswith(
                "52"
            )

            and len(
                telefono_digitos
            ) == 12

        ):

            telefono_local = (
                telefono_digitos[2:]
            )

        else:

            telefono_local = (
                telefono_digitos
            )


        # ====================================================
        # VALIDAR TELÃ‰FONO
        # ====================================================

        if len(
            telefono_local
        ) != 10:

            return jsonify({

                "ok": False,

                "mensaje":
                    "El nÃºmero de telÃ©fono no es vÃ¡lido"

            }), 400


        # ====================================================
        # BUSCAR USUARIO
        # ====================================================

        usuario = (

            Usuario.query

            .filter_by(
                telefono=telefono_local
            )

            .first()

        )


        if not usuario:

            return jsonify({

                "ok": False,

                "mensaje":
                    "No se encontrÃ³ una cuenta con ese telÃ©fono"

            }), 404


        # ====================================================
        # FORMATO INTERNACIONAL
        # ====================================================

        telefono_twilio = (
            f"+52{telefono_local}"
        )


        # ====================================================
        # VERIFICAR CÃ“DIGO CON TWILIO
        # ====================================================

        try:

            comprobacion = (

                twilio_client

                .verify

                .v2

                .services(
                    TWILIO_VERIFY_SERVICE_SID
                )

                .verification_checks

                .create(

                    to=
                        telefono_twilio,

                    code=
                        codigo

                )

            )


        except Exception as error:

            print("")
            print(
                "ERROR TWILIO AL VERIFICAR CÃ“DIGO:"
            )
            print(error)
            print("")


            canal = (

                "WhatsApp"

                if metodo == "whatsapp"

                else "SMS"

            )


            return jsonify({

                "ok": False,

                "mensaje":
                    f"No fue posible verificar el cÃ³digo de {canal}"

            }), 500


        # ====================================================
        # TWILIO DEBE RESPONDER APPROVED
        # ====================================================

        if (

            comprobacion.status

            !=

            "approved"

        ):

            canal = (

                "WhatsApp"

                if metodo == "whatsapp"

                else "SMS"

            )


            return jsonify({

                "ok": False,

                "mensaje":
                    f"El cÃ³digo de {canal} es incorrecto o ha expirado"

            }), 400


        # ====================================================
        # CAMBIAR CONTRASEÃ‘A
        # ====================================================

        usuario.password = (

            generate_password_hash(
                nueva_password
            )

        )


        try:

            db.session.commit()


        except Exception as error:

            db.session.rollback()


            print(
                "ERROR AL CAMBIAR CONTRASEÃ‘A:",
                error
            )


            return jsonify({

                "ok": False,

                "mensaje":
                    "No fue posible cambiar la contraseÃ±a"

            }), 500


        # ====================================================
        # RESPUESTA FINAL
        # ====================================================

        canal = (

            "WhatsApp"

            if metodo == "whatsapp"

            else "SMS"

        )


        return jsonify({

            "ok": True,

            "mensaje":
                f"ContraseÃ±a cambiada correctamente mediante {canal}"

        }), 200


    # ========================================================
    # MÃ‰TODO NO VÃLIDO
    # ========================================================

    return jsonify({

        "ok": False,

        "mensaje":
            "MÃ©todo de recuperaciÃ³n no vÃ¡lido"

    }), 400
    
# ============================================================
# MEMBRESÃAS HUELLA
# CONTROL DEL LADO DEL SERVIDOR
# ============================================================

PLANES_MEMBRESIA = {

    "basico": {

        "nombre":
            "Plan BÃ¡sico",

        "precio":
            49,

        "dias":
            30,

        "max_mascotas":
            1,

        "permisos": {

            "expediente":
                True,

            "vacunas":
                True,

            "citas":
                True,

            "telemedicina":
                False,

            "documentos":
                False,

            "gps":
                False,

            "geocercas":
                False,

            "reportes":
                False

        }

    },


    "esencial": {

        "nombre":
            "Plan Esencial",

        "precio":
            79,

        "dias":
            45,

        "max_mascotas":
            2,

        "permisos": {

            "expediente":
                True,

            "vacunas":
                True,

            "citas":
                True,

            "telemedicina":
                False,

            "documentos":
                True,

            "gps":
                False,

            "geocercas":
                False,

            "reportes":
                False

        }

    },


    "plus": {

        "nombre":
            "Huella Plus",

        "precio":
            149,

        "dias":
            60,

        "max_mascotas":
            5,

        "permisos": {

            "expediente":
                True,

            "vacunas":
                True,

            "citas":
                True,

            "telemedicina":
                False,

            "documentos":
                True,

            "gps":
                True,

            "geocercas":
                True,

            "reportes":
                False

        }

    },


    "premium": {

        "nombre":
            "Plan Premium",

        "precio":
            249,

        "dias":
            75,

        "max_mascotas":
            10,

        "permisos": {

            "expediente":
                True,

            "vacunas":
                True,

            "citas":
                True,

            "telemedicina":
                True,

            "documentos":
                True,

            "gps":
                True,

            "geocercas":
                True,

            "reportes":
                True

        }

    },


    "pro": {

        "nombre":
            "Huella Pro",

        "precio":
            349,

        "dias":
            90,

        # -1 significa ilimitadas
        "max_mascotas":
            -1,

        "permisos": {

            "expediente":
                True,

            "vacunas":
                True,

            "citas":
                True,

            "telemedicina":
                True,

            "documentos":
                True,

            "gps":
                True,

            "geocercas":
                True,

            "reportes":
                True

        }

    }

}


# ============================================================
# COMPROBAR PERMISO DE MEMBRESÃA
# ============================================================

@app.route(
    "/api/membresia/permiso/<string:funcion>",
    methods=["GET"]
)
def comprobar_permiso_membresia(funcion):

    usuario_id = session.get(
        "usuario_id"
    )

    if not usuario_id:

        return jsonify({
            "ok": False,
            "permitido": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # BUSCAR MEMBRESÃA EN SQLITE
    # ========================================================

    membresia_db = (
        Membresia.query
        .filter_by(
            usuario_id=usuario_id
        )
        .first()
    )


    if not membresia_db:

        return jsonify({
            "ok": True,
            "permitido": False,
            "funcion": funcion,
            "mensaje": "No tienes una membresÃ­a activa"
        }), 200


    # ========================================================
    # COMPROBAR VENCIMIENTO
    # ========================================================

    if (
        membresia_db.fecha_expiracion
        and
        datetime.now() > membresia_db.fecha_expiracion
    ):

        membresia_db.estado = "Vencida"

        db.session.commit()

        return jsonify({
            "ok": True,
            "permitido": False,
            "funcion": funcion,
            "plan": membresia_db.nombre_plan,
            "mensaje": "Tu membresÃ­a ha vencido"
        }), 200


    # ========================================================
    # COMPROBAR ESTADO
    # ========================================================

    if membresia_db.estado != "Activa":

        return jsonify({
            "ok": True,
            "permitido": False,
            "funcion": funcion,
            "plan": membresia_db.nombre_plan,
            "mensaje": "Tu membresÃ­a no estÃ¡ activa"
        }), 200


    # ========================================================
    # LEER PERMISOS GUARDADOS EN SQLITE
    # ========================================================

    try:

        permisos = json.loads(
            membresia_db.permisos_json
            or "{}"
        )

    except Exception:

        permisos = {}


    permitido = bool(
        permisos.get(
            funcion,
            False
        )
    )


    return jsonify({

        "ok": True,

        "permitido":
            permitido,

        "funcion":
            funcion,

        "plan_id":
            membresia_db.plan_id,

        "plan":
            membresia_db.nombre_plan,

        "maxPets":
            membresia_db.max_mascotas,

        "status":
            membresia_db.estado

    }), 200

# ============================================================
# CONSULTAR MEMBRESÃA ACTUAL
# ============================================================
@app.route(
    "/api/membresia",
    methods=["GET"]
)
def obtener_membresia():

    usuario_id = session.get(
        "usuario_id"
    )

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # BUSCAR MEMBRESÃA DIRECTAMENTE EN SQLITE
    # ========================================================

    membresia_db = (
        Membresia.query
        .filter_by(
            usuario_id=usuario_id
        )
        .first()
    )


    if not membresia_db:

        session.pop(
            "membresia",
            None
        )

        return jsonify({
            "ok": True,
            "membresia": None
        }), 200


    # ========================================================
    # COMPROBAR VENCIMIENTO
    # ========================================================

    if (
        membresia_db.fecha_expiracion
        and
        datetime.now() > membresia_db.fecha_expiracion
    ):

        membresia_db.estado = "Vencida"

        db.session.commit()


    # ========================================================
    # PREPARAR RESPUESTA
    # ========================================================

    membresia = (
        membresia_db.to_dict()
    )

    membresia["db_id"] = (
        membresia_db.id
    )

    membresia["id"] = (
        membresia_db.plan_id
    )


    # ========================================================
    # GUARDAR TAMBIÃ‰N EN LA SESIÃ“N
    # ========================================================

    session["membresia"] = (
        membresia
    )

    session.modified = True


    return jsonify({
        "ok": True,
        "membresia": membresia
    }), 200


    # ========================================================
    # COMPROBAR VENCIMIENTO
    # ========================================================

    try:

        fecha_expiracion = datetime.fromisoformat(
            membresia["expiry"]
        )


        if datetime.now() > fecha_expiracion:

            membresia["status"] = "Vencida"

            session["membresia"] = membresia

            session.modified = True

    except Exception:

        membresia["status"] = "Vencida"

        session["membresia"] = membresia

        session.modified = True


    return jsonify({

        "ok":
            True,

        "membresia":
            membresia

    }), 200


# ============================================================
# ACTIVAR MEMBRESÃA
# MODO SANDBOX DEL PROYECTO
# ============================================================


    # ========================================================
    # VALIDAR PLAN
    # ========================================================

    if plan_id not in PLANES_MEMBRESIA:

        return jsonify({
            "ok": False,
            "mensaje": "El plan seleccionado no es vÃ¡lido"
        }), 400


    plan = PLANES_MEMBRESIA[
        plan_id
    ]


    # ========================================================
    # FECHAS
    # ========================================================

    inicio = datetime.now()

    expiracion = (
        inicio
        +
        timedelta(
            days=plan["dias"]
        )
    )


    # ========================================================
    # REFERENCIA SANDBOX
    # ========================================================

    referencia = (
        "HUE-"
        +
        secrets.token_hex(
            4
        ).upper()
    )


    # ========================================================
    # BUSCAR SI EL USUARIO YA TIENE MEMBRESÃA
    # ========================================================

    membresia_db = (
        Membresia.query
        .filter_by(
            usuario_id=usuario_id
        )
        .first()
    )


    # ========================================================
    # SI NO EXISTE, CREARLA
    # ========================================================

    if not membresia_db:

        membresia_db = Membresia(

            usuario_id=
                usuario_id,

            plan_id=
                plan_id,

            nombre_plan=
                plan["nombre"],

            precio=
                plan["precio"],

            moneda=
                "MXN",

            duracion_dias=
                plan["dias"],

            max_mascotas=
                plan["max_mascotas"],

            permisos_json=
                json.dumps(
                    plan["permisos"],
                    ensure_ascii=False
                ),

            beneficios_json=
                json.dumps(
                    [],
                    ensure_ascii=False
                ),

            metodo_pago=
                metodo_pago,

            referencia_pago=
                referencia,

            estado_pago=
                "Aprobado",

            estado=
                "Activa",

            modo=
                "sandbox",

            fecha_inicio=
                inicio,

            fecha_expiracion=
                expiracion

        )

        db.session.add(
            membresia_db
        )


    # ========================================================
    # SI YA EXISTE, ACTUALIZARLA
    # ========================================================

    else:

        membresia_db.plan_id = (
            plan_id
        )

        membresia_db.nombre_plan = (
            plan["nombre"]
        )

        membresia_db.precio = (
            plan["precio"]
        )

        membresia_db.moneda = (
            "MXN"
        )

        membresia_db.duracion_dias = (
            plan["dias"]
        )

        membresia_db.max_mascotas = (
            plan["max_mascotas"]
        )

        membresia_db.permisos_json = (
            json.dumps(
                plan["permisos"],
                ensure_ascii=False
            )
        )

        membresia_db.metodo_pago = (
            metodo_pago
        )

        membresia_db.referencia_pago = (
            referencia
        )

        membresia_db.estado_pago = (
            "Aprobado"
        )

        membresia_db.estado = (
            "Activa"
        )

        membresia_db.modo = (
            "sandbox"
        )

        membresia_db.fecha_inicio = (
            inicio
        )

        membresia_db.fecha_expiracion = (
            expiracion
        )


    # ========================================================
    # GUARDAR EN SQLITE
    # ========================================================

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "ERROR GUARDANDO MEMBRESÃA:",
            error
        )

        return jsonify({
            "ok": False,
            "mensaje": "No fue posible guardar la membresÃ­a"
        }), 500


    # ========================================================
    # PREPARAR RESPUESTA PARA EL FRONTEND
    # ========================================================

    membresia = (
        membresia_db.to_dict()
    )


    # Guardamos el ID numÃ©rico de SQLite aparte.
    membresia["db_id"] = (
        membresia_db.id
    )

    # El frontend usa "id" para identificar
    # el plan: basico, esencial, plus, etc.
    membresia["id"] = (
        membresia_db.plan_id
    )


    # ========================================================
    # MANTENER SESIÃ“N COMPATIBLE
    # ========================================================

    session["membresia"] = (
        membresia
    )

    session.modified = True


    return jsonify({

        "ok": True,

        "mensaje":
            "MembresÃ­a activada y guardada correctamente",

        "membresia":
            membresia

    }), 200
    # ========================================================
    # VALIDAR PLAN
    # ========================================================

    if plan_id not in PLANES_MEMBRESIA:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "El plan seleccionado no es vÃ¡lido"

        }), 400


    plan = PLANES_MEMBRESIA[
        plan_id
    ]


    # ========================================================
    # CALCULAR VIGENCIA DESDE EL SERVIDOR
    # ========================================================

    inicio = datetime.now()


    expiracion = (
        inicio
        +
        timedelta(
            days=plan["dias"]
        )
    )


    # ========================================================
    # REFERENCIA DE PAGO SANDBOX
    # ========================================================

    referencia = (

        "HUE-"

        +

        secrets.token_hex(
            4
        ).upper()

    )


    # ========================================================
    # MEMBRESÃA QUE GUARDARÃ FLASK
    # ========================================================

    membresia = {

        "id":
            plan_id,

        "name":
            plan["nombre"],

        "price":
            plan["precio"],

        "currency":
            "MXN",

        "days":
            plan["dias"],

        "maxPets":
            plan["max_mascotas"],

        "permissions":
            plan["permisos"],

        "start":
            inicio.isoformat(),

        "expiry":
            expiracion.isoformat(),

        "paymentMethod":
            metodo_pago,

        "paymentReference":
            referencia,

        "paymentStatus":
            "Aprobado",

        "status":
            "Activa",

        "mode":
            "sandbox"

    }


    # ========================================================
    # GUARDAR EN SESIÃ“N DEL SERVIDOR
    # ========================================================

    session["membresia"] = membresia

    session.modified = True


    return jsonify({

        "ok":
            True,

        "mensaje":
            "MembresÃ­a activada correctamente",

        "membresia":
            membresia

    }), 200


# ============================================================
# CONSULTAR MEMBRESÃA ACTUAL
# ============================================================



    # ========================================================
    # BUSCAR MEMBRESÃA REAL EN SQLITE
    # ========================================================

    membresia_db = (
        Membresia.query
        .filter_by(
            usuario_id=usuario_id
        )
        .first()
    )


    if not membresia_db:

        session.pop(
            "membresia",
            None
        )

        return jsonify({
            "ok": True,
            "membresia": None
        }), 200


    # ========================================================
    # COMPROBAR VENCIMIENTO
    # ========================================================

    if (
        membresia_db.fecha_expiracion
        and
        datetime.now() > membresia_db.fecha_expiracion
    ):

        membresia_db.estado = "Vencida"

        db.session.commit()


    # ========================================================
    # CONVERTIR A RESPUESTA
    # ========================================================

    membresia = (
        membresia_db.to_dict()
    )

    membresia["db_id"] = (
        membresia_db.id
    )

    membresia["id"] = (
        membresia_db.plan_id
    )


    # ========================================================
    # ACTUALIZAR SESIÃ“N
    # ========================================================

    session["membresia"] = (
        membresia
    )

    session.modified = True


    return jsonify({
        "ok": True,
        "membresia": membresia
    }), 200


# ============================================================
# ACTIVAR MEMBRESÃA
# MODO SANDBOX DEL PROYECTO
# ============================================================

@app.route(
    "/api/membresia/activar",
    methods=["POST"]
)
def activar_membresia():

    usuario_id = session.get(
        "usuario_id"
    )

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    plan_id = str(
        datos.get(
            "plan_id",
            ""
        )
    ).strip().lower()


    metodo_pago = str(
        datos.get(
            "metodo_pago",
            ""
        )
    ).strip()


    # ========================================================
    # VALIDAR PLAN
    # ========================================================

    if plan_id not in PLANES_MEMBRESIA:

        return jsonify({
            "ok": False,
            "mensaje": "El plan seleccionado no es vÃ¡lido"
        }), 400


    plan = PLANES_MEMBRESIA[
        plan_id
    ]


    # ========================================================
    # FECHAS
    # ========================================================

    inicio = datetime.now()

    expiracion = (
        inicio
        +
        timedelta(
            days=plan["dias"]
        )
    )


    # ========================================================
    # REFERENCIA DE PAGO SANDBOX
    # ========================================================

    referencia = (
        "HUE-"
        +
        secrets.token_hex(
            4
        ).upper()
    )


    # ========================================================
    # BUSCAR MEMBRESÃA DEL USUARIO
    # ========================================================

    membresia_db = (
        Membresia.query
        .filter_by(
            usuario_id=usuario_id
        )
        .first()
    )


    # ========================================================
    # CREAR MEMBRESÃA
    # ========================================================

    if not membresia_db:

        membresia_db = Membresia(

            usuario_id=usuario_id,

            plan_id=plan_id,

            nombre_plan=
                plan["nombre"],

            precio=
                plan["precio"],

            moneda=
                "MXN",

            duracion_dias=
                plan["dias"],

            max_mascotas=
                plan["max_mascotas"],

            permisos_json=
                json.dumps(
                    plan["permisos"],
                    ensure_ascii=False
                ),

            beneficios_json=
                json.dumps(
                    [],
                    ensure_ascii=False
                ),

            metodo_pago=
                metodo_pago,

            referencia_pago=
                referencia,

            estado_pago=
                "Aprobado",

            estado=
                "Activa",

            modo=
                "sandbox",

            fecha_inicio=
                inicio,

            fecha_expiracion=
                expiracion

        )

        db.session.add(
            membresia_db
        )


    # ========================================================
    # ACTUALIZAR MEMBRESÃA EXISTENTE
    # ========================================================

    else:

        membresia_db.plan_id = (
            plan_id
        )

        membresia_db.nombre_plan = (
            plan["nombre"]
        )

        membresia_db.precio = (
            plan["precio"]
        )

        membresia_db.moneda = (
            "MXN"
        )

        membresia_db.duracion_dias = (
            plan["dias"]
        )

        membresia_db.max_mascotas = (
            plan["max_mascotas"]
        )

        membresia_db.permisos_json = (
            json.dumps(
                plan["permisos"],
                ensure_ascii=False
            )
        )

        membresia_db.metodo_pago = (
            metodo_pago
        )

        membresia_db.referencia_pago = (
            referencia
        )

        membresia_db.estado_pago = (
            "Aprobado"
        )

        membresia_db.estado = (
            "Activa"
        )

        membresia_db.modo = (
            "sandbox"
        )

        membresia_db.fecha_inicio = (
            inicio
        )

        membresia_db.fecha_expiracion = (
            expiracion
        )


    # ========================================================
    # GUARDAR EN SQLITE
    # ========================================================

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "ERROR GUARDANDO MEMBRESÃA:",
            error
        )

        return jsonify({
            "ok": False,
            "mensaje": "No fue posible guardar la membresÃ­a"
        }), 500


    # ========================================================
    # PREPARAR RESPUESTA
    # ========================================================

    membresia = (
        membresia_db.to_dict()
    )

    membresia["db_id"] = (
        membresia_db.id
    )

    membresia["id"] = (
        membresia_db.plan_id
    )


    # ========================================================
    # GUARDAR TAMBIÃ‰N EN SESIÃ“N
    # ========================================================

    session["membresia"] = (
        membresia
    )

    session.modified = True


    return jsonify({

        "ok": True,

        "mensaje":
            "MembresÃ­a activada y guardada correctamente",

        "membresia":
            membresia

    }), 200

# ============================================================
# MASCOTAS - DATOS REALES EN BASE DE DATOS
# ============================================================

PET_UPLOAD_DIR = Path(
    os.environ.get(
        "HUELLA_PET_UPLOAD_DIR",
        str(BASE_DIR / "uploads" / "mascotas")
    )
).expanduser()
PET_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_PET_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


def _usuario_actual_id():
    return session.get("usuario_id")


def _valor_form_o_json(nombre, default=""):
    if request.form and nombre in request.form:
        return request.form.get(nombre, default)

    datos = request.get_json(silent=True) or {}
    return datos.get(nombre, default)


def _numero_opcional(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    if texto == "":
        return None

    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def _buscar_mascota_del_usuario(mascota_id, usuario_id):
    return (
        Mascota.query
        .filter_by(
            id=mascota_id,
            usuario_id=usuario_id
        )
        .first()
    )


def _guardar_foto_mascota(archivo, usuario_id, mascota_id):
    if not archivo or not archivo.filename:
        return None

    nombre_seguro = secure_filename(archivo.filename)
    extension = Path(nombre_seguro).suffix.lower()

    if extension not in ALLOWED_PET_IMAGE_EXTENSIONS:
        raise ValueError(
            "La fotografÃ­a debe ser JPG, JPEG, PNG o WEBP"
        )

    nuevo_nombre = (
        f"mascota_{usuario_id}_{mascota_id}_"
        f"{uuid.uuid4().hex}{extension}"
    )

    destino = PET_UPLOAD_DIR / nuevo_nombre
    archivo.save(destino)

    return f"/uploads/mascotas/{nuevo_nombre}"


def _eliminar_archivo_foto(ruta_foto):
    if not ruta_foto:
        return

    try:
        nombre = Path(ruta_foto).name
        archivo = PET_UPLOAD_DIR / nombre

        if archivo.exists() and archivo.is_file():
            archivo.unlink()
    except Exception as error:
        print("No fue posible eliminar foto anterior:", error)


@app.route(
    "/api/mascotas",
    methods=["GET"]
)
def listar_mascotas():
    usuario_id = _usuario_actual_id()

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    mascotas = (
        Mascota.query
        .filter_by(usuario_id=usuario_id)
        .order_by(Mascota.fecha_registro.desc())
        .all()
    )

    return jsonify({
        "ok": True,
        "mascotas": [
            mascota.to_dict()
            for mascota in mascotas
        ]
    })
    temperatura = _numero_opcional(
        _valor_form_o_json("temperatura")
        or _valor_form_o_json("temperature")
    )

    rasgos = str(
        _valor_form_o_json("rasgos")
        or _valor_form_o_json("traits")
        or ""
    ).strip()

# ============================================================
# CREAR MASCOTA
# ============================================================

@app.route(
    "/api/mascotas",
    methods=["POST"]
)
def crear_mascota():

    # ========================================================
    # USUARIO ACTUAL
    # ========================================================

    usuario_id = _usuario_actual_id()


    if not usuario_id:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    # ========================================================
    # MEMBRESÃA
    # ========================================================

    membresia_db = (
        Membresia.query
        .filter_by(
            usuario_id=usuario_id
        )
        .first()
    )


    if not membresia_db:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Necesitas una membresÃ­a activa para registrar mascotas"

        }), 403


    # ========================================================
    # VENCIMIENTO
    # ========================================================

    if (
        membresia_db.fecha_expiracion
        and
        datetime.now()
        >
        membresia_db.fecha_expiracion
    ):

        membresia_db.estado ="Vencida"


        db.session.commit()


        return jsonify({

            "ok":
                False,

            "mensaje":
                "Tu membresÃ­a ha vencido"

        }), 403


    # ========================================================
    # ESTADO DE LA MEMBRESÃA
    # ========================================================

    if (
        membresia_db.estado
        !=
        "Activa"
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Tu membresÃ­a no estÃ¡ activa"

        }), 403


    # ========================================================
    # LÃMITE DE MASCOTAS
    # ========================================================

    limite_mascotas = membresia_db.max_mascotas


    total_mascotas = (
        Mascota.query
        .filter_by(
            usuario_id=usuario_id
        )
        .count()
    )


    if (
        limite_mascotas != -1
        and
        total_mascotas >= limite_mascotas
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Has alcanzado el lÃ­mite de mascotas de tu plan.",

            "plan":
                membresia_db.nombre_plan,

            "mascotas_registradas":
                total_mascotas,

            "limite":
                limite_mascotas

        }), 403


    # ========================================================
    # NOMBRE
    # ========================================================

    nombre = str(

        _valor_form_o_json(
            "nombre"
        )

        or

        _valor_form_o_json(
            "name"
        )

        or

        ""

    ).strip()


    # ========================================================
    # ESPECIE
    # ========================================================

    especie = str(

        _valor_form_o_json(
            "especie"
        )

        or

        _valor_form_o_json(
            "species"
        )

        or

        ""

    ).strip()


    # ========================================================
    # RAZA
    # ========================================================

    raza = str(

        _valor_form_o_json(
            "raza"
        )

        or

        _valor_form_o_json(
            "breed"
        )

        or

        ""

    ).strip()


    # ========================================================
    # EDAD
    # ========================================================

    edad = _numero_opcional(

        _valor_form_o_json(
            "edad"
        )

        or

        _valor_form_o_json(
            "age"
        )

    )


    # ========================================================
    # PESO
    # ========================================================

    peso = _numero_opcional(

        _valor_form_o_json(
            "peso"
        )

        or

        _valor_form_o_json(
            "weight"
        )

    )


    # ========================================================
    # TEMPERATURA
    # ========================================================

    temperatura = _numero_opcional(

        _valor_form_o_json(
            "temperatura"
        )

        or

        _valor_form_o_json(
            "temperature"
        )

    )


    # ========================================================
    # RASGOS
    # ========================================================

    rasgos = str(

        _valor_form_o_json(
            "rasgos"
        )

        or

        _valor_form_o_json(
            "traits"
        )

        or

        ""

    ).strip()


    # ========================================================
    # SEXO
    # ========================================================

    sexo = str(

        _valor_form_o_json(
            "sexo"
        )

        or

        _valor_form_o_json(
            "sex"
        )

        or

        ""

    ).strip()


    # ========================================================
    # ESTERILIZACIÃ“N
    # ========================================================

    esterilizacion = str(

        _valor_form_o_json(
            "esterilizacion"
        )

        or

        _valor_form_o_json(
            "sterilization"
        )

        or

        ""

    ).strip()


    # ========================================================
    # MICROCHIP
    # ========================================================

    microchip = str(

        _valor_form_o_json(
            "microchip"
        )

        or

        ""

    ).strip()


    # ========================================================
    # VALIDAR NOMBRE
    # ========================================================

    if not nombre:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "El nombre de la mascota es obligatorio"

        }), 400


    # ========================================================
    # VALIDAR ESPECIE
    # ========================================================

    if not especie:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "La especie de la mascota es obligatoria"

        }), 400


    # ========================================================
    # COMPROBAR DUPLICADO
    # ========================================================

    duplicada = (
        Mascota.query
        .filter(

            Mascota.usuario_id
            ==
            usuario_id,

            db.func.lower(
                Mascota.nombre
            )
            ==
            nombre.lower()

        )
        .first()
    )


    if duplicada:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Ya tienes una mascota con ese nombre"

        }), 409


    # ========================================================
    # GENERAR ID HUELLA
    # ========================================================

    huella_id = (

        "HU-"

        +

        secrets
        .token_hex(
            5
        )
        .upper()

    )


    while (
        Mascota.query
        .filter_by(
            huella_id=huella_id
        )
        .first()
    ):

        huella_id = (

            "HU-"

            +

            secrets
            .token_hex(
                5
            )
            .upper()

        )


    # ========================================================
    # CREAR OBJETO
    # ========================================================

    mascota = Mascota(

        usuario_id=
            usuario_id,

        nombre=
            nombre,

        especie=
            especie,

        raza=
            raza,

        edad=
            edad,

        peso=
            peso,

        temperatura=
            temperatura,

        rasgos=
            rasgos,

        sexo=
            sexo,

        esterilizacion=
            esterilizacion,

        microchip=
            microchip,

        huella_id=
            huella_id

    )


    # ========================================================
    # GUARDAR
    # ========================================================

    try:

        db.session.add(
            mascota
        )


        db.session.flush()


        # ====================================================
        # FOTO OPCIONAL
        # ====================================================

        archivo = request.files.get(
                "foto"
            )


        if (
            archivo
            and
            archivo.filename
        ):

            mascota.foto = (
                _guardar_foto_mascota(

                    archivo,

                    usuario_id,

                    mascota.id

                )
            )


        db.session.commit()


        return jsonify({

            "ok":
                True,

            "mensaje":
                "Mascota registrada correctamente",

            "mascota":
                mascota.to_dict()

        }), 201


    except ValueError as error:

        db.session.rollback()


        return jsonify({

            "ok":
                False,

            "mensaje":
                str(
                    error
                )

        }), 400


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR REGISTRANDO MASCOTA:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible registrar la mascota"

        }), 500

## ============================================================
# TICKET PÃšBLICO DEL PEDIDO
# QR -> CONSULTA SEGURA DE LA ORDEN
# ============================================================

@app.route(
    "/api/publico/pedido/<string:numero>",
    methods=["GET"]
)
def api_publico_pedido(numero):

    try:

        # ====================================================
        # BUSCAR PEDIDO
        # ====================================================

        pedido = (
            Pedido.query
            .filter_by(
                numero=numero
            )
            .first()
        )


        if not pedido:

            return jsonify({
                "ok": False,
                "mensaje": "Pedido no encontrado"
            }), 404


        # ====================================================
        # MASCOTA
        # ====================================================

        mascota_nombre = ""


        if pedido.mascota_id:

            mascota = db.session.get(
                Mascota,
                pedido.mascota_id
            )


            if mascota:

                mascota_nombre = (
                    mascota.nombre
                    or
                    ""
                )


        # ====================================================
        # PRODUCTOS
        # ====================================================

        detalles = (
            DetallePedido.query
            .filter_by(
                pedido_id=pedido.id
            )
            .order_by(
                DetallePedido.id.asc()
            )
            .all()
        )


        productos = []


        for detalle in detalles:

            productos.append({

                "id":
                    detalle.id,

                "producto_id":
                    detalle.producto_id,

                "nombre_producto":
                    detalle.nombre_producto,

                "cantidad":
                    int(
                        detalle.cantidad
                        or
                        0
                    ),

                "precio_unitario":
                    float(
                        detalle.precio_unitario
                        or
                        0
                    ),

                "subtotal":
                    float(
                        detalle.subtotal
                        or
                        0
                    )

            })


        # ====================================================
        # DATOS PÃšBLICOS
        #
        # No exponemos:
        # - direcciÃ³n
        # - telÃ©fono
        # - correo
        # - datos bancarios
        # ====================================================

        resultado = {

            "id":
                pedido.id,

            "numero":
                pedido.numero,

            "mascota":
                mascota_nombre,

            "estado":
                pedido.estado,

            "metodo_pago":
                pedido.metodo_pago,

            "tipo_entrega":
                pedido.tipo_entrega,

            "subtotal":
                float(
                    pedido.subtotal
                    or
                    0
                ),

            "envio":
                float(
                    pedido.envio
                    or
                    0
                ),

            "total":
                float(
                    pedido.total
                    or
                    0
                ),

            "creado_en":
                (
                    pedido.creado_en.isoformat()
                    if pedido.creado_en
                    else None
                ),

            "productos":
                productos

        }


        return jsonify({

            "ok":
                True,

            "pedido":
                resultado

        }), 200


    except Exception as error:

        print(
            "ERROR TICKET PUBLICO:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible consultar el pedido."

        }), 500

    # ========================================================
    # COMPROBAR ESTADO
    # ========================================================

    if membresia_db.estado != "Activa":

        return jsonify({
            "ok": False,
            "mensaje":
                "Tu membresÃ­a no estÃ¡ activa"
        }), 403


    # ========================================================
    # CONTAR MASCOTAS REGISTRADAS
    # ========================================================

   
    limite_mascotas = membresia_db.max_mascotas
    total_mascotas = (
        Mascota.query
        .filter_by(
            usuario_id=usuario_id
        )
        .count()
    )


    # ========================================================
    # BLOQUEAR SI YA LLEGÃ“ AL LÃMITE
    # -1 SIGNIFICA ILIMITADAS
    # ========================================================

    if (
        limite_mascotas != -1
        and
        total_mascotas >= limite_mascotas
    ):

        return jsonify({
            "ok": False,
            "mensaje":
                "Has alcanzado el lÃ­mite de mascotas de tu plan.",
            "plan":
                membresia_db.nombre_plan,
            "mascotas_registradas":
                total_mascotas,
            "limite":
                limite_mascotas
        }), 403
    

    nombre = str(
        _valor_form_o_json("nombre")
        or _valor_form_o_json("name")
        or ""
    ).strip()

    especie = str(
        _valor_form_o_json("especie")
        or _valor_form_o_json("species")
        or ""
    ).strip()

    raza = str(
        _valor_form_o_json("raza")
        or _valor_form_o_json("breed")
        or ""
    ).strip()

    edad = _numero_opcional(
        _valor_form_o_json("edad")
        or _valor_form_o_json("age")
    )

    peso = _numero_opcional(
        _valor_form_o_json("peso")
        or _valor_form_o_json("weight")
    )

    sexo = str(
        _valor_form_o_json("sexo")
        or _valor_form_o_json("sex")
        or ""
    ).strip()

    esterilizacion = str(
        _valor_form_o_json("esterilizacion")
        or _valor_form_o_json("sterilization")
        or ""
    ).strip()

    microchip = str(
        _valor_form_o_json("microchip")
        or ""
    ).strip()

    if not nombre:
        return jsonify({
            "ok": False,
            "mensaje": "El nombre de la mascota es obligatorio"
        }), 400

    if not especie:
        especie = "Sin especie registrada"

    duplicada = (
        Mascota.query
        .filter(
            Mascota.usuario_id == usuario_id,
            db.func.lower(Mascota.nombre) == nombre.lower()
        )
        .first()
    )

    if duplicada:
        return jsonify({
            "ok": False,
            "mensaje": "Ya tienes una mascota con ese nombre"
        }), 409

    huella_id = (
        "HU-" + secrets.token_hex(5).upper()
    )

    while Mascota.query.filter_by(huella_id=huella_id).first():
        huella_id = (
            "HU-" + secrets.token_hex(5).upper()
        )

    mascota = Mascota(
        usuario_id=usuario_id,
        nombre=nombre,
        especie=especie,
        raza=raza,
        edad=edad,
        peso=peso,
        temperatura=temperatura,
        rasgos=rasgos,
        sexo=sexo,
        esterilizacion=esterilizacion,
        microchip=microchip,
        huella_id=huella_id
    )

    db.session.add(mascota)
    db.session.flush()

    archivo = request.files.get("foto")

    if archivo and archivo.filename:
        try:
            mascota.foto = _guardar_foto_mascota(
                archivo,
                usuario_id,
                mascota.id
            )
        except ValueError as error:
            db.session.rollback()
            return jsonify({
                "ok": False,
                "mensaje": str(error)
            }), 400

    db.session.commit()

    return jsonify({
        "ok": True,
        "mensaje": "Mascota registrada correctamente",
        "mascota": mascota.to_dict()
    }), 201


@app.route(
    "/api/mascotas/<int:mascota_id>",
    methods=["GET"]
)
def obtener_mascota(mascota_id):
    usuario_id = _usuario_actual_id()

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )

    if not mascota:
        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404

    return jsonify({
        "ok": True,
        "mascota": mascota.to_dict()
    })


@app.route(
    "/api/mascotas/<int:mascota_id>",
    methods=["PUT", "PATCH"]
)
def actualizar_mascota(mascota_id):
    usuario_id = _usuario_actual_id()

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )

    if not mascota:
        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404

    nombre = str(
        _valor_form_o_json("nombre", mascota.nombre)
        or _valor_form_o_json("name", mascota.nombre)
        or mascota.nombre
    ).strip()

    if not nombre:
        return jsonify({
            "ok": False,
            "mensaje": "El nombre de la mascota es obligatorio"
        }), 400

    duplicada = (
        Mascota.query
        .filter(
            Mascota.usuario_id == usuario_id,
            Mascota.id != mascota.id,
            db.func.lower(Mascota.nombre) == nombre.lower()
        )
        .first()
    )

    if duplicada:
        return jsonify({
            "ok": False,
            "mensaje": "Ya tienes otra mascota con ese nombre"
        }), 409

    mascota.nombre = nombre
    mascota.especie = str(
        _valor_form_o_json("especie", mascota.especie)
        or _valor_form_o_json("species", mascota.especie)
        or mascota.especie
    ).strip()

    mascota.raza = str(
        _valor_form_o_json("raza", mascota.raza or "")
        or _valor_form_o_json("breed", mascota.raza or "")
        or ""
    ).strip()

    edad_valor = (
        _valor_form_o_json("edad", mascota.edad)
        if request.form and "edad" in request.form
        else _valor_form_o_json("age", mascota.edad)
    )

    peso_valor = (
        _valor_form_o_json("peso", mascota.peso)
        if request.form and "peso" in request.form
        else _valor_form_o_json("weight", mascota.peso)
    )

    mascota.edad = _numero_opcional(edad_valor)
    mascota.peso = _numero_opcional(peso_valor)
    
    temperatura_valor = (_valor_form_o_json(
            "temperatura",
            mascota.temperatura
        )
        or
        _valor_form_o_json(
            "temperature",
            mascota.temperatura
        )
    )

    mascota.temperatura = _numero_opcional(
        temperatura_valor
    )


    rasgos_valor = (
        _valor_form_o_json(
            "rasgos",
            mascota.rasgos or ""
        )
        or
        _valor_form_o_json(
            "traits",
            mascota.rasgos or ""
        )
        or
        ""
    )

    mascota.rasgos = str(
        rasgos_valor
    ).strip()

    mascota.sexo = str(
        _valor_form_o_json("sexo", mascota.sexo or "")
        or _valor_form_o_json("sex", mascota.sexo or "")
        or ""
    ).strip()

    mascota.esterilizacion = str(
        _valor_form_o_json(
            "esterilizacion",
            mascota.esterilizacion or ""
        )
        or _valor_form_o_json(
            "sterilization",
            mascota.esterilizacion or ""
        )
        or ""
    ).strip()

    mascota.microchip = str(
        _valor_form_o_json("microchip", mascota.microchip or "")
        or ""
    ).strip()

    archivo = request.files.get("foto")

    if archivo and archivo.filename:
        try:
            nueva_foto = _guardar_foto_mascota(
                archivo,
                usuario_id,
                mascota.id
            )
        except ValueError as error:
            return jsonify({
                "ok": False,
                "mensaje": str(error)
            }), 400

        _eliminar_archivo_foto(mascota.foto)
        mascota.foto = nueva_foto

    db.session.commit()

    return jsonify({
        "ok": True,
        "mensaje": "Mascota actualizada correctamente",
        "mascota": mascota.to_dict()
    })


@app.route(
    "/api/mascotas/<int:mascota_id>",
    methods=["DELETE"]
)
def eliminar_mascota(mascota_id):
    usuario_id = _usuario_actual_id()

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )

    if not mascota:
        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404

    _eliminar_archivo_foto(mascota.foto)

    DatosModuloMascota.query.filter_by(
        usuario_id=usuario_id,
        mascota_id=mascota.id
    ).delete(synchronize_session=False)

    db.session.delete(mascota)
    db.session.commit()

    return jsonify({
        "ok": True,
        "mensaje": "Mascota eliminada correctamente"
    })


@app.route(
    "/api/mascotas/<int:mascota_id>/foto",
    methods=["POST"]
)
def actualizar_foto_mascota(mascota_id):
    usuario_id = _usuario_actual_id()

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )

    if not mascota:
        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404

    archivo = request.files.get("foto")

    if not archivo or not archivo.filename:
        return jsonify({
            "ok": False,
            "mensaje": "Selecciona una fotografÃ­a"
        }), 400

    try:
        nueva_foto = _guardar_foto_mascota(
            archivo,
            usuario_id,
            mascota.id
        )
    except ValueError as error:
        return jsonify({
            "ok": False,
            "mensaje": str(error)
        }), 400

    _eliminar_archivo_foto(mascota.foto)
    mascota.foto = nueva_foto
    db.session.commit()

    return jsonify({
        "ok": True,
        "mensaje": "FotografÃ­a actualizada correctamente",
        "mascota": mascota.to_dict()
    })


@app.route(
    "/api/mascotas/<int:mascota_id>/foto",
    methods=["DELETE"]
)
def eliminar_foto_mascota(mascota_id):
    usuario_id = _usuario_actual_id()

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )

    if not mascota:
        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404

    _eliminar_archivo_foto(mascota.foto)
    mascota.foto = None
    db.session.commit()

    return jsonify({
        "ok": True,
        "mensaje": "FotografÃ­a eliminada correctamente",
        "mascota": mascota.to_dict()
    })


# ============================================================
# CARRUSEL DE FOTOGRAFÃAS DE MASCOTAS
# ============================================================


def _registrar_foto_actual_en_carrusel(mascota):

    if not mascota:
        return

    if not mascota.foto:
        return

    existente = (
        FotoMascota.query
        .filter_by(
            mascota_id=mascota.id,
            archivo=mascota.foto
        )
        .first()
    )

    if existente:
        return

    total = (
        FotoMascota.query
        .filter_by(
            mascota_id=mascota.id
        )
        .count()
    )

    foto = FotoMascota(
        mascota_id=mascota.id,
        archivo=mascota.foto,
        portada=True,
        orden=total
    )

    # Quitamos cualquier portada anterior.
    FotoMascota.query.filter_by(
        mascota_id=mascota.id
    ).update({
        "portada": False
    })

    db.session.add(foto)
    db.session.commit()


# ============================================================
# LISTAR FOTOS DEL CARRUSEL
# ============================================================

@app.route(
    "/api/mascotas/<int:mascota_id>/fotos",
    methods=["GET"]
)
def listar_fotos_mascota(mascota_id):

    usuario_id = _usuario_actual_id()

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )


    if not mascota:

        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404


    # Si la mascota ya tenÃ­a la foto antigua,
    # la incorporamos automÃ¡ticamente al carrusel.
    _registrar_foto_actual_en_carrusel(
        mascota
    )


    fotos = (
        FotoMascota.query
        .filter_by(
            mascota_id=mascota.id
        )
        .order_by(
            FotoMascota.portada.desc(),
            FotoMascota.orden.asc(),
            FotoMascota.id.asc()
        )
        .all()
    )


    return jsonify({

        "ok": True,

        "mascota": {
            "id": mascota.id,
            "nombre": mascota.nombre,
            "foto": mascota.foto or ""
        },

        "fotos": [
            foto.to_dict()
            for foto in fotos
        ],

        "total": len(fotos)

    }), 200


# ============================================================
# SUBIR UNA FOTO NUEVA AL CARRUSEL
# ============================================================

@app.route(
    "/api/mascotas/<int:mascota_id>/fotos",
    methods=["POST"]
)
def subir_foto_carrusel(mascota_id):

    usuario_id = _usuario_actual_id()

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )


    if not mascota:

        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404


    archivo = request.files.get(
        "foto"
    )


    if not archivo or not archivo.filename:

        return jsonify({
            "ok": False,
            "mensaje": "Selecciona una fotografÃ­a"
        }), 400


    # ========================================================
    # LÃMITE DE FOTOS
    # ========================================================

    total_actual = (
        FotoMascota.query
        .filter_by(
            mascota_id=mascota.id
        )
        .count()
    )


    if total_actual >= 20:

        return jsonify({
            "ok": False,
            "mensaje":
                "Puedes guardar un mÃ¡ximo de 20 fotografÃ­as por mascota."
        }), 400


    # ========================================================
    # GUARDAR ARCHIVO
    # ========================================================

    try:

        nueva_ruta = _guardar_foto_mascota(
            archivo,
            usuario_id,
            mascota.id
        )

    except ValueError as error:

        return jsonify({
            "ok": False,
            "mensaje": str(error)
        }), 400


    # ========================================================
    # INCORPORAR FOTO ANTERIOR AL CARRUSEL
    # ========================================================

    if mascota.foto:

        foto_anterior = (
            FotoMascota.query
            .filter_by(
                mascota_id=mascota.id,
                archivo=mascota.foto
            )
            .first()
        )

        if not foto_anterior:

            foto_anterior = FotoMascota(

                mascota_id=
                    mascota.id,

                archivo=
                    mascota.foto,

                portada=
                    True,

                orden=
                    0

            )

            db.session.add(
                foto_anterior
            )


    # ========================================================
    # OBTENER ORDEN
    # ========================================================

    ultimo = (
        FotoMascota.query
        .filter_by(
            mascota_id=mascota.id
        )
        .order_by(
            FotoMascota.orden.desc()
        )
        .first()
    )


    siguiente_orden = (
        int(ultimo.orden) + 1
        if ultimo
        else 0
    )


    # ========================================================
    # PRIMERA FOTO = PORTADA
    # ========================================================

    existe_portada = (
        FotoMascota.query
        .filter_by(
            mascota_id=mascota.id,
            portada=True
        )
        .first()
    )


    es_portada = (
        existe_portada is None
        and not mascota.foto
    )


    nueva_foto = FotoMascota(

        mascota_id=
            mascota.id,

        archivo=
            nueva_ruta,

        portada=
            es_portada,

        orden=
            siguiente_orden

    )


    db.session.add(
        nueva_foto
    )


    if not mascota.foto:

        mascota.foto = nueva_ruta

        nueva_foto.portada = True


    db.session.commit()


    return jsonify({

        "ok": True,

        "mensaje":
            "FotografÃ­a agregada al carrusel.",

        "foto":
            nueva_foto.to_dict(),

        "mascota":
            mascota.to_dict()

    }), 201


# ============================================================
# ELEGIR FOTO DE PORTADA
# ============================================================

@app.route(
    "/api/mascotas/<int:mascota_id>/fotos/<int:foto_id>/portada",
    methods=["PATCH", "PUT"]
)
def establecer_foto_portada(
    mascota_id,
    foto_id
):

    usuario_id = _usuario_actual_id()


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )


    if not mascota:

        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404


    foto = (
        FotoMascota.query
        .filter_by(
            id=foto_id,
            mascota_id=mascota.id
        )
        .first()
    )


    if not foto:

        return jsonify({
            "ok": False,
            "mensaje": "FotografÃ­a no encontrada"
        }), 404


    # Quitar la portada anterior.
    FotoMascota.query.filter_by(
        mascota_id=mascota.id
    ).update({
        "portada": False
    })


    # Marcar la nueva.
    foto.portada = True


    # Mantener compatibilidad con todo Huella.
    # Los mÃ³dulos antiguos siguen usando mascota.foto.
    mascota.foto = foto.archivo


    db.session.commit()


    return jsonify({

        "ok": True,

        "mensaje":
            "La fotografÃ­a ahora es la portada de la mascota.",

        "foto":
            foto.to_dict(),

        "mascota":
            mascota.to_dict()

    }), 200


# ============================================================
# ELIMINAR FOTO DEL CARRUSEL
# ============================================================

@app.route(
    "/api/mascotas/<int:mascota_id>/fotos/<int:foto_id>",
    methods=["DELETE"]
)
def eliminar_foto_carrusel(
    mascota_id,
    foto_id
):

    usuario_id = _usuario_actual_id()


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )


    if not mascota:

        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404


    foto = (
        FotoMascota.query
        .filter_by(
            id=foto_id,
            mascota_id=mascota.id
        )
        .first()
    )


    if not foto:

        return jsonify({
            "ok": False,
            "mensaje": "FotografÃ­a no encontrada"
        }), 404


    ruta_eliminada = foto.archivo

    era_portada = bool(
        foto.portada
        or
        mascota.foto == foto.archivo
    )


    db.session.delete(
        foto
    )


    db.session.flush()


    nueva_portada = None


    # ========================================================
    # SI ERA PORTADA, ELEGIR OTRA
    # ========================================================

    if era_portada:

        nueva_portada = (
            FotoMascota.query
            .filter_by(
                mascota_id=mascota.id
            )
            .order_by(
                FotoMascota.orden.asc(),
                FotoMascota.id.asc()
            )
            .first()
        )


        FotoMascota.query.filter_by(
            mascota_id=mascota.id
        ).update({
            "portada": False
        })


        if nueva_portada:

            nueva_portada.portada = True

            mascota.foto = (
                nueva_portada.archivo
            )

        else:

            mascota.foto = None


    db.session.commit()


    # El archivo fÃ­sico se elimina despuÃ©s
    # de guardar correctamente en la base.
    _eliminar_archivo_foto(
        ruta_eliminada
    )


    return jsonify({

        "ok": True,

        "mensaje":
            "FotografÃ­a eliminada del carrusel.",

        "nueva_portada":
            (
                nueva_portada.to_dict()
                if nueva_portada
                else None
            ),

        "mascota":
            mascota.to_dict()

    }), 200


# ============================================================
# PERMISOS REQUERIDOS POR MÃ“DULO
# ============================================================

MODULO_A_PERMISO = {

    "expediente":
        "expediente",

    "vacunas":
        "vacunas",

    "citas":
        "citas",

    "telemedicina":
        "telemedicina",

    "estudios":
        "documentos",

    "recordatorios":
        "recordatorios",

    "gps":
        "gps",

    "geocercas":
        "geocercas",

    "tratamientos":
        "expediente"

}


# ============================================================
# VERIFICAR PERMISO DE MEMBRESÃA DESDE SQLITE
# ============================================================

def _verificar_permiso_modulo(
    usuario_id,
    modulo
):

    # Recetas actualmente no requiere
    # una funciÃ³n especial de membresÃ­a.
    permiso_requerido = (
        MODULO_A_PERMISO.get(
            modulo
        )
    )

    if not permiso_requerido:

        return (
            True,
            None,
            200
        )


    # ========================================================
    # BUSCAR MEMBRESÃA REAL
    # ========================================================

    membresia_db = (
        Membresia.query
        .filter_by(
            usuario_id=usuario_id
        )
        .first()
    )


    if not membresia_db:

        return (
            False,
            {
                "ok": False,
                "permitido": False,
                "mensaje":
                    "Necesitas una membresÃ­a activa para usar este mÃ³dulo",
                "modulo":
                    modulo
            },
            403
        )


    # ========================================================
    # REVISAR VENCIMIENTO
    # ========================================================

    if (
        membresia_db.fecha_expiracion
        and
        datetime.now()
        >
        membresia_db.fecha_expiracion
    ):

        membresia_db.estado = (
            "Vencida"
        )

        db.session.commit()

        return (
            False,
            {
                "ok": False,
                "permitido": False,
                "mensaje":
                    "Tu membresÃ­a ha vencido",
                "modulo":
                    modulo
            },
            403
        )


    # ========================================================
    # REVISAR ESTADO
    # ========================================================

    if membresia_db.estado != "Activa":

        return (
            False,
            {
                "ok": False,
                "permitido": False,
                "mensaje":
                    "Tu membresÃ­a no estÃ¡ activa",
                "modulo":
                    modulo
            },
            403
        )


    # ========================================================
    # LEER PERMISOS
    # ========================================================

    try:

        permisos = json.loads(
            membresia_db.permisos_json
            or "{}"
        )

    except Exception:

        permisos = {}


    permitido = bool(
        permisos.get(
            permiso_requerido,
            False
        )
    )


    if not permitido:

        return (
            False,
            {
                "ok": False,
                "permitido": False,
                "mensaje":
                    "Tu plan actual no incluye esta funciÃ³n",
                "modulo":
                    modulo,
                "funcion":
                    permiso_requerido,
                "plan":
                    membresia_db.nombre_plan
            },
            403
        )


    return (
        True,
        None,
        200
    )

# ============================================================
# MÃ“DULOS PERSISTENTES POR MASCOTA
# ============================================================

MODULOS_MASCOTA_PERMITIDOS = {
    "expediente",
    "consultas",
    "vacunas",
    "citas",
    "telemedicina",
    "estudios",
    "recordatorios",
    "gps",
    "geocercas",
    "recetas",
    "tratamientos"
}


def _obtener_datos_modulo(usuario_id, mascota_id, modulo):
    return (
        DatosModuloMascota.query
        .filter_by(
            usuario_id=usuario_id,
            mascota_id=mascota_id,
            modulo=modulo
        )
        .first()
    )


@app.route(
    "/api/mascotas/<int:mascota_id>/modulos/<string:modulo>",
    methods=["GET"]
)
def obtener_modulo_mascota(mascota_id, modulo):
    usuario_id = _usuario_actual_id()

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    modulo = str(modulo or "").strip().lower()

    if modulo not in MODULOS_MASCOTA_PERMITIDOS:
        return jsonify({
            "ok": False,
            "mensaje": "MÃ³dulo no permitido"
        }), 400
    permitido, error_permiso, status_permiso = (
        _verificar_permiso_modulo(
            usuario_id,
            modulo
        )
    )

    if not permitido:
        return jsonify(
            error_permiso
        ), status_permiso
        
    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )

    if not mascota:
        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404

    registro = _obtener_datos_modulo(
        usuario_id,
        mascota_id,
        modulo
    )

    if not registro:
        return jsonify({
            "ok": True,
            "existe": False,
            "modulo": modulo,
            "mascota": mascota.to_dict(),
            "datos": None
        })

    try:
        datos = json.loads(registro.datos_json)
    except Exception:
        datos = None

    return jsonify({
        "ok": True,
        "existe": True,
        "modulo": modulo,
        "mascota": mascota.to_dict(),
        "datos": datos,
        "actualizado_en": (
            registro.actualizado_en.isoformat()
            if registro.actualizado_en
            else None
        )
    })
    
    


@app.route(
    "/api/mascotas/<int:mascota_id>/modulos/<string:modulo>",
    methods=["PUT", "POST"]
)
def guardar_modulo_mascota(mascota_id, modulo):
    usuario_id = _usuario_actual_id()

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    modulo = str(modulo or "").strip().lower()

    if modulo not in MODULOS_MASCOTA_PERMITIDOS:
        return jsonify({
            "ok": False,
            "mensaje": "MÃ³dulo no permitido"
        }), 400
    permitido, error_permiso, status_permiso = (
        _verificar_permiso_modulo(
            usuario_id,
            modulo
        )
    )

    if not permitido:
        return jsonify(
            error_permiso
        ), status_permiso

    mascota = _buscar_mascota_del_usuario(
        mascota_id,
        usuario_id
    )

    if not mascota:
        return jsonify({
            "ok": False,
            "mensaje": "Mascota no encontrada"
        }), 404

    payload = request.get_json(silent=True)

    if payload is None:
        return jsonify({
            "ok": False,
            "mensaje": "EnvÃ­a datos JSON vÃ¡lidos"
        }), 400

    datos = payload.get("datos", payload)

    try:
        datos_json = json.dumps(
            datos,
            ensure_ascii=False
        )
    except (TypeError, ValueError):
        return jsonify({
            "ok": False,
            "mensaje": "Los datos no se pueden guardar"
        }), 400

    registro = _obtener_datos_modulo(
        usuario_id,
        mascota_id,
        modulo
    )

    if registro is None:
        registro = DatosModuloMascota(
            usuario_id=usuario_id,
            mascota_id=mascota_id,
            modulo=modulo,
            datos_json=datos_json
        )
        db.session.add(registro)
    else:
        registro.datos_json = datos_json
        registro.actualizado_en = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "ok": True,
        "mensaje": "Datos guardados correctamente",
        "modulo": modulo,
        "mascota_id": mascota_id,
        "datos": datos
    })
    
    
# ============================================================
# VETERINARIO - LISTAR PACIENTES VINCULADOS
# ============================================================

@app.route(
    "/api/veterinario/pacientes",
    methods=["GET"]
)
def listar_pacientes_veterinario():

    veterinario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )

    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not veterinario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "veterinario":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Veterinario"
        }), 403

    # ========================================================
    # BUSCAR VÃNCULOS ACTIVOS
    # ========================================================

    vinculos = (
        VinculoVeterinarioMascota.query
        .filter_by(
            veterinario_id=veterinario_id,
            estado="Activo"
        )
        .order_by(
            VinculoVeterinarioMascota.creado_en.desc()
        )
        .all()
    )

    pacientes = []

    # ========================================================
    # CONSTRUIR LISTA DE PACIENTES
    # ========================================================

    for vinculo in vinculos:

        mascota = db.session.get(
            Mascota,
            vinculo.mascota_id
        )

        if not mascota:
            continue

        propietario = db.session.get(
            Usuario,
            vinculo.propietario_id
        )

        paciente = {
            **mascota.to_dict(),

            "mascota_id":
                mascota.id,

            "vinculo_id":
                vinculo.id,

            "estado_vinculo":
                vinculo.estado,

            "propietario": {
                "id":
                    propietario.id
                    if propietario
                    else None,

                "nombre":
                    propietario.nombre
                    if propietario
                    else "Propietario"
            },

            "fecha_vinculacion":
                (
                    vinculo.fecha_vinculacion.isoformat()
                    if vinculo.fecha_vinculacion
                    else None
                )
        }

        pacientes.append(
            paciente
        )

    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({
        "ok": True,
        "total": len(pacientes),
        "pacientes": pacientes
    }), 200
    
    
    # ============================================================
# VETERINARIO - OBTENER PACIENTE VINCULADO
# ============================================================

@app.route(
    "/api/veterinario/pacientes/<int:mascota_id>",
    methods=["GET"]
)
def obtener_paciente_veterinario(mascota_id):

    veterinario_id = session.get("usuario_id")
    rol = session.get("rol")

    if not veterinario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    if rol != "veterinario":

        return jsonify({
            "ok": False,
            "mensaje": "Esta funciÃ³n pertenece al perfil Veterinario"
        }), 403


    # ========================================================
    # COMPROBAR QUE EL VETERINARIO ESTÃ‰ AUTORIZADO
    # ========================================================

    vinculo = (
        VinculoVeterinarioMascota.query
        .filter_by(
            veterinario_id=veterinario_id,
            mascota_id=mascota_id,
            estado="Activo"
        )
        .first()
    )


    if not vinculo:

        return jsonify({
            "ok": False,
            "mensaje":
                "No tienes autorizaciÃ³n para consultar esta mascota"
        }), 403


    mascota = db.session.get(
        Mascota,
        mascota_id
    )


    if not mascota:

        return jsonify({
            "ok": False,
            "mensaje": "Paciente no encontrado"
        }), 404


    propietario = db.session.get(
        Usuario,
        vinculo.propietario_id
    )


    return jsonify({

        "ok": True,

        "paciente": {
            **mascota.to_dict(),

            "mascota_id":
                mascota.id,

            "estado_vinculo":
                vinculo.estado,

            "propietario": {
                "id":
                    propietario.id
                    if propietario
                    else None,

                "nombre":
                    propietario.nombre
                    if propietario
                    else "Propietario"
            }
        }

    }), 200

# ============================================================
# VETERINARIO - CONSULTAR MÃ“DULO CLÃNICO DEL PACIENTE
# ============================================================

@app.route(
    "/api/veterinario/pacientes/<int:mascota_id>/modulos/<string:modulo>",
    methods=["GET"]
)
def obtener_modulo_paciente_veterinario(
    mascota_id,
    modulo
):

    veterinario_id = session.get("usuario_id")
    rol = session.get("rol")


    if not veterinario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "veterinario":

        return jsonify({
            "ok": False,
            "mensaje":
                "Acceso exclusivo para veterinarios"
        }), 403


    # ========================================================
    # VALIDAR VÃNCULO ACTIVO
    # ========================================================

    vinculo = (
        VinculoVeterinarioMascota.query
        .filter_by(
            veterinario_id=veterinario_id,
            mascota_id=mascota_id,
            estado="Activo"
        )
        .first()
    )


    if not vinculo:

        return jsonify({
            "ok": False,
            "mensaje":
                "No tienes autorizaciÃ³n para consultar esta mascota"
        }), 403


    # ========================================================
    # VALIDAR MÃ“DULO
    # ========================================================

    modulo = str(
        modulo or ""
    ).strip().lower()


    if modulo not in MODULOS_MASCOTA_PERMITIDOS:

        return jsonify({
            "ok": False,
            "mensaje": "MÃ³dulo no permitido"
        }), 400


    # ========================================================
    # BUSCAR DATOS DEL DUEÃ‘O EN SQLITE
    # ========================================================

    registro = (
        DatosModuloMascota.query
        .filter_by(
            usuario_id=
                vinculo.propietario_id,

            mascota_id=
                mascota_id,

            modulo=
                modulo
        )
        .first()
    )


    if not registro:

        return jsonify({
            "ok": True,
            "existe": False,
            "mascota_id":
                mascota_id,
            "modulo":
                modulo,
            "datos":
                None
        }), 200


    try:

        datos = json.loads(
            registro.datos_json or "null"
        )

    except Exception:

        datos = None


    return jsonify({
        "ok": True,
        "existe": True,
        "mascota_id":
            mascota_id,
        "modulo":
            modulo,
        "datos":
            datos,
        "actualizado_en":
            (
                registro.actualizado_en.isoformat()
                if registro.actualizado_en
                else None
            )
    }), 200
# ============================================================
# VETERINARIO - GUARDAR MÃ“DULO CLÃNICO DEL PACIENTE
# ============================================================

@app.route(
    "/api/veterinario/pacientes/<int:mascota_id>/modulos/<string:modulo>",
    methods=["PUT", "POST"]
)
def guardar_modulo_paciente_veterinario(
    mascota_id,
    modulo
):

    veterinario_id = session.get("usuario_id")
    rol = session.get("rol")


    if not veterinario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "veterinario":

        return jsonify({
            "ok": False,
            "mensaje":
                "Acceso exclusivo para veterinarios"
        }), 403


    # ========================================================
    # VALIDAR VÃNCULO ACTIVO
    # ========================================================

    vinculo = (
        VinculoVeterinarioMascota.query
        .filter_by(
            veterinario_id=veterinario_id,
            mascota_id=mascota_id,
            estado="Activo"
        )
        .first()
    )


    if not vinculo:

        return jsonify({
            "ok": False,
            "mensaje":
                "No tienes autorizaciÃ³n para modificar esta mascota"
        }), 403


    modulo = str(
        modulo or ""
    ).strip().lower()


    if modulo not in MODULOS_MASCOTA_PERMITIDOS:

        return jsonify({
            "ok": False,
            "mensaje": "MÃ³dulo no permitido"
        }), 400


    datos_recibidos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    datos = datos_recibidos.get(
        "datos",
        datos_recibidos
    )


    try:

        datos_json = json.dumps(
            datos,
            ensure_ascii=False
        )

    except (TypeError, ValueError):

        return jsonify({
            "ok": False,
            "mensaje":
                "Los datos no se pueden guardar"
        }), 400


    registro = (
        DatosModuloMascota.query
        .filter_by(
            usuario_id=
                vinculo.propietario_id,

            mascota_id=
                mascota_id,

            modulo=
                modulo
        )
        .first()
    )


    if registro is None:

        registro = DatosModuloMascota(

            usuario_id=
                vinculo.propietario_id,

            mascota_id=
                mascota_id,

            modulo=
                modulo,

            datos_json=
                datos_json
        )

        db.session.add(
            registro
        )

    else:

        registro.datos_json = datos_json

        registro.actualizado_en =datetime.utcnow()


    db.session.commit()


    return jsonify({
        "ok": True,
        "mensaje":
            "Expediente actualizado correctamente",
        "mascota_id":
            mascota_id,
        "modulo":
            modulo,
        "datos":
            datos
    }), 200


    try:

        datos = json.loads(
            registro.datos_json or "null"
        )

    except Exception:

        datos = None


    return jsonify({
        "ok": True,
        "existe": True,
        "mascota_id": mascota_id,
        "modulo": modulo,
        "datos": datos,
        "actualizado_en":
            (
                registro.actualizado_en.isoformat()
                if registro.actualizado_en
                else None
            )
    }), 200
    
    # ============================================================
# DUEÃ‘O - VER SOLICITUDES DE VETERINARIOS
# ============================================================

@app.route(
    "/api/dueno/solicitudes-veterinario",
    methods=["GET"]
)
def listar_solicitudes_veterinario_dueno():

    propietario_id = session.get("usuario_id")
    rol = session.get("rol")

    if not propietario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    if rol != "dueno":
        return jsonify({
            "ok": False,
            "mensaje": "Esta funciÃ³n pertenece al perfil DueÃ±o / Tutor"
        }), 403


    vinculos = (
        VinculoVeterinarioMascota.query
        .filter_by(
            propietario_id=propietario_id,
            estado="Pendiente"
        )
        .order_by(
            VinculoVeterinarioMascota.fecha_solicitud.desc()
        )
        .all()
    )


    solicitudes = []


    for vinculo in vinculos:

        veterinario = db.session.get(
            Usuario,
            vinculo.veterinario_id
        )

        mascota = db.session.get(
            Mascota,
            vinculo.mascota_id
        )


        if not mascota:
            continue


        solicitudes.append({

            "vinculo_id":
                vinculo.id,

            "estado":
                vinculo.estado,

            "fecha_solicitud":
                (
                    vinculo.fecha_solicitud.isoformat()
                    if vinculo.fecha_solicitud
                    else None
                ),

            "veterinario": {

                "id":
                    veterinario.id
                    if veterinario
                    else None,

                "nombre":
                    veterinario.nombre
                    if veterinario
                    else "Veterinario",

                "cedula":
                    veterinario.cedula_profesional
                    if veterinario
                    else None

            },

            "mascota": {

                "id":
                    mascota.id,

                "nombre":
                    mascota.nombre,

                "huella_id":
                    mascota.huella_id,

                "especie":
                    mascota.especie,

                "raza":
                    mascota.raza

            }

        })


    return jsonify({

        "ok": True,

        "total":
            len(solicitudes),

        "solicitudes":
            solicitudes

    }), 200


# ============================================================
# DUEÃ‘O - ACEPTAR O RECHAZAR SOLICITUD
# ============================================================

@app.route(
    "/api/dueno/solicitudes-veterinario/<int:vinculo_id>/responder",
    methods=["POST"]
)
def responder_solicitud_veterinario(vinculo_id):

    propietario_id = session.get("usuario_id")
    rol = session.get("rol")


    if not propietario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "dueno":

        return jsonify({
            "ok": False,
            "mensaje": "Esta funciÃ³n pertenece al perfil DueÃ±o / Tutor"
        }), 403


    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    accion = str(
        datos.get(
            "accion",
            ""
        )
    ).strip().lower()


    if accion not in [
        "aceptar",
        "rechazar"
    ]:

        return jsonify({
            "ok": False,
            "mensaje": "AcciÃ³n no vÃ¡lida"
        }), 400


    vinculo = (
        VinculoVeterinarioMascota.query
        .filter_by(
            id=vinculo_id,
            propietario_id=propietario_id
        )
        .first()
    )


    if not vinculo:

        return jsonify({
            "ok": False,
            "mensaje": "Solicitud no encontrada"
        }), 404


    if vinculo.estado != "Pendiente":

        return jsonify({
            "ok": False,
            "mensaje": "Esta solicitud ya fue respondida"
        }), 409


    if accion == "aceptar":

        vinculo.estado = "Activo"
        vinculo.fecha_vinculacion = datetime.utcnow()

        mensaje = (
            "Veterinario vinculado correctamente"
        )

    else:

        vinculo.estado = "Rechazado"

        mensaje = (
            "Solicitud rechazada"
        )


    db.session.commit()


    return jsonify({

        "ok": True,

        "mensaje":
            mensaje,

        "vinculo":
            vinculo.to_dict()

    }), 200
    # ============================================================
# VETERINARIO - BUSCAR MASCOTA PARA SOLICITAR ACCESO
# ============================================================

@app.route(
    "/api/veterinario/solicitudes-acceso/buscar",
    methods=["GET"]
)
def buscar_mascota_para_solicitud_acceso():

    veterinario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not veterinario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "veterinario":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Veterinario"
        }), 403


    # ========================================================
    # RECIBIR ID HUELLA
    # ========================================================

    huella_id = str(

        request.args.get(
            "huella_id",
            ""
        )

    ).strip().upper()


    if not huella_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Ingresa el ID Huella de la mascota"
        }), 400


    # ========================================================
    # BUSCAR MASCOTA REAL EN SQLITE
    # ========================================================

    mascota = (

        Mascota.query

        .filter_by(
            huella_id=huella_id
        )

        .first()

    )


    if not mascota:

        return jsonify({
            "ok": False,
            "mensaje":
                "No existe una mascota con ese ID Huella"
        }), 404


    # ========================================================
    # BUSCAR PROPIETARIO
    # ========================================================

    propietario = db.session.get(

        Usuario,

        mascota.usuario_id

    )


    # ========================================================
    # COMPROBAR VÃNCULO EXISTENTE
    # ========================================================

    vinculo = (

        VinculoVeterinarioMascota.query

        .filter_by(

            veterinario_id=
                veterinario_id,

            mascota_id=
                mascota.id

        )

        .first()

    )


    estado_vinculo = (

        str(
            vinculo.estado
        ).strip()

        if (
            vinculo
            and
            vinculo.estado
        )

        else
        ""

    )


    # ========================================================
    # COMPROBAR SI YA ESTÃ AUTORIZADA
    # ========================================================

    ya_vinculada = (

        estado_vinculo.lower()
        ==
        "activo"

    )


    # ========================================================
    # COMPROBAR SOLICITUD PENDIENTE
    # ========================================================

    solicitud_pendiente = (

        estado_vinculo.lower()
        ==
        "pendiente"

    )


    # ========================================================
    # RESPUESTA
    #
    # IMPORTANTE:
    # SOLO SE ENVÃAN DATOS BÃSICOS.
    # NO SE ENVÃA EXPEDIENTE, VACUNAS,
    # TRATAMIENTOS NI INFORMACIÃ“N CLÃNICA.
    # ========================================================

    return jsonify({

        "ok":
            True,


        "mascota": {

            "id":
                mascota.id,


            "mascota_id":
                mascota.id,


            "nombre":
                mascota.nombre,


            "huella_id":
                mascota.huella_id,


            "especie":
                mascota.especie,


            "raza":
                mascota.raza,


            "tutor":

                (
                    propietario.nombre

                    if propietario

                    else
                    "Tutor de la mascota"
                ),


            "ya_vinculada":
                ya_vinculada,


            "solicitud_pendiente":
                solicitud_pendiente

        },


        "ya_vinculada":
            ya_vinculada,


        "solicitud_pendiente":
            solicitud_pendiente,


        "estado_vinculo":

            (
                estado_vinculo

                if estado_vinculo

                else None
            )

    }), 200



# ============================================================
# VETERINARIO - ENVIAR SOLICITUD DE ACCESO AL DUEÃ‘O
# ============================================================

@app.route(
    "/api/veterinario/solicitudes-acceso",
    methods=["POST"]
)

# ============================================================
# CONSERVAR COMPATIBILIDAD CON LA RUTA ANTERIOR
# ============================================================

@app.route(
    "/api/veterinario/vincular-paciente",
    methods=["POST"]
)

def solicitar_vinculacion_veterinario():

    veterinario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not veterinario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "veterinario":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Veterinario"
        }), 403


    # ========================================================
    # RECIBIR DATOS DEL FRONTEND
    # ========================================================

    datos = (

        request.get_json(
            silent=True
        )

        or {}

    )


    huella_id = str(

        datos.get(
            "huella_id",
            ""
        )

    ).strip().upper()


    mascota_id = datos.get(
        "mascota_id"
    )


    # ========================================================
    # LOCALIZAR MASCOTA
    # ========================================================

    mascota = None


    # ========================================================
    # BUSCAR PRIMERO POR ID INTERNO
    # ========================================================

    if mascota_id not in [
        None,
        ""
    ]:

        try:

            mascota_id = int(
                mascota_id
            )

        except (
            TypeError,
            ValueError
        ):

            return jsonify({
                "ok": False,
                "mensaje":
                    "El ID de la mascota no es vÃ¡lido"
            }), 400


        mascota = db.session.get(

            Mascota,

            mascota_id

        )


    # ========================================================
    # SI NO SE ENCONTRÃ“ POR ID,
    # BUSCAR POR ID HUELLA
    # ========================================================

    if (
        mascota is None
        and
        huella_id
    ):

        mascota = (

            Mascota.query

            .filter_by(
                huella_id=huella_id
            )

            .first()

        )


    # ========================================================
    # MASCOTA NO ENCONTRADA
    # ========================================================

    if not mascota:

        return jsonify({
            "ok": False,
            "mensaje":
                "No existe una mascota con ese ID Huella"
        }), 404


    # ========================================================
    # SI EL FRONTEND MANDÃ“
    # mascota_id + huella_id,
    # COMPROBAR QUE SEAN LA MISMA MASCOTA
    # ========================================================

    if (
        huella_id

        and

        str(
            mascota.huella_id
            or
            ""
        ).strip().upper()

        !=

        huella_id
    ):

        return jsonify({
            "ok": False,
            "mensaje":
                (
                    "El ID Huella no corresponde "
                    "a la mascota seleccionada"
                )
        }), 400


    # ========================================================
    # PROPIETARIO REAL
    # ========================================================

    propietario_id = (
        mascota.usuario_id
    )


    if not propietario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                (
                    "La mascota no tiene "
                    "un propietario asociado"
                )
        }), 409


    # ========================================================
    # COMPROBAR SI YA EXISTE UN VÃNCULO
    # ========================================================

    vinculo = (

        VinculoVeterinarioMascota.query

        .filter_by(

            veterinario_id=
                veterinario_id,

            mascota_id=
                mascota.id

        )

        .first()

    )


    # ========================================================
    # YA EXISTE ALGÃšN VÃNCULO
    # ========================================================

    if vinculo:

        estado_actual = str(

            vinculo.estado
            or
            ""

        ).strip().lower()


        # ====================================================
        # YA ESTÃ AUTORIZADO
        # ====================================================

        if estado_actual == "activo":

            return jsonify({

                "ok":
                    False,


                "mensaje":
                    (
                        "Ya tienes acceso autorizado "
                        "a esta mascota"
                    ),


                "ya_vinculada":
                    True,


                "solicitud_pendiente":
                    False,


                "vinculo":
                    vinculo.to_dict()

            }), 409


        # ====================================================
        # YA HAY SOLICITUD PENDIENTE
        # ====================================================

        if estado_actual == "pendiente":

            return jsonify({

                "ok":
                    False,


                "mensaje":
                    (
                        "Ya existe una solicitud "
                        "pendiente para esta mascota"
                    ),


                "ya_vinculada":
                    False,


                "solicitud_pendiente":
                    True,


                "vinculo":
                    vinculo.to_dict()

            }), 409


        # ====================================================
        # SI FUE RECHAZADA O REVOCADA,
        # PERMITIR CREAR NUEVA SOLICITUD
        # ====================================================

        vinculo.propietario_id = (
            propietario_id
        )


        vinculo.estado = (
            "Pendiente"
        )


        vinculo.fecha_solicitud = (
            datetime.utcnow()
        )


        vinculo.fecha_vinculacion = (
            None
        )


    # ========================================================
    # NO EXISTÃA VÃNCULO
    # ========================================================

    else:

        vinculo = (
            VinculoVeterinarioMascota(

                veterinario_id=
                    veterinario_id,

                propietario_id=
                    propietario_id,

                mascota_id=
                    mascota.id,

                estado=
                    "Pendiente"

            )
        )


        db.session.add(
            vinculo
        )


    # ========================================================
    # GUARDAR SOLICITUD EN SQLITE
    # ========================================================

    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR CREANDO SOLICITUD VETERINARIA:",
            error
        )


        return jsonify({

            "ok":
                False,


            "mensaje":
                (
                    "No fue posible enviar "
                    "la solicitud al dueÃ±o"
                )

        }), 500


    # ========================================================
    # CONSULTAR PROPIETARIO PARA RESPUESTA
    # ========================================================

    propietario = db.session.get(

        Usuario,

        propietario_id

    )


    # ========================================================
    # RESPUESTA FINAL
    # ========================================================

    return jsonify({

        "ok":
            True,


        "mensaje":
            "Solicitud enviada al dueÃ±o de la mascota",


        "solicitud_pendiente":
            True,


        "ya_vinculada":
            False,


        "mascota": {

            "id":
                mascota.id,


            "mascota_id":
                mascota.id,


            "nombre":
                mascota.nombre,


            "huella_id":
                mascota.huella_id,


            "especie":
                mascota.especie,


            "raza":
                mascota.raza,


            "tutor":

                (
                    propietario.nombre

                    if propietario

                    else
                    "Tutor de la mascota"
                )

        },


        "vinculo":
            vinculo.to_dict()

    }), 201
    
    
    
    # ============================================================
# VETERINARIO - RESUMEN DEL PORTAL
# ============================================================

@app.route(
    "/api/veterinario/resumen",
    methods=["GET"]
)
def resumen_portal_veterinario():

    veterinario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not veterinario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "veterinario":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Veterinario"
        }), 403


    veterinario = db.session.get(
        Usuario,
        veterinario_id
    )


    if not veterinario:

        return jsonify({
            "ok": False,
            "mensaje": "Veterinario no encontrado"
        }), 404


    # ========================================================
    # PACIENTES VINCULADOS
    # ========================================================

    vinculos = (

        VinculoVeterinarioMascota.query

        .filter_by(
            veterinario_id=veterinario_id,
            estado="Activo"
        )

        .order_by(
            VinculoVeterinarioMascota.creado_en.desc()
        )

        .all()

    )


    pacientes = []


    for vinculo in vinculos:

        mascota = db.session.get(
            Mascota,
            vinculo.mascota_id
        )


        if not mascota:

            continue


        propietario = db.session.get(
            Usuario,
            vinculo.propietario_id
        )


        pacientes.append({

            **mascota.to_dict(),

            "mascota_id":
                mascota.id,

            "tutor":
                (
                    propietario.nombre
                    if propietario
                    else "Propietario"
                ),

            "propietario": {

                "id":
                    propietario.id
                    if propietario
                    else None,

                "nombre":
                    propietario.nombre
                    if propietario
                    else "Propietario"

            },

            "estado_vinculo":
                vinculo.estado

        })


    # ========================================================
    # LISTAS GENERALES
    # ========================================================

    citas = []

    citas_hoy = []

    telemedicina = []

    alertas = []


    hoy = datetime.now().strftime(
        "%Y-%m-%d"
    )


    # ========================================================
    # LEER MÃ“DULOS DE CADA PACIENTE
    # ========================================================

    for vinculo in vinculos:

        mascota = db.session.get(
            Mascota,
            vinculo.mascota_id
        )


        if not mascota:

            continue


        propietario = db.session.get(
            Usuario,
            vinculo.propietario_id
        )


        tutor_nombre = (
            propietario.nombre
            if propietario
            else "Propietario"
        )


        # ====================================================
        # CITAS
        # ====================================================

        registro_citas = (

            DatosModuloMascota.query

            .filter_by(
                usuario_id=vinculo.propietario_id,
                mascota_id=mascota.id,
                modulo="citas"
            )

            .first()

        )


        if registro_citas:

            try:

                datos_citas = json.loads(
                    registro_citas.datos_json
                    or
                    "[]"
                )

            except Exception:

                datos_citas = []


            if isinstance(
                datos_citas,
                dict
            ):

                datos_citas = (
                    datos_citas.get("citas")
                    or
                    datos_citas.get("items")
                    or
                    datos_citas.get("registros")
                    or
                    []
                )


            if not isinstance(
                datos_citas,
                list
            ):

                datos_citas = []


            for cita in datos_citas:

                if not isinstance(
                    cita,
                    dict
                ):

                    continue


                item = dict(
                    cita
                )


                item["mascota_id"] = (
                    mascota.id
                )


                item["mascota"] = (
                    mascota.nombre
                )


                item["tutor"] = (
                    tutor_nombre
                )


                citas.append(
                    item
                )


                if (
                    str(
                        item.get(
                            "fecha",
                            ""
                        )
                    )
                    ==
                    hoy
                ):

                    citas_hoy.append(
                        item
                    )


        # ====================================================
        # TELEMEDICINA
        # ====================================================

        registro_telemedicina = (

            DatosModuloMascota.query

            .filter_by(
                usuario_id=vinculo.propietario_id,
                mascota_id=mascota.id,
                modulo="telemedicina"
            )

            .first()

        )


        if registro_telemedicina:

            try:

                datos_tele = json.loads(
                    registro_telemedicina.datos_json
                    or
                    "[]"
                )

            except Exception:

                datos_tele = []


            if isinstance(
                datos_tele,
                dict
            ):

                datos_tele = (
                    datos_tele.get("solicitudes")
                    or
                    datos_tele.get("items")
                    or
                    datos_tele.get("registros")
                    or
                    []
                )


            if not isinstance(
                datos_tele,
                list
            ):

                datos_tele = []


            for solicitud in datos_tele:

                if not isinstance(
                    solicitud,
                    dict
                ):

                    continue


                item = dict(
                    solicitud
                )


                item["mascota_id"] = (
                    mascota.id
                )


                item["mascota"] = (
                    mascota.nombre
                )


                telemedicina.append(
                    item
                )


    # ========================================================
    # RESPUESTA FINAL
    # ========================================================

    return jsonify({

        "ok":
            True,


        "veterinario": {

            "id":
                veterinario.id,

            "nombre":
                veterinario.nombre,

            "correo":
                veterinario.correo

        },


        "pacientes":
            pacientes,


        "citas":
            citas,


        "citas_hoy":
            citas_hoy,


        "telemedicina":
            telemedicina,


        "alertas":
            alertas,


        "resumen": {

            "pacientes":
                len(pacientes),

            "citas_hoy":
                len(citas_hoy),

            "telemedicina":
                len(telemedicina),

            "alertas":
                len(alertas)

        }

    }), 200
    
    # ============================================================
# FINALIZAR VIDEOLLAMADA PARA TODOS LOS PARTICIPANTES
# ============================================================

@socketio.on(
    "end-video-room"
)
def finalizar_videollamada(datos):

    usuario_id = session.get(
        "usuario_id"
    )

    if not usuario_id:
        return


    sala = obtener_sala_video(
        datos
    )

    if not sala:
        return


    consultation_id = (
        datos or {}
    ).get(
        "consultation_id"
    )


    duration_seconds = (
        datos or {}
    ).get(
        "duration_seconds",
        0
    )


    try:

        duration_seconds = int(
            duration_seconds
        )

    except:

        duration_seconds = 0


    if duration_seconds < 0:
        duration_seconds = 0


    print(
        "Videollamada finalizada:",
        sala,
        "por usuario:",
        usuario_id,
        "duraciÃ³n:",
        duration_seconds,
        "segundos"
    )


    # Avisar a la otra persona
    emit(
        "video-room-ended",
        {
            "room":
                sala,

            "consultation_id":
                consultation_id,

            "duration_seconds":
                duration_seconds
        },
        to=sala,
        include_self=False
    )


    # El usuario que finalizÃ³ sale de la sala
    leave_room(
        sala
    )
    

# ============================================================
# SOCKET.IO - VIDEOLLAMADAS WEBRTC
# ============================================================

def obtener_sala_video(datos):

    datos = datos or {}

    sala = str(
        datos.get(
            "room",
            ""
        )
    ).strip()

    if not sala:
        return None

    if not sala.startswith(
        "teleconsulta-"
    ):
        return None

    if len(sala) > 100:
        return None

    return sala


# ============================================================
# ENTRAR A SALA
# ============================================================

@socketio.on(
    "join-video-room"
)
def entrar_sala_video(datos):

    usuario_id = session.get(
        "usuario_id"
    )

    if not usuario_id:
        return

    sala = obtener_sala_video(
        datos
    )

    if not sala:
        return

    join_room(
        sala
    )

    print(
        "Usuario",
        usuario_id,
        "entrÃ³ a:",
        sala
    )

    emit(
        "user-joined",
        {
            "room": sala
        },
        to=sala,
        include_self=False
    )


# ============================================================
# SALIR DE SALA
# ============================================================

@socketio.on(
    "leave-video-room"
)
def salir_sala_video(datos):

    usuario_id = session.get(
        "usuario_id"
    )

    if not usuario_id:
        return

    sala = obtener_sala_video(
        datos
    )

    if not sala:
        return

    leave_room(
        sala
    )

    print(
        "Usuario",
        usuario_id,
        "saliÃ³ de:",
        sala
    )

    emit(
        "user-left",
        {
            "room": sala
        },
        to=sala,
        include_self=False
    )


# ============================================================
# WEBRTC - OFERTA
# ============================================================

@socketio.on(
    "webrtc-offer"
)
def enviar_oferta_webrtc(datos):

    if not session.get(
        "usuario_id"
    ):
        return

    sala = obtener_sala_video(
        datos
    )

    oferta = (
        datos or {}
    ).get(
        "offer"
    )

    if (
        not sala
        or not oferta
    ):
        return

    emit(
        "webrtc-offer",
        {
            "room": sala,
            "offer": oferta
        },
        to=sala,
        include_self=False
    )


# ============================================================
# WEBRTC - RESPUESTA
# ============================================================

@socketio.on(
    "webrtc-answer"
)
def enviar_respuesta_webrtc(datos):

    if not session.get(
        "usuario_id"
    ):
        return

    sala = obtener_sala_video(
        datos
    )

    respuesta = (
        datos or {}
    ).get(
        "answer"
    )

    if (
        not sala
        or not respuesta
    ):
        return

    emit(
        "webrtc-answer",
        {
            "room": sala,
            "answer": respuesta
        },
        to=sala,
        include_self=False
    )


# ============================================================
# WEBRTC - ICE CANDIDATE
# ============================================================

@socketio.on(
    "webrtc-ice-candidate"
)
def enviar_ice_candidate(datos):

    if not session.get(
        "usuario_id"
    ):
        return

    sala = obtener_sala_video(
        datos
    )

    candidato = (
        datos or {}
    ).get(
        "candidate"
    )

    if (
        not sala
        or not candidato
    ):
        return

    emit(
        "webrtc-ice-candidate",
        {
            "room": sala,
            "candidate": candidato
        },
        to=sala,
        include_self=False
    )


# ============================================================
# PÃGINA PRINCIPAL
# ============================================================

@app.route("/")
def inicio():

    return send_from_directory(

        str(BASE_DIR),

        "index.html"

    )

# ============================================================
# CARPETA DONDE ESTÃ APP.PY
# ============================================================

BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

# ============================================================
# LOGIN
# ============================================================

@app.route("/login")
def pagina_login():

    return send_from_directory(
        str(BASE_DIR),
        "login.html"
    )


# ============================================================
# REGISTRO
# ============================================================

@app.route("/registro")
def pagina_registro():

    return send_from_directory(
        str(BASE_DIR),
        "registro.html"
    )


# ============================================================
# COMPATIBILIDAD LOGIN.HTML
# ============================================================

@app.route("/login.html")
def pagina_login_html():

    return redirect(
        "/login"
    )


# ============================================================
# COMPATIBILIDAD REGISTRO.HTML
# ============================================================

# ============================================================
# PASAPORTE BIOMÃ‰TRICO PÃšBLICO
# MISMO DISEÃ‘O QUE EL PASAPORTE DEL DUEÃ‘O
# ============================================================

@app.route("/pasaporte-publico")
def pasaporte_publico():

    return send_from_directory(

        str(
            BASE_DIR
            / "perfiles"
            / "dueno"
        ),

        "pasaporte-biometrico.html"

    )
    
    
    
    # ============================================================
# CARNET DIGITAL COMPARTIDO
# DUEÃ‘O + VETERINARIO
# ============================================================

@app.route("/carnet")
@app.route("/carnet.html")
def carnet_digital_compartido():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )

    if not usuario_id:

        return redirect(
            "/login"
        )

    if rol not in [
        "dueno",
        "veterinario"
    ]:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Esta funciÃ³n solo estÃ¡ disponible para DueÃ±o y Veterinario"

        }), 403


    return send_from_directory(

        str(
            BASE_DIR
            /
            "perfiles" / "dueno"
        ),

        "carnet.html"

    )


# ============================================================
# DUEÃ‘O - VETERINARIO ACTIVO DE UNA MASCOTA
# ============================================================

@app.route(
    "/api/dueno/mascotas/<int:mascota_id>/veterinario-activo",
    methods=["GET"]
)
def obtener_veterinario_activo_mascota(
    mascota_id
):

    propietario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not propietario_id:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    if rol != "dueno":

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Esta funciÃ³n pertenece al DueÃ±o / Tutor"

        }), 403


    mascota = (
        Mascota.query
        .filter_by(
            id=mascota_id,
            usuario_id=propietario_id
        )
        .first()
    )


    if not mascota:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Mascota no encontrada"

        }), 404


    vinculo = (
        VinculoVeterinarioMascota.query
        .filter_by(
            propietario_id=propietario_id,
            mascota_id=mascota_id,
            estado="Activo"
        )
        .order_by(
            VinculoVeterinarioMascota.fecha_vinculacion.desc()
        )
        .first()
    )


    if not vinculo:

        return jsonify({

            "ok":
                True,

            "vinculado":
                False,

            "veterinario":
                None

        }), 200


    veterinario = db.session.get(
        Usuario,
        vinculo.veterinario_id
    )


    if not veterinario:

        return jsonify({

            "ok":
                True,

            "vinculado":
                False,

            "veterinario":
                None

        }), 200


    return jsonify({

        "ok":
            True,

        "vinculado":
            True,

        "veterinario": {

            "id":
                veterinario.id,

            "nombre":
                veterinario.nombre,

            "correo":
                veterinario.correo,

            "telefono":
                veterinario.telefono,

            "cedula":
                veterinario.cedula_profesional,

            "fecha_vinculacion":
                (
                    vinculo.fecha_vinculacion.isoformat()
                    if vinculo.fecha_vinculacion
                    else None
                )

        }

    }), 200
    
  
# ============================================================
# SERVIR ARCHIVOS DE PERFILES
# ============================================================

@app.route("/<path:ruta>")
def archivos(ruta):

    # ========================================================
    # PROTEGER PÃGINAS PRIVADAS
    # ========================================================

    if ruta.startswith("perfiles/"):

        usuario_id = session.get(
            "usuario_id"
        )

        rol = session.get(
            "rol"
        )

        if (
            not usuario_id
            or
            not rol
        ):

            return redirect(
                "/login"
            )


        paginas_por_rol = {

            "dueno": [
                "perfiles/dueno.html",
                "perfiles/dueno/"
            ],

            "veterinario": [
                "perfiles/veterinario.html",
                "perfiles/veterinario/"
            ],

            "proveedor": [
                "perfiles/proveedor.html",
                "perfiles/proveedor/"
            ],

            "administrador": [
                "perfiles/administrador.html",
                "perfiles/administrador/"
            ]

        }


        rutas_permitidas = (
            paginas_por_rol.get(
                rol,
                []
            )
        )


        permitido = any(

            ruta == ruta_permitida

            or

            (
                ruta_permitida.endswith("/")
                and
                ruta.startswith(
                    ruta_permitida
                )
            )

            for ruta_permitida
            in rutas_permitidas

        )


        if not permitido:

            destinos = {

                "dueno":
                    "/perfiles/dueno.html",

                "veterinario":
                    "/perfiles/veterinario.html",

                "proveedor":
                    "/perfiles/proveedor.html",

                "administrador":
                    "/perfiles/administrador.html"

            }


            return redirect(

                destinos.get(
                    rol,
                    "/"
                )

            )


        # ====================================================
        # BUSCAR EL ARCHIVO DENTRO DE BACKEND
        # ====================================================

        archivo_perfil = (
            BACKEND_DIR
            /
            ruta
        )


        if (
            archivo_perfil.exists()
            and
            archivo_perfil.is_file()
        ):

            return send_from_directory(

                str(
                    BACKEND_DIR
                ),

                ruta

            )


    # ========================================================
    # SERVIR ARCHIVOS DE LA RAÃZ
    # ========================================================

    archivo = (
        BASE_DIR
        /
        ruta
    )


    if (
        archivo.exists()
        and
        archivo.is_file()
    ):

        return send_from_directory(

            str(
                BASE_DIR
            ),

            ruta

        )


    # ========================================================
    # NO ENCONTRADO
    # ========================================================

    return jsonify({

        "ok":
            False,

        "error":
            "Archivo no encontrado"

    }), 404

# ============================================================
# PERFIL REAL DEL PROVEEDOR
# ============================================================


def obtener_perfil_proveedor(
    usuario_id
):

    perfil = (
        PerfilProveedor.query
        .filter_by(
            proveedor_id=usuario_id
        )
        .first()
    )


    if perfil:

        return perfil


    usuario = db.session.get(
        Usuario,
        usuario_id
    )


    perfil = PerfilProveedor(

        proveedor_id=
            usuario_id,

        nombre_comercial=
            (
                usuario.nombre
                if usuario
                else "Mi comercio Huella"
            ),

        correo=
            (
                usuario.correo
                if usuario
                else ""
            ),

        telefono=
            (
                usuario.telefono
                if usuario
                else ""
            ),

        categoria=
            "Tienda de mascotas",

        descripcion=
            (
                "Negocio registrado como proveedor "
                "dentro de Huella."
            ),

        horario_semana=
            "09:00 - 18:00",

        horario_sabado=
            "10:00 - 15:00",

        horario_domingo=
            "Cerrado",

        entrega_domicilio=
            True,

        recoger_tienda=
            True,

        pago_electronico=
            True,

        notificaciones=
            True

    )


    db.session.add(
        perfil
    )

    db.session.commit()


    return perfil



# ============================================================
# PROVEEDOR - CONSULTAR PERFIL
# ============================================================

@app.route(
    "/api/proveedor/perfil",
    methods=["GET"]
)
def proveedor_obtener_perfil():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "proveedor":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403


    try:

        perfil = obtener_perfil_proveedor(
            usuario_id
        )


        return jsonify({

            "ok":
                True,

            "perfil":
                perfil.to_dict()

        }), 200


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR CONSULTANDO PERFIL PROVEEDOR:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible cargar el perfil del proveedor"

        }), 500



# ============================================================
# PROVEEDOR - ACTUALIZAR PERFIL
# ============================================================

@app.route(
    "/api/proveedor/perfil",
    methods=[
        "PUT",
        "POST"
    ]
)
def proveedor_actualizar_perfil():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "proveedor":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403


    datos = (
        request.get_json(
            silent=True
        )
        or
        {}
    )


    try:

        perfil = obtener_perfil_proveedor(
            usuario_id
        )


        nombre = str(
            datos.get(
                "nombre",
                datos.get(
                    "nombre_comercial",
                    perfil.nombre_comercial
                )
            )
            or
            ""
        ).strip()


        if not nombre:

            return jsonify({
                "ok": False,
                "mensaje":
                    "El nombre comercial es obligatorio"
            }), 400


        perfil.nombre_comercial = (
            nombre
        )


        perfil.categoria = str(
            datos.get(
                "categoria",
                perfil.categoria
                or ""
            )
            or
            ""
        ).strip()


        perfil.telefono = str(
            datos.get(
                "telefono",
                perfil.telefono
                or ""
            )
            or
            ""
        ).strip()


        perfil.correo = str(
            datos.get(
                "correo",
                perfil.correo
                or ""
            )
            or
            ""
        ).strip()


        perfil.ubicacion = str(
            datos.get(
                "ubicacion",
                perfil.ubicacion
                or ""
            )
            or
            ""
        ).strip()


        perfil.direccion = str(
            datos.get(
                "direccion",
                perfil.direccion
                or ""
            )
            or
            ""
        ).strip()


        perfil.descripcion = str(
            datos.get(
                "descripcion",
                perfil.descripcion
                or ""
            )
            or
            ""
        ).strip()


        perfil.logo = str(
            datos.get(
                "logo",
                perfil.logo
                or ""
            )
            or
            ""
        )


        perfil.horario_semana = str(
            datos.get(
                "horarioSemana",
                perfil.horario_semana
                or ""
            )
            or
            ""
        ).strip()


        perfil.horario_sabado = str(
            datos.get(
                "horarioSabado",
                perfil.horario_sabado
                or ""
            )
            or
            ""
        ).strip()


        perfil.horario_domingo = str(
            datos.get(
                "horarioDomingo",
                perfil.horario_domingo
                or ""
            )
            or
            ""
        ).strip()


        if (
            "entrega"
            in datos
        ):

            perfil.entrega_domicilio = bool(
                datos.get(
                    "entrega"
                )
            )


        if (
            "recoger"
            in datos
        ):

            perfil.recoger_tienda = bool(
                datos.get(
                    "recoger"
                )
            )


        if (
            "pagoElectronico"
            in datos
        ):

            perfil.pago_electronico = bool(
                datos.get(
                    "pagoElectronico"
                )
            )


        if (
            "notificaciones"
            in datos
        ):

            perfil.notificaciones = bool(
                datos.get(
                    "notificaciones"
                )
            )


        perfil.actualizado_en = (
            datetime.utcnow()
        )


        db.session.commit()


        return jsonify({

            "ok":
                True,

            "mensaje":
                "Perfil comercial actualizado correctamente",

            "perfil":
                perfil.to_dict()

        }), 200


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR ACTUALIZANDO PERFIL PROVEEDOR:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible actualizar el perfil comercial"

        }), 500



# ============================================================
# COMERCIO - PRODUCTOS DEL PROVEEDOR
# ============================================================

@app.route(
    "/api/proveedor/productos",
    methods=["GET"]
)
def proveedor_listar_productos():

    usuario_id = session.get("usuario_id")
    rol = session.get("rol")

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    if rol != "proveedor":
        return jsonify({
            "ok": False,
            "mensaje": "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403

    productos = (
        ProductoProveedor.query
        .filter_by(
            proveedor_id=usuario_id
        )
        .order_by(
            ProductoProveedor.creado_en.desc()
        )
        .all()
    )

    return jsonify({
        "ok": True,
        "total": len(productos),
        "productos": [
            producto.to_dict()
            for producto in productos
        ]
    }), 200


# ============================================================
# PROVEEDOR - CREAR PRODUCTO
# ============================================================

@app.route(
    "/api/proveedor/productos",
    methods=["POST"]
)
def proveedor_crear_producto():

    usuario_id = session.get("usuario_id")
    rol = session.get("rol")

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    if rol != "proveedor":
        return jsonify({
            "ok": False,
            "mensaje": "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403

    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )

    nombre = str(
        datos.get(
            "nombre",
            ""
        )
    ).strip()

    categoria = str(
        datos.get(
            "categoria",
            "Otro"
        )
    ).strip()

    descripcion = str(
        datos.get(
            "descripcion",
            ""
        )
    ).strip()

    estado = str(
        datos.get(
            "estado",
            "Activo"
        )
    ).strip()

    imagen = str(
        datos.get(
            "imagen",
            ""
        )
    ).strip()

    if not nombre:

        return jsonify({
            "ok": False,
            "mensaje":
                "El nombre del producto es obligatorio"
        }), 400

    try:

        precio = float(
            datos.get(
                "precio",
                0
            )
        )

    except (TypeError, ValueError):

        return jsonify({
            "ok": False,
            "mensaje":
                "El precio no es vÃ¡lido"
        }), 400

    try:

        stock = int(
            datos.get(
                "stock",
                0
            )
        )

    except (TypeError, ValueError):

        return jsonify({
            "ok": False,
            "mensaje":
                "Las existencias no son vÃ¡lidas"
        }), 400

    if precio < 0:

        return jsonify({
            "ok": False,
            "mensaje":
                "El precio no puede ser negativo"
        }), 400

    if stock < 0:

        return jsonify({
            "ok": False,
            "mensaje":
                "Las existencias no pueden ser negativas"
        }), 400

    if estado not in [
        "Activo",
        "Inactivo"
    ]:

        estado = "Activo"

    producto = ProductoProveedor(

        proveedor_id=
            usuario_id,

        nombre=
            nombre,

        categoria=
            categoria or "Otro",

        descripcion=
            descripcion,

        precio=
            precio,

        stock=
            stock,

        estado=
            estado,

        imagen=
            imagen or None

    )

    try:

        db.session.add(
            producto
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "ERROR AL CREAR PRODUCTO:",
            error
        )

        return jsonify({
            "ok": False,
            "mensaje":
                "No fue posible guardar el producto"
        }), 500

    return jsonify({
        "ok": True,
        "mensaje":
            "Producto registrado correctamente",
        "producto":
            producto.to_dict()
    }), 201


# ============================================================
# PROVEEDOR - EDITAR PRODUCTO
# ============================================================

@app.route(
    "/api/proveedor/productos/<int:producto_id>",
    methods=["PUT"]
)
def proveedor_editar_producto(producto_id):

    usuario_id = session.get("usuario_id")
    rol = session.get("rol")

    if not usuario_id:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    if rol != "proveedor":
        return jsonify({
            "ok": False,
            "mensaje": "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403

    producto = (
        ProductoProveedor.query
        .filter_by(
            id=producto_id,
            proveedor_id=usuario_id
        )
        .first()
    )

    if not producto:
        return jsonify({
            "ok": False,
            "mensaje": "Producto no encontrado"
        }), 404

    datos = request.get_json(silent=True) or {}

    nombre = str(
        datos.get(
            "nombre",
            producto.nombre
        )
    ).strip()

    categoria = str(
        datos.get(
            "categoria",
            producto.categoria
        )
    ).strip()

    descripcion = str(
        datos.get(
            "descripcion",
            producto.descripcion or ""
        )
    ).strip()

    estado = str(
        datos.get(
            "estado",
            producto.estado
        )
    ).strip()

    imagen = str(
        datos.get(
            "imagen",
            producto.imagen or ""
        )
    ).strip()

    if not nombre:
        return jsonify({
            "ok": False,
            "mensaje": "El nombre es obligatorio"
        }), 400

    try:
        precio = float(
            datos.get(
                "precio",
                producto.precio
            )
        )
    except (TypeError, ValueError):
        return jsonify({
            "ok": False,
            "mensaje": "Precio no vÃ¡lido"
        }), 400

    try:
        stock = int(
            datos.get(
                "stock",
                producto.stock
            )
        )
    except (TypeError, ValueError):
        return jsonify({
            "ok": False,
            "mensaje": "Existencias no vÃ¡lidas"
        }), 400

    if precio < 0 or stock < 0:
        return jsonify({
            "ok": False,
            "mensaje":
                "Precio y existencias no pueden ser negativos"
        }), 400

    producto.nombre = nombre
    producto.categoria = categoria or "Otro"
    producto.descripcion = descripcion
    producto.precio = precio
    producto.stock = stock
    producto.estado = (
        estado
        if estado in ["Activo", "Inactivo"]
        else "Activo"
    )
    producto.imagen = imagen or None
    producto.actualizado_en = datetime.utcnow()

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "ERROR AL EDITAR PRODUCTO:",
            error
        )

        return jsonify({
            "ok": False,
            "mensaje":
                "No fue posible actualizar el producto"
        }), 500

    return jsonify({
        "ok": True,
        "mensaje":
            "Producto actualizado correctamente",
        "producto":
            producto.to_dict()
    }), 200

# ============================================================
# PROVEEDOR - ELIMINAR PRODUCTO
# PROTEGE PRODUCTOS QUE YA TIENEN HISTORIAL DE PEDIDOS
# ============================================================

@app.route(
    "/api/proveedor/productos/<int:producto_id>",
    methods=["DELETE"]
)
def proveedor_eliminar_producto(producto_id):

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not usuario_id:

        return jsonify({

            "ok": False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "proveedor":

        return jsonify({

            "ok": False,

            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"

        }), 403


    # ========================================================
    # BUSCAR PRODUCTO DEL PROVEEDOR
    # ========================================================

    producto = (

        ProductoProveedor.query

        .filter_by(

            id=producto_id,

            proveedor_id=usuario_id

        )

        .first()

    )


    if not producto:

        return jsonify({

            "ok": False,

            "mensaje":
                "Producto no encontrado"

        }), 404


    # ========================================================
    # COMPROBAR SI EL PRODUCTO YA APARECE EN UN PEDIDO
    # ========================================================

    detalle_existente = (

        DetallePedido.query

        .filter_by(

            producto_id=producto_id

        )

        .first()

    )


    # ========================================================
    # SI TIENE HISTORIAL, NO SE DEBE ELIMINAR
    # ========================================================

    if detalle_existente:

        return jsonify({

            "ok": False,

            "mensaje":
                (
                    "Este producto ya tiene historial de pedidos "
                    "y no puede eliminarse. "
                    "Puedes editarlo y cambiar su estado a Inactivo."
                )

        }), 409


    # ========================================================
    # ELIMINAR SOLO SI NUNCA HA SIDO COMPRADO
    # ========================================================

    try:

        db.session.delete(
            producto
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR AL ELIMINAR PRODUCTO:",
            error
        )


        return jsonify({

            "ok": False,

            "mensaje":
                "No fue posible eliminar el producto"

        }), 500


    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({

        "ok": True,

        "mensaje":
            "Producto eliminado correctamente"

    }), 200
# ============================================================
# DUEÃ‘O - LISTAR PEDIDOS REALES
# ============================================================

@app.route(
    "/api/dueno/pedidos",
    methods=["GET"]
)
def dueno_listar_pedidos():

    usuario_id = session.get("usuario_id")
    rol = session.get("rol")

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "dueno":

        return jsonify({
            "ok": False,
            "mensaje": "Esta funciÃ³n pertenece al perfil DueÃ±o"
        }), 403


    # --------------------------------------------------------
    # FILTRO OPCIONAL POR MASCOTA
    # --------------------------------------------------------

    mascota_id = request.args.get(
        "mascota_id",
        type=int
    )


    query = (
        Pedido.query
        .filter_by(
            comprador_id=usuario_id
        )
    )


    if mascota_id:

        # Comprobar que la mascota pertenece al dueÃ±o.
        mascota_propietario = (
            Mascota.query
            .filter_by(
                id=mascota_id,
                usuario_id=usuario_id
            )
            .first()
        )

        if not mascota_propietario:

            return jsonify({
                "ok": False,
                "mensaje": "La mascota no pertenece al usuario"
            }), 403


        query = query.filter_by(
            mascota_id=mascota_id
        )


    pedidos = (
        query
        .order_by(
            Pedido.creado_en.desc()
        )
        .all()
    )


    resultado = []


    for pedido in pedidos:

        detalles = (
            DetallePedido.query
            .filter_by(
                pedido_id=pedido.id
            )
            .all()
        )


        mascota = None


        if pedido.mascota_id:

            mascota = db.session.get(
                Mascota,
                pedido.mascota_id
            )


        datos = pedido.to_dict()


        datos["mascota"] = (
            mascota.nombre
            if mascota
            else ""
        )


        datos["productos"] = [
            detalle.to_dict()
            for detalle in detalles
        ]


        resultado.append(
            datos
        )


    return jsonify({
        "ok": True,
        "total": len(resultado),
        "pedidos": resultado
    }), 200

# ============================================================
# ENVIAR SMS DE CONFIRMACIÃ“N DEL PEDIDO
# ============================================================

def enviar_sms_pedido(
    telefono,
    numero,
    total
):

    client = get_twilio_client()

    if not client:

        print(
            "SMS PEDIDO: Twilio no estÃ¡ configurado."
        )

        return False


    if not TWILIO_PHONE_NUMBER:

        print(
            "SMS PEDIDO: falta TWILIO_PHONE_NUMBER."
        )

        return False


    telefono_destino = normalizar_telefono_mexico(
        telefono
    )


    if not telefono_destino:

        print(
            "SMS PEDIDO: telÃ©fono no vÃ¡lido."
        )

        return False


    mensaje = (
        "Huella - Pedido "
        +
        str(numero)
        +
        " registrado correctamente. "
        +
        "Total: $"
        +
        format(
            float(total),
            ".2f"
        )
        +
        " MXN."
    )


    try:

        mensaje_twilio = (
            client
            .messages
            .create(
                body=mensaje,
                from_=TWILIO_PHONE_NUMBER,
                to=telefono_destino
            )
        )


        print(
            "SMS ENVIADO:",
            mensaje_twilio.sid
        )


        return True


    except Exception as error:

        print(
            "ERROR SMS PEDIDO:",
            error
        )


        return False

# ============================================================
# DUEÃ‘O - CREAR PEDIDO REAL
# TELÃ‰FONO VERIFICADO + STRIPE + SQLITE + SMS
# ============================================================

@app.route(
    "/api/dueno/pedidos",
    methods=["POST"]
)
def dueno_crear_pedido():

    # ========================================================
    # SESIÃ“N
    # ========================================================

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    if rol != "dueno":

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Esta funciÃ³n pertenece al perfil DueÃ±o"

        }), 403


    # ========================================================
    # LEER DATOS
    # ========================================================

    datos = (
        request.get_json(
            silent=True
        )
        or
        {}
    )


    productos = datos.get(
        "productos",
        []
    )


    if (
        not isinstance(
            productos,
            list
        )
        or
        not productos
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                "El pedido no contiene productos"

        }), 400


    # ========================================================
    # DATOS DEL CLIENTE
    # ========================================================

    cliente_nombre = str(
        datos.get(
            "cliente_nombre",
            ""
        )
    ).strip()


    telefono_original = str(
        datos.get(
            "telefono",
            ""
        )
    ).strip()


    telefono = normalizar_telefono_mexico(
        telefono_original
    )


    correo = str(
        datos.get(
            "correo",
            ""
        )
    ).strip()


    direccion = str(
        datos.get(
            "direccion",
            ""
        )
    ).strip()


    metodo_pago = str(
        datos.get(
            "metodo_pago",
            ""
        )
    ).strip()


    payment_intent_id = str(
        datos.get(
            "payment_intent_id",
            ""
        )
    ).strip()


    tipo_entrega = str(
        datos.get(
            "tipo_entrega",
            "EnvÃ­o estÃ¡ndar"
        )
    ).strip()


    notas = str(
        datos.get(
            "notas",
            ""
        )
    ).strip()


    mascota_id = datos.get(
        "mascota_id"
    )


    # ========================================================
    # VALIDAR DATOS DEL CLIENTE
    # ========================================================

    if not cliente_nombre:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "El nombre del cliente es obligatorio"

        }), 400


    if not telefono:

        return jsonify({

            "ok":
                False,

            "mensaje":
                (
                    "Ingresa un telÃ©fono mexicano "
                    "vÃ¡lido de 10 dÃ­gitos"
                )

        }), 400


    if not correo:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "El correo electrÃ³nico es obligatorio"

        }), 400


    if not direccion:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "La direcciÃ³n es obligatoria"

        }), 400


    # ========================================================
    # COMPROBAR TELÃ‰FONO VERIFICADO
    # ========================================================

    telefono_verificado = session.get(
        "telefono_verificado"
    )


    if (
        not telefono_verificado
        or
        telefono_verificado
        !=
        telefono
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                (
                    "Debes verificar el telÃ©fono "
                    "con el cÃ³digo SMS antes de "
                    "confirmar el pedido."
                )

        }), 400


    # ========================================================
    # VALIDAR MÃ‰TODO DE PAGO
    # ========================================================

    metodos_permitidos = [

        "Tarjeta",

        "Efectivo contra entrega",

        "Transferencia"

    ]


    if (
        metodo_pago
        not in
        metodos_permitidos
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Selecciona un mÃ©todo de pago vÃ¡lido"

        }), 400


    # ========================================================
    # VALIDAR TIPO DE ENTREGA
    # ========================================================

    entregas_permitidas = [

        "EnvÃ­o estÃ¡ndar",

        "EnvÃ­o express"

    ]


    if (
        tipo_entrega
        not in
        entregas_permitidas
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                "El tipo de entrega no es vÃ¡lido"

        }), 400


    # ========================================================
    # VALIDAR MASCOTA
    # ========================================================

    mascota = None


    if (
        mascota_id
        not in
        [
            None,
            "",
            0
        ]
    ):

        try:

            mascota_id = int(
                mascota_id
            )

        except (
            TypeError,
            ValueError
        ):

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "La mascota seleccionada no es vÃ¡lida"

            }), 400


        mascota = (

            Mascota.query

            .filter_by(

                id=
                    mascota_id,

                usuario_id=
                    usuario_id

            )

            .first()

        )


        if not mascota:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "La mascota no pertenece al usuario"

            }), 403


    # ========================================================
    # VALIDAR PRODUCTOS
    # ========================================================

    productos_validados = []


    subtotal = 0.0


    for item in productos:

        try:

            producto_id = int(
                item.get(
                    "producto_id"
                )
            )


            cantidad = int(
                item.get(
                    "cantidad",
                    1
                )
            )


        except (
            TypeError,
            ValueError
        ):

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "Producto o cantidad no vÃ¡lidos"

            }), 400


        if cantidad <= 0:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "La cantidad debe ser mayor a cero"

            }), 400


        # ----------------------------------------------------
        # PRODUCTO REAL EN SQLITE
        # ----------------------------------------------------

        producto = (

            ProductoProveedor.query

            .filter_by(

                id=
                    producto_id,

                estado=
                    "Activo"

            )

            .first()

        )


        if not producto:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    (
                        "Uno de los productos "
                        "ya no estÃ¡ disponible"
                    )

            }), 404


        # ----------------------------------------------------
        # STOCK
        # ----------------------------------------------------

        stock_actual = int(
            producto.stock
            or
            0
        )


        if (
            stock_actual
            <
            cantidad
        ):

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    (
                        "No hay suficiente stock de "
                        +
                        producto.nombre
                    )

            }), 400


        # ----------------------------------------------------
        # PRECIO REAL
        # ----------------------------------------------------

        precio = float(
            producto.precio
            or
            0
        )


        subtotal_item = (
            precio
            *
            cantidad
        )


        subtotal += subtotal_item


        productos_validados.append({

            "producto":
                producto,

            "cantidad":
                cantidad,

            "precio":
                precio,

            "subtotal":
                subtotal_item

        })


    # ========================================================
    # UN SOLO PROVEEDOR POR PEDIDO
    # ========================================================

    proveedores_pedido = {

        item[
            "producto"
        ]
        .proveedor_id

        for item
        in productos_validados

    }


    if (
        len(
            proveedores_pedido
        )
        >
        1
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                (
                    "Cada pedido debe contener productos "
                    "de un solo proveedor. "
                    "Finaliza esta compra antes de comprar "
                    "a otro proveedor."
                )

        }), 400


    # ========================================================
    # CALCULAR ENVÃO
    # ========================================================

    if subtotal >= 1000:

        envio = 0.0


    elif (
        tipo_entrega
        ==
        "EnvÃ­o express"
    ):

        envio = 149.0


    else:

        envio = 89.0


    # ========================================================
    # TOTAL REAL
    # ========================================================

    subtotal = round(
        subtotal,
        2
    )


    envio = round(
        envio,
        2
    )


    total = round(
        subtotal
        +
        envio,
        2
    )


    # ========================================================
    # VALIDAR TARJETA CON STRIPE
    # ========================================================

    stripe_intent = None


    if (
        metodo_pago
        ==
        "Tarjeta"
    ):

        # ----------------------------------------------------
        # DEBE EXISTIR PAYMENT INTENT
        # ----------------------------------------------------

        if not payment_intent_id:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    (
                        "No se recibiÃ³ la confirmaciÃ³n "
                        "del pago con tarjeta."
                    )

            }), 400


        # ----------------------------------------------------
        # STRIPE DEBE ESTAR CONFIGURADO
        # ----------------------------------------------------

        if not stripe.api_key:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "Stripe no estÃ¡ configurado"

            }), 500


        try:

            stripe_intent = (
                stripe.PaymentIntent.retrieve(
                    payment_intent_id
                )
            )


        except Exception as error:

            print(
                "ERROR CONSULTANDO PAYMENT INTENT:",
                error
            )


            return jsonify({

                "ok":
                    False,

                "mensaje":
                    (
                        "No fue posible validar "
                        "el pago con tarjeta."
                    )

            }), 400


        # ----------------------------------------------------
        # PAGO APROBADO
        # ----------------------------------------------------

        if (
            stripe_intent.status
            !=
            "succeeded"
        ):

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    (
                        "El pago con tarjeta "
                        "todavÃ­a no fue aprobado."
                    )

            }), 400


        # ----------------------------------------------------
        # MONEDA
        # ----------------------------------------------------

        moneda = str(
            stripe_intent.currency
            or
            ""
        ).lower()


        if moneda != "mxn":

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "La moneda del pago no es vÃ¡lida."

            }), 400


        # ----------------------------------------------------
        # IMPORTE ESPERADO
        # ----------------------------------------------------

        total_centavos = int(
            round(
                total
                *
                100
            )
        )


        importe_pagado = int(

            stripe_intent.amount_received

            or

            stripe_intent.amount

            or

            0

        )


        if (
            importe_pagado
            !=
            total_centavos
        ):

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    (
                        "El importe pagado no coincide "
                        "con el total del pedido."
                    )

            }), 400

        # ----------------------------------------------------
        # CONVERTIR METADATA DE STRIPE
        # ----------------------------------------------------

        metadata_stripe = {}

        if stripe_intent.metadata:

            try:

                metadata_stripe = (
                    stripe_intent
                    .metadata
                    .to_dict()
                )

            except Exception as error:

                print(
                    "ERROR CONVIRTIENDO METADATA STRIPE:",
                    error
                )

                metadata_stripe = {}

        # ----------------------------------------------------
        # CONVERTIR METADATA DE STRIPE A DICCIONARIO
        # ----------------------------------------------------

        metadata_stripe = {}

        if stripe_intent.metadata:

            try:

                metadata_stripe = (
                    stripe_intent
                    .metadata
                    .to_dict()
                )

            except Exception as error:

                print(
                    "ERROR CONVIRTIENDO METADATA STRIPE:",
                    error
                )

                metadata_stripe = {}


        # ----------------------------------------------------
        # COMPROBAR USUARIO DEL PAYMENT INTENT
        # ----------------------------------------------------

        metadata_usuario = str(
            metadata_stripe.get(
                "usuario_id",
                ""
            )
        )


        if (
            metadata_usuario
            and
            metadata_usuario
            !=
            str(
                usuario_id
            )
        ):

            return jsonify({

                "ok": False,

                "mensaje":
                    "El pago no pertenece a este usuario."

            }), 403


        # ----------------------------------------------------
        # EVITAR REUTILIZAR EL MISMO PAGO
        # ----------------------------------------------------

        pedido_previo = str(
            metadata_stripe.get(
                "huella_pedido_numero",
                ""
            )
        ).strip()
        # ----------------------------------------------------
        # EVITAR REUTILIZAR UN PAGO
        # ----------------------------------------------------

        pedido_previo = str(
            metadata_stripe.get(
                "huella_pedido_numero",
                ""
            )
        ).strip()
        # ----------------------------------------------------
        # EVITAR REUTILIZAR UN PAGO
        # ----------------------------------------------------

        pedido_previo = str(
            metadata_stripe.get(
                "huella_pedido_numero",
                ""
            )
        ).strip()


        if pedido_previo:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    (
                        "Este pago ya fue utilizado "
                        "en otro pedido."
                    )

            }), 409


    # ========================================================
    # NÃšMERO DE PEDIDO
    # ========================================================

    numero = (

        "HUE-"

        +

        datetime.now()
        .strftime(
            "%y%m%d-%H%M%S"
        )

        +

        "-"

        +

        uuid.uuid4()
        .hex[:4]
        .upper()

    )


    # ========================================================
    # GUARDAR PEDIDO EN SQLITE
    # ========================================================

    try:

        pedido = Pedido(

            numero=
                numero,

            comprador_id=
                usuario_id,

            mascota_id=(

                mascota.id

                if mascota

                else None

            ),

            cliente_nombre=
                cliente_nombre,

            telefono=
                telefono,

            correo=
                correo,

            direccion=
                direccion,

            metodo_pago=
                metodo_pago,

            tipo_entrega=
                tipo_entrega,

            notas=
                notas,

            subtotal=
                subtotal,

            envio=
                envio,

            total=
                total,

            estado=
                "Pendiente"

        )


        db.session.add(
            pedido
        )


        # Necesitamos el ID antes de guardar los detalles.

        db.session.flush()


        detalles = []


        # ====================================================
        # DETALLES + DESCONTAR STOCK
        # ====================================================

        for item in productos_validados:

            producto = item[
                "producto"
            ]


            cantidad = item[
                "cantidad"
            ]


            producto.stock = (

                int(
                    producto.stock
                    or
                    0
                )

                -

                cantidad

            )


            detalle = DetallePedido(

                pedido_id=
                    pedido.id,

                producto_id=
                    producto.id,

                proveedor_id=
                    producto.proveedor_id,

                nombre_producto=
                    producto.nombre,

                precio_unitario=
                    item[
                        "precio"
                    ],

                cantidad=
                    cantidad,

                subtotal=
                    item[
                        "subtotal"
                    ]

            )


            db.session.add(
                detalle
            )


            detalles.append(
                detalle
            )


        # ====================================================
        # GUARDAR TODO
        # ====================================================

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR AL CREAR PEDIDO:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible registrar el pedido"

        }), 500


    # ========================================================
    # MARCAR PAYMENT INTENT COMO UTILIZADO
    # ========================================================

    if (
        metodo_pago
        ==
        "Tarjeta"
        and
        payment_intent_id
    ):

        try:

            stripe.PaymentIntent.modify(

                payment_intent_id,

                metadata={

                    "usuario_id":
                        str(
                            usuario_id
                        ),

                    "huella_pedido_numero":
                        numero

                }

            )


        except Exception as error:

            # El pedido YA estÃ¡ guardado.
            # Por eso este error no cancela la compra.

            print(
                "ADVERTENCIA ACTUALIZANDO METADATA STRIPE:",
                error
            )


    # ========================================================
    # ENVIAR NOTIFICACIÃ“N SMS DEL PEDIDO
    # ========================================================

    sms_enviado = False


    try:

        sms_enviado = enviar_sms_pedido(

            telefono=
                telefono,

            numero=
                numero,

            total=
                total

        )


    except Exception as error:

        print(
            "ERROR ENVIANDO SMS DEL PEDIDO:",
            error
        )


        sms_enviado = False


    # ========================================================
    # LIMPIAR VERIFICACIÃ“N TEMPORAL
    # ========================================================

    session[
        "telefono_verificacion"
    ] = None


    session[
        "telefono_verificado"
    ] = None


    session.modified = True


    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({

        "ok":
            True,

        "mensaje":
            "Pedido registrado correctamente",

        "sms_enviado":
            sms_enviado,

        "pago": {

            "metodo":
                metodo_pago,

            "confirmado":
                (
                    metodo_pago
                    !=
                    "Tarjeta"
                    or
                    (
                        stripe_intent
                        is not None
                        and
                        stripe_intent.status
                        ==
                        "succeeded"
                    )
                )

        },

        "pedido": {

            **pedido.to_dict(),

            "mascota": (

                mascota.nombre

                if mascota

                else ""

            ),

            "productos": [

                detalle.to_dict()

                for detalle
                in detalles

            ]

        }

    }), 201
    # ========================================================
    # GUARDAR PEDIDO, DETALLES Y DESCONTAR STOCK
    # ========================================================

    try:

        pedido = Pedido(
            numero=numero,
            comprador_id=usuario_id,
            mascota_id=(
                mascota.id
                if mascota
                else None
            ),
            cliente_nombre=cliente_nombre,
            telefono=telefono,
            correo=correo,
            direccion=direccion,
            metodo_pago=metodo_pago,
            tipo_entrega=tipo_entrega,
            notas=notas,
            subtotal=subtotal,
            envio=envio,
            total=total,
            estado="Pendiente"
        )


        db.session.add(
            pedido
        )


        # Obtener el ID del pedido
        # antes de crear los detalles.

        db.session.flush()


        # ====================================================
        # LISTA DE DETALLES
        # ====================================================

        detalles = []


        # ====================================================
        # GUARDAR DETALLES Y DESCONTAR STOCK
        # ====================================================

        for item in productos_validados:

            producto = item[
                "producto"
            ]


            cantidad = item[
                "cantidad"
            ]


            producto.stock = (
                int(
                    producto.stock
                    or
                    0
                )
                -
                cantidad
            )


            detalle = DetallePedido(
                pedido_id=pedido.id,
                producto_id=producto.id,
                proveedor_id=producto.proveedor_id,
                nombre_producto=producto.nombre,
                precio_unitario=item["precio"],
                cantidad=cantidad,
                subtotal=item["subtotal"]
            )


            db.session.add(
                detalle
            )


            detalles.append(
                detalle
            )


        # ====================================================
        # GUARDAR TODO EN SQLITE
        # ====================================================

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR AL CREAR PEDIDO:",
            error
        )


        return jsonify({

            "ok": False,

            "mensaje":
                "No fue posible registrar el pedido"

        }), 500


    # ========================================================
    # MARCAR PAYMENT INTENT COMO UTILIZADO
    # ========================================================

    if (
        metodo_pago == "Tarjeta"
        and
        payment_intent_id
    ):

        try:

            stripe.PaymentIntent.modify(
                payment_intent_id,
                metadata={

                    "usuario_id":
                        str(
                            usuario_id
                        ),

                    "huella_pedido_numero":
                        numero

                }
            )


        except Exception as error:

            print(
                "ADVERTENCIA ACTUALIZANDO STRIPE:",
                error
            )


    # ========================================================
    # ENVIAR SMS DE CONFIRMACIÃ“N
    # ========================================================

    sms_enviado = False


    try:

        sms_enviado = enviar_sms_pedido(
            telefono=telefono,
            numero=numero,
            total=total
        )


    except Exception as error:

        print(
            "ERROR ENVIANDO SMS DEL PEDIDO:",
            error
        )


        sms_enviado = False


    # ========================================================
    # LIMPIAR VERIFICACIÃ“N DEL TELÃ‰FONO
    # ========================================================

    session[
        "telefono_verificacion"
    ] = None


    session[
        "telefono_verificado"
    ] = None


    session.modified = True


    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({

        "ok":
            True,

        "mensaje":
            "Pedido registrado correctamente",

        "sms_enviado":
            sms_enviado,

        "pedido": {

            **pedido.to_dict(),

            "mascota": (
                mascota.nombre
                if mascota
                else ""
            ),

            "productos": [

                detalle.to_dict()

                for detalle
                in detalles

            ]

        }

    }), 201
    # ============================================================
# COMERCIO REAL - UTILIDADES DE STOCK
# ============================================================

def _detalles_de_pedido(
    pedido_id
):

    return (
        DetallePedido.query
        .filter_by(
            pedido_id=pedido_id
        )
        .all()
    )


# ============================================================
# DEVOLVER STOCK
# ============================================================

def _devolver_stock_pedido(
    pedido
):

    detalles = _detalles_de_pedido(
        pedido.id
    )


    for detalle in detalles:

        producto = db.session.get(
            ProductoProveedor,
            detalle.producto_id
        )


        if not producto:

            continue


        producto.stock = (
            int(
                producto.stock or 0
            )
            +
            int(
                detalle.cantidad or 0
            )
        )


        producto.actualizado_en = (
            datetime.utcnow()
        )


# ============================================================
# RESERVAR STOCK AL REACTIVAR
# ============================================================

def _reservar_stock_pedido(
    pedido
):

    detalles = _detalles_de_pedido(
        pedido.id
    )


    # Primero validar todo.
    for detalle in detalles:

        producto = db.session.get(
            ProductoProveedor,
            detalle.producto_id
        )


        if not producto:

            return (
                False,
                "Uno de los productos ya no existe"
            )


        if producto.estado != "Activo":

            return (
                False,
                "El producto "
                + detalle.nombre_producto
                + " ya no estÃ¡ disponible"
            )


        stock_actual = int(
            producto.stock or 0
        )


        cantidad = int(
            detalle.cantidad or 0
        )


        if stock_actual < cantidad:

            return (
                False,
                "No hay suficiente stock de "
                + detalle.nombre_producto
            )


    # Si todos tienen stock, descontar.
    for detalle in detalles:

        producto = db.session.get(
            ProductoProveedor,
            detalle.producto_id
        )


        producto.stock = (
            int(
                producto.stock or 0
            )
            -
            int(
                detalle.cantidad or 0
            )
        )


        producto.actualizado_en = (
            datetime.utcnow()
        )


    return True, ""


# ============================================================
# PROVEEDOR - LISTAR PEDIDOS REALES
# ============================================================

@app.route(
    "/api/proveedor/pedidos",
    methods=["GET"]
)
def proveedor_listar_pedidos():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "proveedor":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403


    # --------------------------------------------------------
    # BUSCAR LOS PEDIDOS QUE CONTIENEN PRODUCTOS
    # DE ESTE PROVEEDOR
    # --------------------------------------------------------

    filas = (
        db.session
        .query(
            DetallePedido.pedido_id
        )
        .filter(
            DetallePedido.proveedor_id
            ==
            usuario_id
        )
        .distinct()
        .all()
    )


    pedido_ids = [
        fila[0]
        for fila in filas
    ]


    if not pedido_ids:

        return jsonify({
            "ok": True,
            "total": 0,
            "pedidos": []
        }), 200


    pedidos = (
        Pedido.query
        .filter(
            Pedido.id.in_(
                pedido_ids
            )
        )
        .order_by(
            Pedido.creado_en.desc()
        )
        .all()
    )


    resultado = []


    for pedido in pedidos:

        # Solo los productos que pertenecen
        # al proveedor conectado.

        detalles = (
            DetallePedido.query
            .filter_by(
                pedido_id=pedido.id,
                proveedor_id=usuario_id
            )
            .all()
        )


        if not detalles:

            continue


        mascota = None


        if pedido.mascota_id:

            mascota = db.session.get(
                Mascota,
                pedido.mascota_id
            )


        productos = []

        subtotal_proveedor = 0.0


        for detalle in detalles:

            subtotal_detalle = float(
                detalle.subtotal or 0
            )


            subtotal_proveedor += (
                subtotal_detalle
            )


            productos.append({

                "id":
                    detalle.id,

                "detalle_id":
                    detalle.id,

                "pedido_id":
                    detalle.pedido_id,

                "producto_id":
                    detalle.producto_id,

                "proveedor_id":
                    detalle.proveedor_id,

                "nombre":
                    detalle.nombre_producto,

                "nombre_producto":
                    detalle.nombre_producto,

                "precio":
                    float(
                        detalle.precio_unitario
                        or 0
                    ),

                "precio_unitario":
                    float(
                        detalle.precio_unitario
                        or 0
                    ),

                "cantidad":
                    int(
                        detalle.cantidad
                        or 0
                    ),

                "subtotal":
                    subtotal_detalle

            })


        resultado.append({

            "id":
                pedido.id,

            "pedido_id":
                pedido.id,

            "numero":
                pedido.numero,

            "numeroPedido":
                pedido.numero,

            "comprador_id":
                pedido.comprador_id,

            "mascota_id":
                pedido.mascota_id,

            "mascota":
                mascota.nombre
                if mascota
                else "",

            "cliente":
                pedido.cliente_nombre,

            "cliente_nombre":
                pedido.cliente_nombre,

            "telefono":
                pedido.telefono
                or "",

            "correo":
                pedido.correo
                or "",

            "direccion":
                pedido.direccion,

            "metodoPago":
                pedido.metodo_pago,

            "metodo_pago":
                pedido.metodo_pago,

            "tipoEntrega":
                pedido.tipo_entrega,

            "tipo_entrega":
                pedido.tipo_entrega,

            "notas":
                pedido.notas
                or "",

            "fecha":
                (
                    pedido.creado_en.isoformat()
                    if pedido.creado_en
                    else None
                ),

            "creado_en":
                (
                    pedido.creado_en.isoformat()
                    if pedido.creado_en
                    else None
                ),

            "estado":
                pedido.estado,

            "productos":
                productos,

            "productosDetalle":
                productos,

            # Para el proveedor solamente
            # contamos sus productos.
            "subtotal":
                subtotal_proveedor,

            "envio":
                0.0,

            "total":
                subtotal_proveedor

        })


    return jsonify({

        "ok":
            True,

        "total":
            len(
                resultado
            ),

        "pedidos":
            resultado

    }), 200


# ============================================================
# PROVEEDOR - CAMBIAR ESTADO DEL PEDIDO
# ============================================================

@app.route(
    "/api/proveedor/pedidos/<int:pedido_id>/estado",
    methods=[
        "PATCH",
        "POST"
    ]
)
def proveedor_cambiar_estado_pedido(
    pedido_id
):

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "proveedor":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403


    # --------------------------------------------------------
    # COMPROBAR QUE EL PEDIDO TIENE PRODUCTOS
    # DEL PROVEEDOR ACTUAL
    # --------------------------------------------------------

    pertenece = (
        DetallePedido.query
        .filter_by(
            pedido_id=pedido_id,
            proveedor_id=usuario_id
        )
        .first()
    )


    if not pertenece:

        return jsonify({
            "ok": False,
            "mensaje":
                "Este pedido no pertenece al proveedor"
        }), 404


    pedido = db.session.get(
        Pedido,
        pedido_id
    )


    if not pedido:

        return jsonify({
            "ok": False,
            "mensaje": "Pedido no encontrado"
        }), 404


    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    nuevo_estado = str(
        datos.get(
            "estado",
            ""
        )
    ).strip()


    estados_permitidos = [

        "Pendiente",

        "Preparando",

        "Enviado",

        "Completado",

        "Cancelado"

    ]


    if (
        nuevo_estado
        not in
        estados_permitidos
    ):

        return jsonify({
            "ok": False,
            "mensaje":
                "Estado de pedido no vÃ¡lido"
        }), 400


    estado_actual = (
        pedido.estado
        or
        "Pendiente"
    )


    # --------------------------------------------------------
    # TRANSICIONES PERMITIDAS
    # --------------------------------------------------------

    transiciones = {

        "Pendiente": [
            "Preparando",
            "Cancelado"
        ],

        "Preparando": [
            "Enviado",
            "Cancelado"
        ],

        "Enviado": [
            "Completado"
        ],

        "Completado": [],

        "Cancelado": [
            "Pendiente"
        ]

    }


    if nuevo_estado == estado_actual:

        return jsonify({
            "ok": True,
            "mensaje":
                "El pedido ya tiene ese estado",
            "pedido":
                pedido.to_dict()
        }), 200


    if (
        nuevo_estado
        not in
        transiciones.get(
            estado_actual,
            []
        )
    ):

        return jsonify({

            "ok":
                False,

            "mensaje":
                "No se puede cambiar de "
                + estado_actual
                + " a "
                + nuevo_estado

        }), 400


    try:

        # ----------------------------------------------------
        # CANCELAR = DEVOLVER STOCK
        # ----------------------------------------------------

        if nuevo_estado == "Cancelado":

            _devolver_stock_pedido(
                pedido
            )


        # ----------------------------------------------------
        # REACTIVAR = VOLVER A DESCONTAR STOCK
        # ----------------------------------------------------

        elif (
            estado_actual
            ==
            "Cancelado"
            and
            nuevo_estado
            ==
            "Pendiente"
        ):

            ok, mensaje = (
                _reservar_stock_pedido(
                    pedido
                )
            )


            if not ok:

                db.session.rollback()

                return jsonify({
                    "ok": False,
                    "mensaje": mensaje
                }), 400


        pedido.estado = (
            nuevo_estado
        )


        pedido.actualizado_en = (
            datetime.utcnow()
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR CAMBIANDO ESTADO DEL PEDIDO:",
            error
        )


        return jsonify({
            "ok": False,
            "mensaje":
                "No fue posible actualizar el pedido"
        }), 500


    return jsonify({

        "ok":
            True,

        "mensaje":
            "Pedido actualizado correctamente",

        "pedido":
            pedido.to_dict()

    }), 200


# ============================================================
# DUEÃ‘O - CANCELAR PEDIDO REAL
# ============================================================

@app.route(
    "/api/dueno/pedidos/<int:pedido_id>/cancelar",
    methods=["POST"]
)
def dueno_cancelar_pedido(
    pedido_id
):

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "dueno":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil DueÃ±o"
        }), 403


    pedido = (
        Pedido.query
        .filter_by(
            id=pedido_id,
            comprador_id=usuario_id
        )
        .first()
    )


    if not pedido:

        return jsonify({
            "ok": False,
            "mensaje":
                "Pedido no encontrado"
        }), 404


    # Solamente se permite cancelar
    # antes de que el proveedor lo prepare.

    if pedido.estado != "Pendiente":

        return jsonify({

            "ok":
                False,

            "mensaje":
                "El pedido ya estÃ¡ siendo procesado "
                "y no puede cancelarse"

        }), 400


    try:

        _devolver_stock_pedido(
            pedido
        )


        pedido.estado = (
            "Cancelado"
        )


        pedido.actualizado_en = (
            datetime.utcnow()
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR CANCELANDO PEDIDO:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible cancelar el pedido"

        }), 500


    return jsonify({

        "ok":
            True,

        "mensaje":
            "Pedido cancelado correctamente",

        "pedido":
            pedido.to_dict()

    }), 200
    
# ============================================================
# TIENDA - CATÃLOGO REAL
# ============================================================

@app.route(
    "/api/tienda/productos",
    methods=["GET"]
)
def tienda_listar_productos():

    productos = (
        ProductoProveedor.query
        .filter_by(
            estado="Activo"
        )
        .order_by(
            ProductoProveedor.creado_en.desc()
        )
        .all()
    )

    return jsonify({
        "ok": True,
        "total": len(productos),
        "productos": [
            producto.to_dict()
            for producto in productos
        ]
    }), 200

# ============================================================
# PROVEEDOR - ESTADO DE STRIPE CONNECT
# ============================================================

@app.route(
    "/api/proveedor/connect/estado",
    methods=["GET"]
)
def proveedor_connect_estado():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # --------------------------------------------------------
    # VALIDAR SESIÃ“N
    # --------------------------------------------------------

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "proveedor":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403


    # --------------------------------------------------------
    # CUENTA CONNECT DE PRUEBA
    # --------------------------------------------------------

    connect_account_id = (
        os.environ
        .get(
            "STRIPE_CONNECT_ACCOUNT_ID",
            ""
        )
        .strip()
    )


    if not connect_account_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Stripe Connect todavÃ­a no estÃ¡ configurado"
        }), 400


    if not stripe.api_key:

        return jsonify({
            "ok": False,
            "mensaje":
                "Stripe no estÃ¡ configurado"
        }), 500


    try:

        # ----------------------------------------------------
        # CONSULTAR CUENTA
        # ----------------------------------------------------

        cuenta = (
            stripe.Account.retrieve(
                connect_account_id
            )
        )


        # ----------------------------------------------------
        # CONSULTAR SALDO DISPONIBLE
        # ----------------------------------------------------

        saldo_disponible = 0.0

        saldo_pendiente = 0.0


        try:

            balance = (
                stripe.Balance.retrieve(
                    stripe_account=
                        connect_account_id
                )
            )


            for item in (
                balance.available
                or
                []
            ):

                if (
                    str(
                        item.currency
                    ).lower()
                    ==
                    "mxn"
                ):

                    saldo_disponible += (
                        float(
                            item.amount
                            or
                            0
                        )
                        /
                        100
                    )


            for item in (
                balance.pending
                or
                []
            ):

                if (
                    str(
                        item.currency
                    ).lower()
                    ==
                    "mxn"
                ):

                    saldo_pendiente += (
                        float(
                            item.amount
                            or
                            0
                        )
                        /
                        100
                    )


        except Exception as balance_error:

            print(
                "ERROR CONSULTANDO BALANCE CONNECT:",
                balance_error
            )


        # ----------------------------------------------------
        # REQUISITOS PENDIENTES
        # ----------------------------------------------------

        requisitos = []


        try:

            requirements = (
                cuenta.requirements
            )


            if requirements:

                requirements_dict = (
                    requirements.to_dict()
                )


                requisitos = (
                    requirements_dict.get(
                        "currently_due",
                        []
                    )
                    or
                    []
                )


        except Exception:

            requisitos = []


        # ----------------------------------------------------
        # RESPUESTA
        # ----------------------------------------------------

        return jsonify({

            "ok": True,

            "cuenta_conectada":
                True,

            "charges_enabled":
                bool(
                    cuenta.charges_enabled
                ),

            "payouts_enabled":
                bool(
                    cuenta.payouts_enabled
                ),

            "details_submitted":
                bool(
                    cuenta.details_submitted
                ),

            "saldo_disponible":
                round(
                    saldo_disponible,
                    2
                ),

            "saldo_pendiente_stripe":
                round(
                    saldo_pendiente,
                    2
                ),

            "requisitos_pendientes":
                requisitos

        }), 200


    except Exception as error:

        print(
            "ERROR STRIPE CONNECT:",
            error
        )


        return jsonify({

            "ok": False,

            "mensaje":
                "No fue posible consultar Stripe Connect"

        }), 500


# ============================================================
# PROVEEDOR - HISTORIAL DE RETIROS STRIPE CONNECT
# ============================================================

@app.route(
    "/api/proveedor/connect/retiros",
    methods=["GET"]
)
def proveedor_connect_retiros():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # --------------------------------------------------------
    # VALIDAR SESIÃ“N
    # --------------------------------------------------------

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "proveedor":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403


    # --------------------------------------------------------
    # CUENTA STRIPE CONNECT
    # --------------------------------------------------------

    connect_account_id = (
        os.environ
        .get(
            "STRIPE_CONNECT_ACCOUNT_ID",
            ""
        )
        .strip()
    )


    if not connect_account_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Stripe Connect todavÃ­a no estÃ¡ configurado"
        }), 400


    if not stripe.api_key:

        return jsonify({
            "ok": False,
            "mensaje":
                "Stripe no estÃ¡ configurado"
        }), 500


    try:

        # ----------------------------------------------------
        # CONSULTAR RETIROS DE STRIPE
        # ----------------------------------------------------

        payouts = stripe.Payout.list(
            limit=20,
            stripe_account=
                connect_account_id
        )


        retiros = []


        for payout in payouts.data:

            payout_dict = (
                payout.to_dict()
            )


            monto = (
                float(
                    payout_dict.get(
                        "amount",
                        0
                    )
                )
                /
                100
            )


            moneda = str(
                payout_dict.get(
                    "currency",
                    "mxn"
                )
            ).upper()


            estado_stripe = str(
                payout_dict.get(
                    "status",
                    "pending"
                )
            ).lower()


            estados = {

                "paid":
                    "Pagado",

                "pending":
                    "Pendiente",

                "in_transit":
                    "En trÃ¡nsito",

                "failed":
                    "Fallido",

                "canceled":
                    "Cancelado"

            }


            estado = estados.get(
                estado_stripe,
                estado_stripe
            )


            retiros.append({

                "id":
                    payout_dict.get(
                        "id",
                        ""
                    ),

                "monto":
                    round(
                        monto,
                        2
                    ),

                "moneda":
                    moneda,

                "estado":
                    estado,

                "creado":
                    payout_dict.get(
                        "created"
                    ),

                "llegada":
                    payout_dict.get(
                        "arrival_date"
                    ),

                "metodo":
                    payout_dict.get(
                        "method",
                        ""
                    )

            })


        return jsonify({

            "ok":
                True,

            "total":
                len(
                    retiros
                ),

            "retiros":
                retiros

        }), 200


    except Exception as error:

        print(
            "ERROR CONSULTANDO RETIROS CONNECT:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible consultar los retiros de Stripe"

        }), 500


# ============================================================
# PROVEEDOR - SOLICITAR RETIRO STRIPE CONNECT
# MODO DE PRUEBA
# ============================================================

@app.route(
    "/api/proveedor/connect/retiros",
    methods=["POST"]
)
def proveedor_connect_crear_retiro():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # --------------------------------------------------------
    # VALIDAR SESIÃ“N
    # --------------------------------------------------------

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "proveedor":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403


    # --------------------------------------------------------
    # SOLO ENTORNO DE PRUEBA
    # --------------------------------------------------------

    stripe_secret = (
        os.environ
        .get(
            "STRIPE_SECRET_KEY",
            ""
        )
        .strip()
    )


    if not stripe_secret.startswith(
        "sk_test_"
    ):

        return jsonify({
            "ok": False,
            "mensaje":
                "Los retiros solamente estÃ¡n habilitados en modo de prueba durante el desarrollo"
        }), 403


    # --------------------------------------------------------
    # CUENTA CONNECT
    # --------------------------------------------------------

    connect_account_id = (
        os.environ
        .get(
            "STRIPE_CONNECT_ACCOUNT_ID",
            ""
        )
        .strip()
    )


    if not connect_account_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Stripe Connect no estÃ¡ configurado"
        }), 400


    try:

        cuenta = stripe.Account.retrieve(
            connect_account_id
        )


        # ----------------------------------------------------
        # NO RETIRAR SI STRIPE NO LO AUTORIZA
        # ----------------------------------------------------

        if not cuenta.payouts_enabled:

            return jsonify({
                "ok": False,
                "mensaje":
                    (
                        "Stripe todavÃ­a no ha habilitado "
                        "los retiros para esta cuenta."
                    )
            }), 403


        # ----------------------------------------------------
        # LEER SOLICITUD
        # ----------------------------------------------------

        datos = (
            request.get_json(
                silent=True
            )
            or
            {}
        )


        try:

            monto = float(
                datos.get(
                    "monto",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            return jsonify({
                "ok": False,
                "mensaje":
                    "El monto no es vÃ¡lido"
            }), 400


        if monto <= 0:

            return jsonify({
                "ok": False,
                "mensaje":
                    "El monto debe ser mayor a cero"
            }), 400


        # ----------------------------------------------------
        # CONSULTAR SALDO REAL DE PRUEBA
        # ----------------------------------------------------

        balance = stripe.Balance.retrieve(
            stripe_account=
                connect_account_id
        )


        saldo_disponible = 0


        for item in (
            balance.available
            or
            []
        ):

            if (
                str(
                    item.currency
                ).lower()
                ==
                "mxn"
            ):

                saldo_disponible += int(
                    item.amount
                    or
                    0
                )


        monto_centavos = int(
            round(
                monto * 100
            )
        )


        if (
            monto_centavos
            >
            saldo_disponible
        ):

            return jsonify({
                "ok": False,
                "mensaje":
                    "El monto supera el saldo disponible"
            }), 400


        # ----------------------------------------------------
        # CREAR RETIRO DE PRUEBA
        # ----------------------------------------------------

        payout = stripe.Payout.create(

            amount=
                monto_centavos,

            currency=
                "mxn",

            stripe_account=
                connect_account_id

        )


        return jsonify({

            "ok":
                True,

            "mensaje":
                "Retiro de prueba solicitado correctamente",

            "retiro": {

                "id":
                    payout.id,

                "monto":
                    monto,

                "estado":
                    payout.status

            }

        }), 201


    except Exception as error:

        print(
            "ERROR CREANDO RETIRO CONNECT:",
            error
        )


        return jsonify({
            "ok": False,
            "mensaje":
                "No fue posible procesar el retiro de prueba"
        }), 500

# ============================================================
# PROVEEDOR - ABRIR ONBOARDING DE STRIPE CONNECT
# ============================================================

@app.route(
    "/api/proveedor/connect/onboarding",
    methods=["POST"]
)
def proveedor_connect_onboarding():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # --------------------------------------------------------
    # VALIDAR SESIÃ“N
    # --------------------------------------------------------

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    if rol != "proveedor":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al perfil Proveedor"
        }), 403


    # --------------------------------------------------------
    # CUENTA CONNECT
    # --------------------------------------------------------

    connect_account_id = (
        os.environ
        .get(
            "STRIPE_CONNECT_ACCOUNT_ID",
            ""
        )
        .strip()
    )


    if not connect_account_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Stripe Connect todavÃ­a no estÃ¡ configurado"
        }), 400


    if not stripe.api_key:

        return jsonify({
            "ok": False,
            "mensaje":
                "Stripe no estÃ¡ configurado"
        }), 500


    try:

        # ----------------------------------------------------
        # URL BASE DE HUELLA
        # ----------------------------------------------------

        public_url = (
            os.environ
            .get(
                "HUELLA_PUBLIC_URL",
                ""
            )
            .strip()
            .rstrip("/")
        )


        if not public_url:

            public_url = (
                request
                .host_url
                .rstrip("/")
            )


        # ----------------------------------------------------
        # CREAR ENLACE TEMPORAL
        # ----------------------------------------------------

        account_link = (
            stripe.AccountLink.create(

                account=
                    connect_account_id,

                refresh_url=
                    public_url
                    +
                    "/perfiles/proveedor/ventas.html"
                    +
                    "?connect=refresh",

                return_url=
                    public_url
                    +
                    "/perfiles/proveedor/ventas.html"
                    +
                    "?connect=done",

                type=
                    "account_onboarding"

            )
        )


        return jsonify({

            "ok":
                True,

            "url":
                account_link.url

        }), 200


    except Exception as error:

        print(
            "ERROR CREANDO ONBOARDING CONNECT:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible abrir Stripe Connect"

        }), 500
        
        # ============================================================
# DUEÃ‘O - RESUMEN REAL DEL PANEL PRINCIPAL
# ============================================================


def _huella_extraer_lista_modulo(
    datos,
    modulo
):

    """
    Convierte los datos JSON guardados por cada mÃ³dulo
    en una lista que el dashboard pueda contabilizar.

    Es compatible con varias versiones anteriores
    de los mÃ³dulos de Huella.
    """

    if datos is None:

        return []


    # ========================================================
    # SI YA ES LISTA
    # ========================================================

    if isinstance(
        datos,
        list
    ):

        return datos


    # ========================================================
    # SI ES UN OBJETO
    # ========================================================

    if not isinstance(
        datos,
        dict
    ):

        return []


    claves_por_modulo = {

        "expediente": [
            "expediente",
            "registros",
            "historial",
            "items"
        ],

        "consultas": [
            "consultas",
            "consultations",
            "registros",
            "historial",
            "items"
        ],

        "citas": [
            "citas",
            "appointments",
            "agenda",
            "registros",
            "items",
            "historial"
        ],

        "vacunas": [
            "vacunas",
            "vaccines",
            "registros",
            "items",
            "historial"
        ],

        "tratamientos": [
            "tratamientos",
            "treatments",
            "registros",
            "items",
            "historial"
        ],

        "recetas": [
            "recetas",
            "prescriptions",
            "registros",
            "items",
            "historial"
        ]

    }


    posibles_claves = (
        claves_por_modulo.get(
            modulo,
            []
        )
    )


    # ========================================================
    # BUSCAR CLAVES CONOCIDAS
    # ========================================================

    for clave in posibles_claves:

        valor = datos.get(
            clave
        )


        if isinstance(
            valor,
            list
        ):

            return valor


    # ========================================================
    # BUSCAR CUALQUIER LISTA INTERNA
    # ========================================================

    for valor in datos.values():

        if isinstance(
            valor,
            list
        ):

            return valor


    # ========================================================
    # SI TIENE DATOS PERO NO CONTIENE LISTAS,
    # LO CONSIDERAMOS UN REGISTRO
    # ========================================================

    if datos:

        return [
            datos
        ]


    return []


# ============================================================
# FECHA DE UNA CITA
# ============================================================

def _huella_fecha_cita(
    cita
):

    if not isinstance(
        cita,
        dict
    ):

        return None


    fecha = (

        cita.get(
            "fecha"
        )

        or

        cita.get(
            "date"
        )

        or

        cita.get(
            "fecha_cita"
        )

        or

        cita.get(
            "appointmentDate"
        )

        or

        ""

    )


    hora = (

        cita.get(
            "hora"
        )

        or

        cita.get(
            "time"
        )

        or

        cita.get(
            "hora_cita"
        )

        or

        cita.get(
            "appointmentTime"
        )

        or

        "00:00"

    )


    fecha = str(
        fecha
    ).strip()


    hora = str(
        hora
    ).strip()


    if not fecha:

        return None


    try:

        # ====================================================
        # FECHA ISO QUE YA INCLUYE HORA
        # ====================================================

        if (
            "T" in fecha
            or
            " " in fecha
        ):

            fecha_limpia = (
                fecha
                .replace(
                    "Z",
                    "+00:00"
                )
            )


            resultado = (
                datetime
                .fromisoformat(
                    fecha_limpia
                )
            )


            # Si trae zona horaria,
            # quitamos tz para comparar localmente.
            if resultado.tzinfo:

                resultado = (
                    resultado
                    .replace(
                        tzinfo=None
                    )
                )


            return resultado


        # ====================================================
        # FECHA YYYY-MM-DD + HORA
        # ====================================================

        return datetime.fromisoformat(

            fecha
            +
            "T"
            +
            (
                hora
                if hora
                else
                "00:00"
            )

        )


    except Exception:

        return None


# ============================================================
# CONSULTAR RESUMEN DEL DUEÃ‘O
# ============================================================

@app.route(
    "/api/dueno/resumen",
    methods=["GET"]
)
def dueno_resumen():

    # ========================================================
    # SESIÃ“N
    # ========================================================

    usuario_id = session.get(
        "usuario_id"
    )


    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    if rol != "dueno":

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Esta funciÃ³n pertenece al perfil DueÃ±o / Tutor"

        }), 403


    # ========================================================
    # USUARIO
    # ========================================================

    usuario = db.session.get(
        Usuario,
        usuario_id
    )


    if not usuario:

        return jsonify({

            "ok":
                False,

            "mensaje":
                "Usuario no encontrado"

        }), 404


    # ========================================================
    # MASCOTAS REALES
    # ========================================================

    mascotas = (

        Mascota.query

        .filter_by(
            usuario_id=usuario_id
        )

        .order_by(
            Mascota.fecha_registro.desc()
        )

        .all()

    )


    mascotas_ids = [

        mascota.id

        for mascota
        in mascotas

    ]


    nombres_mascotas = {

        mascota.id:
            mascota.nombre

        for mascota
        in mascotas

    }


    # ========================================================
    # VARIABLES DEL RESUMEN
    # ========================================================

    expedientes_total = 0

    consultas_total = 0

    citas_total = 0

    vacunas_total = 0

    tratamientos_total = 0

    tratamientos_activos = 0

    recetas_total = 0


    citas_encontradas = []


    # ========================================================
    # LEER MÃ“DULOS GUARDADOS EN SQLITE
    # ========================================================

    if mascotas_ids:

        registros_modulos = (

            DatosModuloMascota.query

            .filter(

                DatosModuloMascota.usuario_id
                ==
                usuario_id,

                DatosModuloMascota.mascota_id.in_(
                    mascotas_ids
                )

            )

            .all()

        )

    else:

        registros_modulos = []


    # ========================================================
    # RECORRER MÃ“DULOS
    # ========================================================

    for registro in registros_modulos:

        modulo = str(
            registro.modulo
            or
            ""
        ).strip().lower()


        try:

            datos = json.loads(
                registro.datos_json
                or
                "null"
            )

        except Exception:

            datos = None


        items = (
            _huella_extraer_lista_modulo(
                datos,
                modulo
            )
        )


        # ====================================================
        # EXPEDIENTE
        # ====================================================

        if modulo == "expediente":

            if datos:

                expedientes_total += 1


        # ====================================================
        # CONSULTAS
        # ====================================================

        elif modulo == "consultas":

            consultas_total += (
                len(
                    items
                )
            )


        # ====================================================
        # CITAS
        # ====================================================

        elif modulo == "citas":

            citas_total += (
                len(
                    items
                )
            )


            for cita in items:

                if not isinstance(
                    cita,
                    dict
                ):

                    continue


                estado = str(

                    cita.get(
                        "estado",
                        ""
                    )

                ).strip().lower()


                # No mostrar citas terminadas
                # como prÃ³ximas.

                if estado in [

                    "completada",
                    "completado",

                    "cancelada",
                    "cancelado",

                    "finalizada",
                    "finalizado"

                ]:

                    continue


                fecha_cita = (
                    _huella_fecha_cita(
                        cita
                    )
                )


                if not fecha_cita:

                    continue


                if (
                    fecha_cita
                    <
                    datetime.now()
                ):

                    continue


                cita_resumen = {

                    **cita,

                    "_fecha_datetime":
                        fecha_cita,

                    "_mascota_id":
                        registro.mascota_id,

                    "_mascota_nombre":
                        nombres_mascotas.get(
                            registro.mascota_id,
                            "Mascota"
                        )

                }


                citas_encontradas.append(
                    cita_resumen
                )


        # ====================================================
        # VACUNAS
        # ====================================================

        elif modulo == "vacunas":

            vacunas_total += (
                len(
                    items
                )
            )


        # ====================================================
        # TRATAMIENTOS
        # ====================================================

        elif modulo == "tratamientos":

            tratamientos_total += (
                len(
                    items
                )
            )


            for tratamiento in items:

                if not isinstance(
                    tratamiento,
                    dict
                ):

                    continue


                estado = str(

                    tratamiento.get(
                        "estado",
                        ""
                    )

                ).strip().lower()


                # Si el registro no tiene estado,
                # tambiÃ©n se considera activo.

                if estado not in [

                    "finalizado",
                    "finalizada",

                    "completado",
                    "completada",

                    "cancelado",
                    "cancelada"

                ]:

                    tratamientos_activos += 1


        # ====================================================
        # RECETAS
        # ====================================================

        elif modulo == "recetas":

            recetas_total += (
                len(
                    items
                )
            )


    # ========================================================
    # PRÃ“XIMA CITA
    # ========================================================

    citas_encontradas.sort(

        key=lambda item:
            item[
                "_fecha_datetime"
            ]

    )


    proxima_cita = None


    if citas_encontradas:

        siguiente = (
            citas_encontradas[
                0
            ]
        )


        fecha_datetime = (
            siguiente.pop(
                "_fecha_datetime",
                None
            )
        )


        mascota_id = (
            siguiente.pop(
                "_mascota_id",
                None
            )
        )


        mascota_nombre = (
            siguiente.pop(
                "_mascota_nombre",
                "Mascota"
            )
        )


        proxima_cita = {

            **siguiente,

            "mascota_id":
                mascota_id,

            "mascota":
                mascota_nombre,

            "fecha_iso":
                (
                    fecha_datetime.isoformat()

                    if fecha_datetime

                    else None
                )

        }


    # ========================================================
    # PEDIDOS REALES
    # ========================================================

    pedidos = (

        Pedido.query

        .filter_by(
            comprador_id=usuario_id
        )

        .order_by(
            Pedido.creado_en.desc()
        )

        .all()

    )


    pedidos_activos = [

        pedido

        for pedido
        in pedidos

        if str(
            pedido.estado
            or
            ""
        ).strip().lower()

        not in [

            "completado",
            "completada",

            "entregado",
            "entregada",

            "cancelado",
            "cancelada"

        ]

    ]


    ultimo_pedido = None


    if pedidos:

        pedido = pedidos[0]


        ultimo_pedido = (
            pedido.to_dict()
        )


        if pedido.mascota_id:

            mascota_pedido = (
                db.session.get(
                    Mascota,
                    pedido.mascota_id
                )
            )


            ultimo_pedido[
                "mascota"
            ] = (

                mascota_pedido.nombre

                if mascota_pedido

                else ""

            )


    # ========================================================
    # MEMBRESÃA REAL
    # ========================================================

    membresia_db = (

        Membresia.query

        .filter_by(
            usuario_id=usuario_id
        )

        .first()

    )


    membresia = None


    if membresia_db:

        # ====================================================
        # COMPROBAR VENCIMIENTO
        # ====================================================

        if (
            membresia_db.fecha_expiracion
            and
            datetime.now()
            >
            membresia_db.fecha_expiracion
        ):

            membresia_db.estado = (
                "Vencida"
            )


            db.session.commit()


        membresia = (
            membresia_db.to_dict()
        )


        membresia[
            "db_id"
        ] = (
            membresia_db.id
        )


        membresia[
            "id"
        ] = (
            membresia_db.plan_id
        )


    # ========================================================
    # SOLICITUDES PENDIENTES DE VETERINARIOS
    # ========================================================

    solicitudes_veterinario = (

        VinculoVeterinarioMascota.query

        .filter_by(

            propietario_id=
                usuario_id,

            estado=
                "Pendiente"

        )

        .count()

    )


    # ========================================================
    # RESPUESTA FINAL
    # ========================================================

    return jsonify({

        "ok":
            True,


        "usuario": {

            "id":
                usuario.id,

            "nombre":
                usuario.nombre,

            "correo":
                usuario.correo

        },


        "mascotas_total":
            len(
                mascotas
            ),


        "mascotas": [

            mascota.to_dict()

            for mascota
            in mascotas

        ],


        "expedientes_total":
            expedientes_total,


        "consultas_total":
            consultas_total,


        "citas_total":
            citas_total,


        "proxima_cita":
            proxima_cita,


        "vacunas_total":
            vacunas_total,


        "tratamientos_total":
            tratamientos_total,


        "tratamientos_activos":
            tratamientos_activos,


        "recetas_total":
            recetas_total,


        "pedidos_total":
            len(
                pedidos
            ),


        "pedidos_activos":
            len(
                pedidos_activos
            ),


        "ultimo_pedido":
            ultimo_pedido,


        "membresia":
            membresia,


        "solicitudes_veterinario":
            solicitudes_veterinario

    }), 200
        
        # ============================================================
# ADMINISTRADOR - RESUMEN GENERAL REAL
# ============================================================

@app.route(
    "/api/administrador/resumen",
    methods=["GET"]
)
def administrador_resumen():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403


    try:

        # ====================================================
        # USUARIOS
        # ====================================================

        usuarios_total = (
            Usuario.query.count()
        )


        duenos_total = (
            Usuario.query
            .filter_by(
                rol="dueno"
            )
            .count()
        )


        veterinarios_total = (
            Usuario.query
            .filter_by(
                rol="veterinario"
            )
            .count()
        )


        proveedores_total = (
            Usuario.query
            .filter_by(
                rol="proveedor"
            )
            .count()
        )


        administradores_total = (
            Usuario.query
            .filter_by(
                rol="administrador"
            )
            .count()
        )


        usuarios_activos = (
            Usuario.query
            .filter_by(
                activo=True
            )
            .count()
        )


        # ====================================================
        # MASCOTAS
        # ====================================================

        mascotas_total = (
            Mascota.query.count()
        )


        # ====================================================
        # PRODUCTOS
        # ====================================================

        productos = (
            ProductoProveedor.query
            .order_by(
                ProductoProveedor.id.desc()
            )
            .all()
        )


        productos_total = len(
            productos
        )


        productos_activos = 0

        stock_bajo = 0

        sin_existencias = 0


        for producto in productos:

            estado = str(
                producto.estado
                or
                "Activo"
            ).strip().lower()


            stock = int(
                producto.stock
                or
                0
            )


            if estado != "inactivo":

                productos_activos += 1


                if stock <= 5:

                    stock_bajo += 1


                if stock <= 0:

                    sin_existencias += 1


        # ====================================================
        # PEDIDOS
        # ====================================================

        pedidos = (
            Pedido.query
            .order_by(
                Pedido.creado_en.desc()
            )
            .all()
        )


        pedidos_total = len(
            pedidos
        )


        pedidos_pendientes = 0

        pedidos_en_proceso = 0

        pedidos_completados = 0

        pedidos_cancelados = 0

        ventas_total = 0.0


        for pedido in pedidos:

            estado = str(
                pedido.estado
                or
                "Pendiente"
            ).strip().lower()


            if estado == "pendiente":

                pedidos_pendientes += 1


            elif estado in [
                "preparando",
                "enviado"
            ]:

                pedidos_en_proceso += 1


            elif estado in [
                "completado",
                "entregado"
            ]:

                pedidos_completados += 1

                ventas_total += float(
                    pedido.total
                    or
                    0
                )


            elif estado == "cancelado":

                pedidos_cancelados += 1


        # ====================================================
        # PEDIDOS RECIENTES
        # ====================================================

        pedidos_recientes = []


        for pedido in pedidos[:5]:

            mascota_nombre = ""


            if pedido.mascota_id:

                mascota = db.session.get(
                    Mascota,
                    pedido.mascota_id
                )


                if mascota:

                    mascota_nombre = (
                        mascota.nombre
                        or
                        ""
                    )


            pedidos_recientes.append({

                "id":
                    pedido.id,

                "numero":
                    pedido.numero,

                "numeroPedido":
                    pedido.numero,

                "cliente":
                    pedido.cliente_nombre
                    or
                    "Cliente",

                "mascota":
                    mascota_nombre,

                "estado":
                    pedido.estado
                    or
                    "Pendiente",

                "total":
                    float(
                        pedido.total
                        or
                        0
                    ),

                "fecha":
                    (
                        pedido.creado_en.isoformat()
                        if pedido.creado_en
                        else None
                    )

            })


        # ====================================================
        # RESPUESTA
        # ====================================================

        return jsonify({

            "ok":
                True,


            "usuarios_total":
                usuarios_total,

            "usuarios_activos":
                usuarios_activos,

            "duenos_total":
                duenos_total,

            "veterinarios_total":
                veterinarios_total,

            "proveedores_total":
                proveedores_total,

            "administradores_total":
                administradores_total,


            "mascotas_total":
                mascotas_total,


            "productos_total":
                productos_total,

            "productos_activos":
                productos_activos,

            "stock_bajo":
                stock_bajo,

            "sin_existencias":
                sin_existencias,


            "pedidos_total":
                pedidos_total,

            "pedidos_pendientes":
                pedidos_pendientes,

            "pedidos_en_proceso":
                pedidos_en_proceso,

            "pedidos_completados":
                pedidos_completados,

            "pedidos_cancelados":
                pedidos_cancelados,


            "ventas_total":
                round(
                    ventas_total,
                    2
                ),


            "pedidos_recientes":
                pedidos_recientes

        }), 200


    except Exception as error:

        print(
            "ERROR RESUMEN ADMINISTRADOR:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible cargar el resumen administrativo"

        }), 500

# ============================================================
# ADMINISTRADOR - LISTAR USUARIOS REALES
# ============================================================

@app.route(
    "/api/administrador/usuarios",
    methods=["GET"]
)
def administrador_listar_usuarios():

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ADMINISTRADOR
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403


    try:

        usuarios = (
            Usuario.query
            .order_by(
                Usuario.fecha_registro.desc()
            )
            .all()
        )


        resultado = []


        for usuario in usuarios:

            datos = (
                usuario.to_dict()
            )


            # ------------------------------------------------
            # NOMBRE AMIGABLE DEL ROL
            # ------------------------------------------------

            rol_real = str(
                usuario.rol
                or
                ""
            ).strip().lower()


            if rol_real == "dueno":

                datos["rol_nombre"] = (
                    "Tutor"
                )

            elif rol_real == "veterinario":

                datos["rol_nombre"] = (
                    "Veterinario"
                )

            elif rol_real == "proveedor":

                datos["rol_nombre"] = (
                    "Proveedor"
                )

            elif rol_real == "administrador":

                datos["rol_nombre"] = (
                    "Administrador"
                )

            else:

                datos["rol_nombre"] = (
                    usuario.rol
                    or
                    "Usuario"
                )


            datos["estado"] = (
                "Activo"
                if usuario.activo
                else "Inactivo"
            )


            resultado.append(
                datos
            )


        return jsonify({

            "ok":
                True,

            "total":
                len(resultado),

            "usuarios":
                resultado

        }), 200


    except Exception as error:

        print(
            "ERROR LISTANDO USUARIOS ADMIN:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible cargar los usuarios"

        }), 500


# ============================================================
# ADMINISTRADOR - ACTIVAR / DESACTIVAR USUARIO
# ============================================================

@app.route(
    "/api/administrador/usuarios/<int:usuario_id>/estado",
    methods=["PATCH", "PUT", "POST"]
)
def administrador_cambiar_estado_usuario(
    usuario_id
):

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403


    # ========================================================
    # EVITAR DESACTIVAR LA PROPIA CUENTA
    # ========================================================

    if int(usuario_id) == int(administrador_id):

        return jsonify({
            "ok": False,
            "mensaje":
                "No puedes desactivar tu propia cuenta de administrador"
        }), 400


    usuario = db.session.get(
        Usuario,
        usuario_id
    )


    if not usuario:

        return jsonify({
            "ok": False,
            "mensaje":
                "Usuario no encontrado"
        }), 404


    datos = (
        request.get_json(
            silent=True
        )
        or
        {}
    )


    activo = datos.get(
        "activo"
    )


    # ========================================================
    # SI NO ENVÃA BOOLEANO, CAMBIAR AL ESTADO CONTRARIO
    # ========================================================

    if activo is None:

        nuevo_estado = (
            not bool(
                usuario.activo
            )
        )

    else:

        nuevo_estado = bool(
            activo
        )


    usuario.activo = (
        nuevo_estado
    )


    try:

        db.session.commit()


        return jsonify({

            "ok":
                True,

            "mensaje":
                (
                    "Usuario activado correctamente"
                    if usuario.activo
                    else
                    "Usuario desactivado correctamente"
                ),

            "usuario":
                usuario.to_dict(),

            "estado":
                (
                    "Activo"
                    if usuario.activo
                    else
                    "Inactivo"
                )

        }), 200


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR CAMBIANDO ESTADO USUARIO:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible actualizar el estado del usuario"

        }), 500


# ============================================================
# ADMINISTRADOR - LISTAR TODAS LAS MASCOTAS
# ============================================================

@app.route(
    "/api/administrador/mascotas",
    methods=["GET"]
)
def administrador_listar_mascotas():

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403


    try:

        mascotas = (
            Mascota.query
            .order_by(
                Mascota.fecha_registro.desc()
            )
            .all()
        )


        resultado = []


        for mascota in mascotas:

            propietario = db.session.get(
                Usuario,
                mascota.usuario_id
            )


            datos = mascota.to_dict()


            datos["propietario"] = {

                "id":
                    (
                        propietario.id
                        if propietario
                        else None
                    ),

                "nombre":
                    (
                        propietario.nombre
                        if propietario
                        else "Sin propietario"
                    ),

                "correo":
                    (
                        propietario.correo
                        if propietario
                        else ""
                    ),

                "telefono":
                    (
                        propietario.telefono
                        if propietario
                        else ""
                    )

            }


            datos["propietario_nombre"] = (
                propietario.nombre
                if propietario
                else "Sin propietario"
            )


            datos["propietario_correo"] = (
                propietario.correo
                if propietario
                else ""
            )


            resultado.append(
                datos
            )


        return jsonify({

            "ok":
                True,

            "total":
                len(resultado),

            "mascotas":
                resultado

        }), 200


    except Exception as error:

        print(
            "ERROR LISTANDO MASCOTAS ADMIN:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible cargar las mascotas"

        }), 500


# ============================================================
# ADMINISTRADOR - LISTAR PROVEEDORES REALES
# ============================================================

@app.route(
    "/api/administrador/proveedores",
    methods=["GET"]
)
def administrador_listar_proveedores():

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403


    try:

        # ====================================================
        # BUSCAR CUENTAS DE PROVEEDOR
        # ====================================================

        usuarios_proveedores = (
            Usuario.query
            .filter_by(
                rol="proveedor"
            )
            .order_by(
                Usuario.fecha_registro.desc()
            )
            .all()
        )


        resultado = []


        total_productos_activos = 0

        total_pedidos = 0

        total_ventas = 0.0


        # ====================================================
        # RECORRER PROVEEDORES
        # ====================================================

        for usuario in usuarios_proveedores:

            # ------------------------------------------------
            # PERFIL COMERCIAL
            # ------------------------------------------------

            perfil = (
                PerfilProveedor.query
                .filter_by(
                    proveedor_id=usuario.id
                )
                .first()
            )


            # ------------------------------------------------
            # PRODUCTOS
            # ------------------------------------------------

            productos = (
                ProductoProveedor.query
                .filter_by(
                    proveedor_id=usuario.id
                )
                .order_by(
                    ProductoProveedor.id.desc()
                )
                .all()
            )


            productos_activos = [
                producto
                for producto in productos
                if str(
                    producto.estado
                    or
                    "Activo"
                ).strip().lower()
                !=
                "inactivo"
            ]


            stock_bajo = [
                producto
                for producto in productos_activos
                if int(
                    producto.stock
                    or
                    0
                )
                <=
                5
            ]


            # ------------------------------------------------
            # PEDIDOS DEL PROVEEDOR
            # ------------------------------------------------

            filas_pedidos = (
                db.session
                .query(
                    DetallePedido.pedido_id
                )
                .filter(
                    DetallePedido.proveedor_id
                    ==
                    usuario.id
                )
                .distinct()
                .all()
            )


            pedido_ids = [
                fila[0]
                for fila in filas_pedidos
            ]


            if pedido_ids:

                pedidos = (
                    Pedido.query
                    .filter(
                        Pedido.id.in_(
                            pedido_ids
                        )
                    )
                    .order_by(
                        Pedido.creado_en.desc()
                    )
                    .all()
                )

            else:

                pedidos = []


            pedidos_completados = 0

            ventas_proveedor = 0.0


            # ------------------------------------------------
            # CALCULAR VENTAS DEL PROVEEDOR
            # ------------------------------------------------

            for pedido in pedidos:

                estado_pedido = str(
                    pedido.estado
                    or
                    ""
                ).strip().lower()


                detalles_proveedor = (
                    DetallePedido.query
                    .filter_by(
                        pedido_id=pedido.id,
                        proveedor_id=usuario.id
                    )
                    .all()
                )


                if estado_pedido in [
                    "completado",
                    "entregado"
                ]:

                    pedidos_completados += 1


                    for detalle in detalles_proveedor:

                        ventas_proveedor += float(
                            detalle.subtotal
                            or
                            0
                        )


            # ------------------------------------------------
            # PERFIL
            # ------------------------------------------------

            if perfil:

                perfil_dict = (
                    perfil.to_dict()
                )

            else:

                perfil_dict = {}


            nombre_comercial = (
                perfil_dict.get(
                    "nombre_comercial"
                )
                or
                perfil_dict.get(
                    "nombre"
                )
                or
                usuario.nombre
                or
                "Proveedor Huella"
            )


            categoria = (
                perfil_dict.get(
                    "categoria"
                )
                or
                "Tienda de mascotas"
            )


            correo = (
                perfil_dict.get(
                    "correo"
                )
                or
                usuario.correo
                or
                ""
            )


            telefono = (
                perfil_dict.get(
                    "telefono"
                )
                or
                usuario.telefono
                or
                ""
            )


            direccion = (
                perfil_dict.get(
                    "direccion"
                )
                or
                perfil_dict.get(
                    "ubicacion"
                )
                or
                ""
            )


            descripcion = (
                perfil_dict.get(
                    "descripcion"
                )
                or
                "Proveedor registrado dentro de Huella."
            )


            logo = (
                perfil_dict.get(
                    "logo"
                )
                or
                ""
            )


            horario_semana = (
                perfil_dict.get(
                    "horario_semana"
                )
                or
                perfil_dict.get(
                    "horarioSemana"
                )
                or
                ""
            )


            horario_sabado = (
                perfil_dict.get(
                    "horario_sabado"
                )
                or
                perfil_dict.get(
                    "horarioSabado"
                )
                or
                ""
            )


            horario_domingo = (
                perfil_dict.get(
                    "horario_domingo"
                )
                or
                perfil_dict.get(
                    "horarioDomingo"
                )
                or
                ""
            )


            # ------------------------------------------------
            # SUMAS GENERALES
            # ------------------------------------------------

            total_productos_activos += (
                len(
                    productos_activos
                )
            )


            total_pedidos += (
                len(
                    pedidos
                )
            )


            total_ventas += (
                ventas_proveedor
            )


            # ------------------------------------------------
            # AGREGAR PROVEEDOR
            # ------------------------------------------------

            resultado.append({

                "id":
                    usuario.id,

                "usuario_id":
                    usuario.id,

                "nombre":
                    nombre_comercial,

                "nombre_comercial":
                    nombre_comercial,

                "responsable":
                    usuario.nombre
                    or
                    "Sin registrar",

                "correo":
                    correo,

                "telefono":
                    telefono,

                "categoria":
                    categoria,

                "direccion":
                    direccion,

                "descripcion":
                    descripcion,

                "logo":
                    logo,

                "horario_semana":
                    horario_semana,

                "horario_sabado":
                    horario_sabado,

                "horario_domingo":
                    horario_domingo,

                "estado":
                    (
                        "Activo"
                        if usuario.activo
                        else
                        "Inactivo"
                    ),

                "activo":
                    bool(
                        usuario.activo
                    ),

                "fecha_registro":
                    (
                        usuario.fecha_registro.isoformat()
                        if usuario.fecha_registro
                        else None
                    ),

                "productos":
                    len(
                        productos
                    ),

                "productos_activos":
                    len(
                        productos_activos
                    ),

                "stock_bajo":
                    len(
                        stock_bajo
                    ),

                "pedidos":
                    len(
                        pedidos
                    ),

                "pedidos_completados":
                    pedidos_completados,

                "ventas":
                    round(
                        ventas_proveedor,
                        2
                    )

            })


        # ====================================================
        # RESPUESTA
        # ====================================================

        return jsonify({

            "ok":
                True,

            "total":
                len(
                    resultado
                ),

            "proveedores":
                resultado,

            "resumen": {

                "proveedores":
                    len(
                        resultado
                    ),

                "productos_activos":
                    total_productos_activos,

                "pedidos":
                    total_pedidos,

                "ventas":
                    round(
                        total_ventas,
                        2
                    )

            }

        }), 200


    except Exception as error:

        print(
            "ERROR LISTANDO PROVEEDORES ADMIN:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                "No fue posible cargar los proveedores"

        }), 500

# ============================================================
# ADMINISTRADOR - LISTAR PRODUCTOS REALES
# ============================================================

@app.route(
    "/api/administrador/productos",
    methods=["GET"]
)
def administrador_listar_productos():

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )

    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403

    try:

        productos = (
            ProductoProveedor.query
            .order_by(
                ProductoProveedor.id.desc()
            )
            .all()
        )

        resultado = []

        activos = 0
        stock_bajo = 0
        agotados = 0

        for producto in productos:

            # =================================================
            # PROVEEDOR
            # =================================================

            proveedor = db.session.get(
                Usuario,
                producto.proveedor_id
            )

            perfil = (
                PerfilProveedor.query
                .filter_by(
                    proveedor_id=producto.proveedor_id
                )
                .first()
            )

            perfil_datos = {}

            if perfil:

                try:

                    perfil_datos = (
                        perfil.to_dict()
                    )

                except Exception:

                    perfil_datos = {}

            proveedor_nombre = (
                perfil_datos.get(
                    "nombre_comercial"
                )
                or
                perfil_datos.get(
                    "nombre"
                )
                or
                (
                    proveedor.nombre
                    if proveedor
                    else None
                )
                or
                "Proveedor Huella"
            )

            # =================================================
            # ESTADO / STOCK
            # =================================================

            estado = str(
                producto.estado
                or
                "Activo"
            ).strip()

            stock = int(
                producto.stock
                or
                0
            )

            if estado.lower() == "activo":

                activos += 1

            if stock <= 0:

                agotados += 1

            elif stock <= 5:

                stock_bajo += 1

            # =================================================
            # DATOS DEL PRODUCTO
            # =================================================

            datos = (
                producto.to_dict()
            )

            datos["proveedor_id"] = (
                producto.proveedor_id
            )

            datos["proveedor"] = (
                proveedor_nombre
            )

            datos["proveedor_nombre"] = (
                proveedor_nombre
            )

            resultado.append(
                datos
            )

        # =====================================================
        # RESPUESTA
        # =====================================================

        return jsonify({

            "ok": True,

            "total":
                len(resultado),

            "productos":
                resultado,

            "resumen": {

                "total":
                    len(resultado),

                "activos":
                    activos,

                "stock_bajo":
                    stock_bajo,

                "agotados":
                    agotados

            }

        }), 200

    except Exception as error:

        print(
            "ERROR LISTANDO PRODUCTOS ADMIN:",
            error
        )

        return jsonify({
            "ok": False,
            "mensaje":
                "No fue posible cargar los productos"
        }), 500


# ============================================================
# ADMINISTRADOR - CAMBIAR ESTADO DEL PRODUCTO
# ============================================================

@app.route(
    "/api/administrador/productos/<int:producto_id>/estado",
    methods=["PATCH", "PUT", "POST"]
)
def administrador_cambiar_estado_producto(
    producto_id
):

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )

    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401

    # ========================================================
    # VALIDAR ADMINISTRADOR
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403

    # ========================================================
    # BUSCAR PRODUCTO
    # ========================================================

    producto = db.session.get(
        ProductoProveedor,
        producto_id
    )

    if not producto:

        return jsonify({
            "ok": False,
            "mensaje": "Producto no encontrado"
        }), 404

    datos = (
        request.get_json(
            silent=True
        )
        or
        {}
    )

    nuevo_estado = str(
        datos.get(
            "estado",
            ""
        )
    ).strip()

    # ========================================================
    # SI NO VIENE ESTADO, CAMBIAR AL CONTRARIO
    # ========================================================

    if nuevo_estado not in [
        "Activo",
        "Inactivo"
    ]:

        estado_actual = str(
            producto.estado
            or
            "Activo"
        ).strip().lower()

        if estado_actual == "activo":

            nuevo_estado = "Inactivo"

        else:

            nuevo_estado = "Activo"

    producto.estado = (
        nuevo_estado
    )

    try:

        db.session.commit()

        return jsonify({

            "ok": True,

            "mensaje":
                (
                    "Producto activado correctamente"
                    if producto.estado == "Activo"
                    else
                    "Producto desactivado correctamente"
                ),

            "producto":
                producto.to_dict()

        }), 200

    except Exception as error:

        db.session.rollback()

        print(
            "ERROR CAMBIANDO ESTADO PRODUCTO ADMIN:",
            error
        )

        return jsonify({
            "ok": False,
            "mensaje":
                "No fue posible actualizar el producto"
        }), 500
        
        
        
        
        # ============================================================
# ADMINISTRADOR - LISTAR TODOS LOS PEDIDOS REALES
# ============================================================

@app.route(
    "/api/administrador/pedidos",
    methods=["GET"]
)
def administrador_listar_pedidos():

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ADMINISTRADOR
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403


    try:

        pedidos = (
            Pedido.query
            .order_by(
                Pedido.creado_en.desc()
            )
            .all()
        )


        resultado = []


        pendientes = 0
        preparando = 0
        enviados = 0
        completados = 0
        cancelados = 0

        ventas_completadas = 0.0


        # ====================================================
        # RECORRER PEDIDOS
        # ====================================================

        for pedido in pedidos:


            # ------------------------------------------------
            # MASCOTA
            # ------------------------------------------------

            mascota = None


            if pedido.mascota_id:

                mascota = db.session.get(
                    Mascota,
                    pedido.mascota_id
                )


            # ------------------------------------------------
            # COMPRADOR
            # ------------------------------------------------

            comprador = db.session.get(
                Usuario,
                pedido.comprador_id
            )


            # ------------------------------------------------
            # PRODUCTOS DEL PEDIDO
            # ------------------------------------------------

            detalles = (
                DetallePedido.query
                .filter_by(
                    pedido_id=pedido.id
                )
                .order_by(
                    DetallePedido.id.asc()
                )
                .all()
            )


            productos = []


            for detalle in detalles:


                proveedor = db.session.get(
                    Usuario,
                    detalle.proveedor_id
                )


                perfil_proveedor = (
                    PerfilProveedor.query
                    .filter_by(
                        proveedor_id=
                            detalle.proveedor_id
                    )
                    .first()
                )


                proveedor_nombre = (
                    (
                        perfil_proveedor.nombre_comercial
                        if (
                            perfil_proveedor
                            and
                            perfil_proveedor.nombre_comercial
                        )
                        else None
                    )
                    or
                    (
                        proveedor.nombre
                        if proveedor
                        else None
                    )
                    or
                    "Proveedor Huella"
                )


                productos.append({

                    "id":
                        detalle.id,

                    "detalle_id":
                        detalle.id,

                    "pedido_id":
                        detalle.pedido_id,

                    "producto_id":
                        detalle.producto_id,

                    "proveedor_id":
                        detalle.proveedor_id,

                    "proveedor":
                        proveedor_nombre,

                    "nombre":
                        detalle.nombre_producto,

                    "nombre_producto":
                        detalle.nombre_producto,

                    "precio":
                        float(
                            detalle.precio_unitario
                            or
                            0
                        ),

                    "precio_unitario":
                        float(
                            detalle.precio_unitario
                            or
                            0
                        ),

                    "cantidad":
                        int(
                            detalle.cantidad
                            or
                            0
                        ),

                    "subtotal":
                        float(
                            detalle.subtotal
                            or
                            0
                        )

                })


            # ------------------------------------------------
            # ESTADO
            # ------------------------------------------------

            estado = str(
                pedido.estado
                or
                "Pendiente"
            ).strip()


            estado_normalizado = (
                estado.lower()
            )


            if estado_normalizado == "pendiente":

                pendientes += 1


            elif estado_normalizado == "preparando":

                preparando += 1


            elif estado_normalizado == "enviado":

                enviados += 1


            elif estado_normalizado in [
                "completado",
                "entregado"
            ]:

                completados += 1

                ventas_completadas += float(
                    pedido.total
                    or
                    0
                )


            elif estado_normalizado == "cancelado":

                cancelados += 1


            # ------------------------------------------------
            # RESPUESTA DEL PEDIDO
            # ------------------------------------------------

            resultado.append({

                "id":
                    pedido.id,

                "pedido_id":
                    pedido.id,

                "numero":
                    pedido.numero,

                "numeroPedido":
                    pedido.numero,

                "comprador_id":
                    pedido.comprador_id,

                "comprador":
                    (
                        comprador.nombre
                        if comprador
                        else ""
                    ),

                "mascota_id":
                    pedido.mascota_id,

                "mascota":
                    (
                        mascota.nombre
                        if mascota
                        else ""
                    ),

                "cliente":
                    pedido.cliente_nombre,

                "cliente_nombre":
                    pedido.cliente_nombre,

                "telefono":
                    pedido.telefono
                    or
                    "",

                "correo":
                    pedido.correo
                    or
                    "",

                "direccion":
                    pedido.direccion
                    or
                    "",

                "metodoPago":
                    pedido.metodo_pago,

                "metodo_pago":
                    pedido.metodo_pago,

                "tipoEntrega":
                    pedido.tipo_entrega,

                "tipo_entrega":
                    pedido.tipo_entrega,

                "notas":
                    pedido.notas
                    or
                    "",

                "subtotal":
                    float(
                        pedido.subtotal
                        or
                        0
                    ),

                "envio":
                    float(
                        pedido.envio
                        or
                        0
                    ),

                "total":
                    float(
                        pedido.total
                        or
                        0
                    ),

                "estado":
                    pedido.estado,

                "fecha":
                    (
                        pedido.creado_en.isoformat()
                        if pedido.creado_en
                        else None
                    ),

                "creado_en":
                    (
                        pedido.creado_en.isoformat()
                        if pedido.creado_en
                        else None
                    ),

                "actualizado_en":
                    (
                        pedido.actualizado_en.isoformat()
                        if pedido.actualizado_en
                        else None
                    ),

                "productos":
                    productos,

                "productosDetalle":
                    productos

            })


        # ====================================================
        # RESPUESTA GENERAL
        # ====================================================

        return jsonify({

            "ok":
                True,

            "total":
                len(resultado),

            "pedidos":
                resultado,

            "resumen": {

                "total":
                    len(resultado),

                "pendientes":
                    pendientes,

                "preparando":
                    preparando,

                "enviados":
                    enviados,

                "completados":
                    completados,

                "cancelados":
                    cancelados,

                "ventas_completadas":
                    round(
                        ventas_completadas,
                        2
                    )

            }

        }), 200


    except Exception as error:

        print(
            "ERROR LISTANDO PEDIDOS ADMIN:",
            error
        )


        return jsonify({
            "ok": False,
            "mensaje":
                "No fue posible cargar los pedidos"
        }), 500


# ============================================================
# ADMINISTRADOR - CAMBIAR ESTADO DE PEDIDO
# ============================================================

@app.route(
    "/api/administrador/pedidos/<int:pedido_id>/estado",
    methods=["PATCH", "POST"]
)
def administrador_cambiar_estado_pedido(
    pedido_id
):

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({
            "ok": False,
            "mensaje":
                "Debes iniciar sesiÃ³n"
        }), 401


    # ========================================================
    # VALIDAR ROL
    # ========================================================

    if rol != "administrador":

        return jsonify({
            "ok": False,
            "mensaje":
                "Esta funciÃ³n pertenece al Administrador"
        }), 403


    # ========================================================
    # BUSCAR PEDIDO
    # ========================================================

    pedido = db.session.get(
        Pedido,
        pedido_id
    )


    if not pedido:

        return jsonify({
            "ok": False,
            "mensaje":
                "Pedido no encontrado"
        }), 404


    datos = (
        request.get_json(
            silent=True
        )
        or
        {}
    )


    nuevo_estado = str(
        datos.get(
            "estado",
            ""
        )
    ).strip()


    estados_permitidos = [

        "Pendiente",
        "Preparando",
        "Enviado",
        "Completado",
        "Cancelado"

    ]


    if nuevo_estado not in estados_permitidos:

        return jsonify({
            "ok": False,
            "mensaje":
                "Estado de pedido no vÃ¡lido"
        }), 400


    estado_actual = str(
        pedido.estado
        or
        "Pendiente"
    ).strip()


    # ========================================================
    # MISMO ESTADO
    # ========================================================

    if nuevo_estado == estado_actual:

        return jsonify({
            "ok": True,
            "mensaje":
                "El pedido ya tiene ese estado",
            "pedido":
                pedido.to_dict()
        }), 200


    # ========================================================
    # TRANSICIONES PERMITIDAS
    # ========================================================

    transiciones = {

        "Pendiente": [
            "Preparando",
            "Cancelado"
        ],

        "Preparando": [
            "Enviado",
            "Cancelado"
        ],

        "Enviado": [
            "Completado"
        ],

        "Completado": [],

        "Cancelado": [
            "Pendiente"
        ]

    }


    if (
        nuevo_estado
        not in
        transiciones.get(
            estado_actual,
            []
        )
    ):

        return jsonify({
            "ok": False,
            "mensaje":
                (
                    "No se puede cambiar el pedido "
                    f"de {estado_actual} a {nuevo_estado}"
                )
        }), 400


    try:

        # ====================================================
        # CANCELAR -> DEVOLVER STOCK
        # ====================================================

        if (
            nuevo_estado == "Cancelado"
            and
            estado_actual != "Cancelado"
        ):

            _devolver_stock_pedido(
                pedido
            )


        # ====================================================
        # REACTIVAR -> VOLVER A RESERVAR STOCK
        # ====================================================

        if (
            estado_actual == "Cancelado"
            and
            nuevo_estado == "Pendiente"
        ):

            ok_stock, mensaje_stock = (
                _reservar_stock_pedido(
                    pedido
                )
            )


            if not ok_stock:

                db.session.rollback()

                return jsonify({
                    "ok": False,
                    "mensaje":
                        mensaje_stock
                }), 400


        # ====================================================
        # GUARDAR ESTADO
        # ====================================================

        pedido.estado = (
            nuevo_estado
        )


        pedido.actualizado_en = (
            datetime.utcnow()
        )


        db.session.commit()


        return jsonify({

            "ok":
                True,

            "mensaje":
                (
                    "Estado del pedido actualizado correctamente"
                ),

            "pedido":
                pedido.to_dict()

        }), 200


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR CAMBIANDO ESTADO PEDIDO ADMIN:",
            error
        )


        return jsonify({
            "ok": False,
            "mensaje":
                "No fue posible actualizar el pedido"
        }), 500


# ============================================================
# ADMINISTRADOR - VERIFICAR Y APROBAR VETERINARIO
# ============================================================

@app.route(
    "/api/administrador/veterinarios/<int:usuario_id>/verificar",
    methods=["POST"]
)
def administrador_verificar_veterinario(usuario_id):

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({

            "ok": False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    # ========================================================
    # VALIDAR ADMINISTRADOR
    # ========================================================

    if rol != "administrador":

        return jsonify({

            "ok": False,

            "mensaje":
                "Acceso exclusivo para administradores"

        }), 403


    # ========================================================
    # BUSCAR VETERINARIO
    # ========================================================

    veterinario = db.session.get(
        Usuario,
        usuario_id
    )


    if not veterinario:

        return jsonify({

            "ok": False,

            "mensaje":
                "Veterinario no encontrado"

        }), 404


    # ========================================================
    # COMPROBAR ROL
    # ========================================================

    if veterinario.rol != "veterinario":

        return jsonify({

            "ok": False,

            "mensaje":
                "El usuario seleccionado no es veterinario"

        }), 400


    # ========================================================
    # COMPROBAR CÃ‰DULA
    # ========================================================

    cedula = str(
        veterinario.cedula_profesional
        or
        ""
    ).strip()


    if not cedula:

        return jsonify({

            "ok": False,

            "mensaje":
                "El veterinario no tiene una cÃ©dula registrada"

        }), 400


    if not cedula.isdigit():

        return jsonify({

            "ok": False,

            "mensaje":
                "La cÃ©dula registrada no tiene un formato vÃ¡lido"

        }), 400


    if (
        len(cedula) < 6
        or
        len(cedula) > 12
    ):

        return jsonify({

            "ok": False,

            "mensaje":
                "La cÃ©dula registrada no tiene una longitud vÃ¡lida"

        }), 400


    # ========================================================
    # LEER CONFIRMACIÃ“N DEL ADMINISTRADOR
    # ========================================================

    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    confirmado = (
        datos.get(
            "confirmado"
        )
        is True
    )


    if not confirmado:

        return jsonify({

            "ok": False,

            "mensaje":
                (
                    "Debes confirmar que la cÃ©dula fue "
                    "consultada y que coincide con el "
                    "nombre y profesiÃ³n del veterinario."
                )

        }), 400


    # ========================================================
    # BUSCAR VERIFICACIÃ“N
    # ========================================================

    verificacion = (

        VerificacionVeterinario.query

        .filter_by(
            usuario_id=veterinario.id
        )

        .first()

    )


    # ========================================================
    # CREAR VERIFICACIÃ“N SI NO EXISTE
    # ========================================================

    if not verificacion:

        verificacion = VerificacionVeterinario(

            usuario_id=
                veterinario.id,

            estado=
                "Pendiente"

        )


        db.session.add(
            verificacion
        )


    # ========================================================
    # MARCAR COMO VERIFICADO
    # ========================================================

    try:

        veterinario.activo = True


        verificacion.estado = (
            "Verificado"
        )


        verificacion.revisado_por = (
            administrador_id
        )


        verificacion.motivo = (
            "CÃ©dula profesional aprobada por administrador."
        )


        verificacion.fecha_revision = (
            datetime.utcnow()
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR VERIFICANDO VETERINARIO:",
            error
        )


        return jsonify({

            "ok": False,

            "mensaje":
                "No fue posible aprobar al veterinario"

        }), 500


    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({

        "ok": True,

        "mensaje":
            (
                "CÃ©dula confirmada. "
                "La cuenta veterinaria fue activada."
            ),

        "estado_verificacion":
            verificacion.estado,

        "veterinario":
            veterinario.to_dict(),

        "verificacion":
            verificacion.to_dict()

    }), 200


# ============================================================
# ADMINISTRADOR - RECHAZAR VETERINARIO
# ============================================================

@app.route(
    "/api/administrador/veterinarios/<int:usuario_id>/rechazar",
    methods=["POST"]
)
def administrador_rechazar_veterinario(usuario_id):

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({

            "ok": False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    # ========================================================
    # VALIDAR ADMINISTRADOR
    # ========================================================

    if rol != "administrador":

        return jsonify({

            "ok": False,

            "mensaje":
                "Acceso exclusivo para administradores"

        }), 403


    # ========================================================
    # BUSCAR VETERINARIO
    # ========================================================

    veterinario = db.session.get(
        Usuario,
        usuario_id
    )


    if not veterinario:

        return jsonify({

            "ok": False,

            "mensaje":
                "Veterinario no encontrado"

        }), 404


    # ========================================================
    # COMPROBAR ROL
    # ========================================================

    if veterinario.rol != "veterinario":

        return jsonify({

            "ok": False,

            "mensaje":
                "El usuario seleccionado no es veterinario"

        }), 400


    # ========================================================
    # DATOS DEL RECHAZO
    # ========================================================

    datos = (
        request.get_json(
            silent=True
        )
        or {}
    )


    motivo = str(
        datos.get(
            "motivo",
            ""
        )
    ).strip()


    if not motivo:

        motivo = (
            "La cÃ©dula profesional no fue aprobada."
        )


    # ========================================================
    # BUSCAR VERIFICACIÃ“N
    # ========================================================

    verificacion = (

        VerificacionVeterinario.query

        .filter_by(
            usuario_id=veterinario.id
        )

        .first()

    )


    # ========================================================
    # CREAR VERIFICACIÃ“N SI NO EXISTE
    # ========================================================

    if not verificacion:

        verificacion = VerificacionVeterinario(

            usuario_id=
                veterinario.id,

            estado=
                "Pendiente"

        )


        db.session.add(
            verificacion
        )


    # ========================================================
    # RECHAZAR
    # ========================================================

    try:

        veterinario.activo = False


        verificacion.estado = (
            "Rechazado"
        )


        verificacion.revisado_por = (
            administrador_id
        )


        verificacion.motivo = (
            motivo
        )


        verificacion.fecha_revision = (
            datetime.utcnow()
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        print(
            "ERROR RECHAZANDO VETERINARIO:",
            error
        )


        return jsonify({

            "ok": False,

            "mensaje":
                "No fue posible rechazar la verificaciÃ³n"

        }), 500


    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({

        "ok": True,

        "mensaje":
            (
                "La verificaciÃ³n fue rechazada. "
                "La cuenta continuarÃ¡ desactivada."
            ),

        "estado_verificacion":
            verificacion.estado,

        "veterinario":
            veterinario.to_dict(),

        "verificacion":
            verificacion.to_dict()

    }), 200
    
    
    # ============================================================
# ADMINISTRADOR - ESTADOS DE VERIFICACIÃ“N DE VETERINARIOS
# ============================================================

@app.route(
    "/api/administrador/veterinarios/verificaciones",
    methods=["GET"]
)
def administrador_verificaciones_veterinarios():

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not administrador_id:

        return jsonify({

            "ok": False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    if rol != "administrador":

        return jsonify({

            "ok": False,

            "mensaje":
                "Acceso exclusivo para administradores"

        }), 403


    veterinarios = (

        Usuario.query

        .filter_by(
            rol="veterinario"
        )

        .order_by(
            Usuario.fecha_registro.desc()
        )

        .all()

    )


    resultado = []


    for veterinario in veterinarios:

        verificacion = (

            VerificacionVeterinario.query

            .filter_by(
                usuario_id=veterinario.id
            )

            .first()

        )


        # ====================================================
        # ESTADO REAL
        # ====================================================

        if verificacion:

            estado_verificacion = (
                verificacion.estado
                or
                "Pendiente"
            )

            motivo = (
                verificacion.motivo
                or
                ""
            )

            fecha_revision = (
                verificacion.fecha_revision.isoformat()
                if verificacion.fecha_revision
                else None
            )


        else:

            # Veterinarios antiguos que ya estaban activos
            # antes de crear el sistema de verificaciÃ³n.

            if veterinario.activo:

                estado_verificacion = (
                    "Verificado"
                )

                motivo = (
                    "Cuenta veterinaria activa anterior "
                    "al mÃ³dulo de verificaciÃ³n."
                )

            else:

                estado_verificacion = (
                    "Pendiente"
                )

                motivo = (
                    "Pendiente de revisiÃ³n de cÃ©dula profesional."
                )


            fecha_revision = None


        resultado.append({

            "usuario_id":
                veterinario.id,

            "nombre":
                veterinario.nombre,

            "cedula_profesional":
                veterinario.cedula_profesional,

            "activo":
                bool(
                    veterinario.activo
                ),

            "estado_verificacion":
                estado_verificacion,

            "motivo":
                motivo,

            "fecha_revision":
                fecha_revision

        })


    return jsonify({

        "ok": True,

        "total":
            len(
                resultado
            ),

        "verificaciones":
            resultado

    }), 200
    
    
    
    # ============================================================
# ADMINISTRADOR - LISTAR VETERINARIOS CON ESTADO DE VERIFICACIÃ“N
# ============================================================

@app.route(
    "/api/administrador/veterinarios",
    methods=["GET"]
)
def administrador_listar_veterinarios():

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({

            "ok": False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    # ========================================================
    # VALIDAR ADMINISTRADOR
    # ========================================================

    if rol != "administrador":

        return jsonify({

            "ok": False,

            "mensaje":
                "Acceso exclusivo para administradores"

        }), 403


    # ========================================================
    # BUSCAR VETERINARIOS
    # ========================================================

    veterinarios = (

        Usuario.query

        .filter_by(
            rol="veterinario"
        )

        .order_by(
            Usuario.fecha_registro.desc()
        )

        .all()

    )


    resultado = []


    # ========================================================
    # CONSTRUIR RESULTADO
    # ========================================================

    for veterinario in veterinarios:


        verificacion = (

            VerificacionVeterinario.query

            .filter_by(
                usuario_id=veterinario.id
            )

            .first()

        )


        # ====================================================
        # ESTADO DE VERIFICACIÃ“N
        # ====================================================

        if verificacion:

            estado_verificacion = (
                verificacion.estado
                or
                "Pendiente"
            )


            motivo = (
                verificacion.motivo
                or
                ""
            )


            fecha_revision = (

                verificacion.fecha_revision.isoformat()

                if verificacion.fecha_revision

                else None

            )


            fecha_solicitud = (

                verificacion.fecha_solicitud.isoformat()

                if verificacion.fecha_solicitud

                else None

            )


        else:

            # ------------------------------------------------
            # CUENTAS ANTIGUAS
            # ------------------------------------------------
            #
            # Si ya estaba activa antes de crear el sistema
            # de verificaciÃ³n, se considera verificada.
            #
            # Si estÃ¡ inactiva y no tiene registro todavÃ­a,
            # se considera pendiente.
            # ------------------------------------------------

            if veterinario.activo:

                estado_verificacion = (
                    "Verificado"
                )

            else:

                estado_verificacion = (
                    "Pendiente"
                )


            motivo = ""

            fecha_revision = None

            fecha_solicitud = (

                veterinario.fecha_registro.isoformat()

                if veterinario.fecha_registro

                else None

            )


        # ====================================================
        # DATOS DEL USUARIO
        # ====================================================

        datos = (
            veterinario.to_dict()
        )


        # ====================================================
        # AGREGAR DATOS DE VERIFICACIÃ“N
        # ====================================================

        datos[
            "estado_verificacion"
        ] = estado_verificacion


        datos[
            "acceso_activo"
        ] = bool(
            veterinario.activo
        )


        datos[
            "motivo_verificacion"
        ] = motivo


        datos[
            "fecha_revision"
        ] = fecha_revision


        datos[
            "fecha_solicitud"
        ] = fecha_solicitud


        resultado.append(
            datos
        )


    # ========================================================
    # RESPUESTA
    # ========================================================

    return jsonify({

        "ok": True,

        "total":
            len(
                resultado
            ),

        "veterinarios":
            resultado

    }), 200
    
    # ============================================================
# ADMINISTRADOR - LISTAR VETERINARIOS CON VERIFICACIÃ“N REAL
# ============================================================

@app.route(
    "/api/administrador/veterinarios",
    methods=["GET"]
)
def administrador_listar_veterinarios_verificados():

    administrador_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    # ========================================================
    # VALIDAR SESIÃ“N
    # ========================================================

    if not administrador_id:

        return jsonify({

            "ok": False,

            "mensaje":
                "Debes iniciar sesiÃ³n"

        }), 401


    # ========================================================
    # VALIDAR ADMINISTRADOR
    # ========================================================

    if rol != "administrador":

        return jsonify({

            "ok": False,

            "mensaje":
                "Acceso exclusivo para administradores"

        }), 403


    # ========================================================
    # CONSULTAR VETERINARIOS
    # ========================================================

    usuarios = (

        Usuario.query

        .filter_by(
            rol="veterinario"
        )

        .order_by(
            Usuario.fecha_registro.desc()
        )

        .all()

    )


    resultado = []


    # ========================================================
    # CONSTRUIR RESULTADO
    # ========================================================

    for usuario in usuarios:

        verificacion = (

            VerificacionVeterinario.query

            .filter_by(
                usuario_id=usuario.id
            )

            .first()

        )


        # ----------------------------------------------------
        # DETERMINAR ESTADO
        # ----------------------------------------------------

        if verificacion:

            estado_verificacion = (
                verificacion.estado
                or
                "Pendiente"
            )


            motivo_verificacion = (
                verificacion.motivo
                or
                ""
            )


            fecha_revision = (

                verificacion.fecha_revision.isoformat()

                if verificacion.fecha_revision

                else None

            )


        else:

            # Cuenta vieja que ya estaba activa
            if usuario.activo:

                estado_verificacion = (
                    "Verificado"
                )

                motivo_verificacion = (
                    "Cuenta veterinaria activa registrada antes del sistema de verificaciÃ³n."
                )

            else:

                estado_verificacion = (
                    "Pendiente"
                )

                motivo_verificacion = (
                    "CÃ©dula profesional pendiente de revisiÃ³n."
                )


            fecha_revision = None


        datos_usuario = (
            usuario.to_dict()
        )


        datos_usuario[
            "estado_verificacion"
        ] = estado_verificacion


        datos_usuario[
            "motivo_verificacion"
        ] = motivo_verificacion


        datos_usuario[
            "fecha_revision_verificacion"
        ] = fecha_revision


        datos_usuario[
            "puede_iniciar_sesion"
        ] = bool(
            usuario.activo
        )


        resultado.append(
            datos_usuario
        )


    return jsonify({

        "ok": True,

        "total":
            len(resultado),

        "veterinarios":
            resultado

    }), 200
    
    # ============================================================
# CARNET DIGITAL
# DUEÃ‘O + VETERINARIO
# ============================================================

def _pagina_carnet_legacy_sin_ruta():

    usuario_id = session.get(
        "usuario_id"
    )

    rol = session.get(
        "rol"
    )


    if not usuario_id:

        return redirect(
            "/login"
        )


    if rol not in [
        "dueno",
        "veterinario"
    ]:

        return jsonify({
            "ok": False,
            "mensaje": "Acceso disponible solo para DueÃ±o y Veterinario"
        }), 403


    return send_from_directory(
        str(
            BACKEND_DIR
            / "perfiles"
            / "dueno"
        ),
        "carnet.html"
    )
    
    
    # ============================================================
# CARNET DIGITAL COMPARTIDO POR QR
# ============================================================

PUBLIC_CARNET_SNAPSHOTS = {}


# ============================================================
# CREAR COPIA DEL CARNET PARA EL QR
# ============================================================

@app.route(
    "/api/carnet/compartir",
    methods=["POST"]
)
def compartir_carnet():

    usuario_id = session.get("usuario_id")
    rol = str(
        session.get("rol")
        or ""
    ).lower()

    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n."
        }), 401

    if rol not in [
        "dueno",
        "dueÃ±o",
        "veterinario"
    ]:

        return jsonify({
            "ok": False,
            "mensaje": "No tienes permiso para compartir este carnet."
        }), 403

    datos = request.get_json(
        silent=True
    ) or {}

    if not datos:

        return jsonify({
            "ok": False,
            "mensaje": "No se recibieron datos del carnet."
        }), 400

    token = secrets.token_urlsafe(24)

    PUBLIC_CARNET_SNAPSHOTS[token] = datos

    return jsonify({
        "ok": True,
        "token": token
    }), 200


# ============================================================
# CONSULTAR CARNET DEL QR
# NO REQUIERE SESIÃ“N
# ============================================================

@app.route(
    "/api/carnet-publico/<string:token>",
    methods=["GET"]
)
def obtener_carnet_publico(token):

    carnet = PUBLIC_CARNET_SNAPSHOTS.get(
        token
    )

    if not carnet:

        return jsonify({
            "ok": False,
            "mensaje": (
                "El carnet compartido no existe "
                "o dejÃ³ de estar disponible."
            )
        }), 404

    return jsonify({
        "ok": True,
        "carnet": carnet
    }), 200


# ============================================================
# PÃGINA DEL CARNET PÃšBLICO
# UTILIZA EL MISMO DISEÃ‘O
# ============================================================

@app.route("/carnet-publico")
def carnet_publico():

    return send_from_directory(
        str(
            BASE_DIR
            / "perfiles"
            / "dueno"
        ),
        "carnet.html"
    )
    
    
    # ============================================================
# CHATBOT IA DE LA MASCOTA - OLLAMA
# ============================================================

@app.route(
    "/api/chatbot-mascota/ia",
    methods=["POST"]
)
def chatbot_mascota_ia():

    # ========================================================
    # SESIÃ“N
    # ========================================================

    usuario_id = session.get(
        "usuario_id"
    )

    rol = str(
        session.get("rol")
        or ""
    ).lower()


    if not usuario_id:

        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesiÃ³n."
        }), 401


    if rol not in [
        "dueno",
        "dueÃ±o"
    ]:

        return jsonify({
            "ok": False,
            "mensaje": "Esta funciÃ³n pertenece al perfil del dueÃ±o."
        }), 403


    # ========================================================
    # DATOS RECIBIDOS
    # ========================================================

    datos = request.get_json(
        silent=True
    ) or {}


    pregunta = str(
        datos.get(
            "pregunta",
            ""
        )
    ).strip()


    contexto = datos.get(
        "contexto"
    ) or {}


    historial = datos.get(
        "historial"
    ) or []


    if not pregunta:

        return jsonify({
            "ok": False,
            "mensaje": "Escribe una pregunta."
        }), 400


    # ========================================================
    # CONTEXTO DE LA MASCOTA
    # ========================================================

    contexto_texto = json.dumps(
        contexto,
        ensure_ascii=False,
        indent=2
    )


    # ========================================================
    # INSTRUCCIONES DEL ASISTENTE
    # ========================================================

    instrucciones = f"""
Eres Huella IA, un asistente conversacional amable,
claro y Ãºtil integrado en una plataforma para mascotas.

La mascota seleccionada tiene la siguiente informaciÃ³n
registrada en Huella:

{contexto_texto}

REGLAS IMPORTANTES:

1. Responde en espaÃ±ol.
2. Puedes responder preguntas generales, no solamente preguntas
   sobre la mascota.
3. Cuando la pregunta sea sobre la mascota, utiliza primero los
   datos proporcionados por Huella.
4. Nunca inventes vacunas, citas, tratamientos, estudios,
   diagnÃ³sticos, medicamentos, pesos, fechas ni datos veterinarios.
5. Si Huella no contiene un dato, dilo claramente.
6. Puedes explicar conceptos y responder preguntas generales de
   manera conversacional, similar a un asistente de IA.
7. MantÃ©n respuestas claras y naturales.
8. No respondas siempre como si fueras literalmente la mascota.
   Eres un asistente digital de Huella.
9. Puedes mencionar el nombre de la mascota cuando resulte natural.
10. No afirmes diagnÃ³sticos veterinarios basÃ¡ndote Ãºnicamente en
    sÃ­ntomas descritos por el usuario.
11. Si se describe una posible emergencia veterinaria, indica que
    debe buscarse atenciÃ³n veterinaria cuanto antes.
12. No recomiendes medicamentos humanos ni dosis especÃ­ficas sin
    indicaciÃ³n veterinaria.
13. Si el usuario pregunta algo no relacionado con mascotas,
    tambiÃ©n puedes responderlo normalmente.
"""


    # ========================================================
    # MENSAJES PARA OLLAMA
    # ========================================================

    mensajes = [

        {
            "role": "system",
            "content": instrucciones
        }

    ]


    # ========================================================
    # AGREGAR HISTORIAL RECIENTE
    # ========================================================

    if isinstance(
        historial,
        list
    ):

        for mensaje in historial[-12:]:

            if not isinstance(
                mensaje,
                dict
            ):
                continue


            contenido = str(
                mensaje.get(
                    "text",
                    ""
                )
            ).strip()


            if not contenido:
                continue


            role = (

                "assistant"

                if mensaje.get("role") == "bot"

                else "user"

            )


            mensajes.append({

                "role": role,

                "content": contenido

            })


    # ========================================================
    # PREGUNTA ACTUAL
    # ========================================================

    mensajes.append({

        "role": "user",

        "content": pregunta

    })


    # ========================================================
    # MODELO
    # ========================================================

    modelo = os.getenv(
        "HUELLA_OLLAMA_MODEL",
        "qwen2.5:3b"
    )


    payload = {

        "model": modelo,

        "messages": mensajes,

        "stream": False,

        "options": {

            "temperature": 0.7,

            "top_p": 0.9

        }

    }


    # ========================================================
    # CONSULTAR OLLAMA
    # ========================================================

    try:

        respuesta = requests.post(

            "http://127.0.0.1:11434/api/chat",

            json=payload,

            timeout=90

        )


        respuesta.raise_for_status()


        resultado = respuesta.json()


        texto = (

            resultado
            .get(
                "message",
                {}
            )
            .get(
                "content",
                ""
            )
            .strip()

        )


        if not texto:

            return jsonify({
                "ok": False,
                "mensaje": "La IA no generÃ³ una respuesta."
            }), 502


        return jsonify({

            "ok": True,

            "respuesta": texto,

            "modelo": modelo

        }), 200


    except requests.exceptions.ConnectionError:

        return jsonify({

            "ok": False,

            "mensaje": (
                "Ollama no estÃ¡ iniciado. "
                "Abre Ollama y vuelve a intentarlo."
            )

        }), 503


    except requests.exceptions.Timeout:

        return jsonify({

            "ok": False,

            "mensaje": (
                "La IA tardÃ³ demasiado en responder."
            )

        }), 504


    except Exception as error:

        print(
            "ERROR CHATBOT IA:",
            error
        )


        return jsonify({

            "ok": False,

            "mensaje": (
                "No fue posible obtener una respuesta "
                "del asistente."
            )

        }), 500
        
        
        
        # ============================================================
# HUELLA
# GENERACIÃ“N DE VIDEO IA
# ============================================================

@app.route(
    "/api/ia/video",
    methods=["POST"]
)
def crear_video_ia():

    try:

        data = (
            request.get_json(
                silent=True
            )
            or
            {}
        )


        mascota_id = (
            data.get(
                "mascota_id"
            )
        )


        mascota_nombre = str(
            data.get(
                "mascota"
            )
            or
            "Mascota"
        ).strip()


        especie = str(
            data.get(
                "especie"
            )
            or
            "Animal"
        ).strip()


        raza = str(
            data.get(
                "raza"
            )
            or
            ""
        ).strip()


        escena = str(
            data.get(
                "escena"
            )
            or
            "Personalizada"
        ).strip()


        formato = str(
            data.get(
                "formato"
            )
            or
            "9:16"
        ).strip()


        duracion = (
            data.get(
                "duracion"
            )
            or
            5
        )


        prompt_usuario = str(
            data.get(
                "prompt"
            )
            or
            ""
        ).strip()


        imagen = str(
            data.get(
                "imagen"
            )
            or
            ""
        ).strip()


        # ====================================================
        # VALIDACIONES
        # ====================================================

        if not mascota_id:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "No se recibiÃ³ el ID de la mascota."

            }), 400


        if not imagen:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "No se recibiÃ³ la fotografÃ­a de la mascota."

            }), 400


        # ====================================================
        # COMPROBAR QUE LA MASCOTA PERTENECE AL DUEÃ‘O
        # ====================================================

        usuario_id = session.get(
            "usuario_id"
        )


        if not usuario_id:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    "La sesiÃ³n ha expirado."

            }), 401


        mascota_db = (
            Mascota.query
            .filter_by(
                id=mascota_id,
                usuario_id=usuario_id
            )
            .first()
        )


        if not mascota_db:

            return jsonify({

                "ok":
                    False,

                "mensaje":
                    (
                        "La mascota no existe "
                        "o no pertenece a tu cuenta."
                    )

            }), 403


        # ====================================================
        # USAR LOS DATOS REALES DE LA BASE DE DATOS
        # ====================================================

        mascota_nombre = (
            mascota_db.nombre
            or
            mascota_nombre
        )


        especie = (
            mascota_db.especie
            or
            especie
        )


        raza = (
            mascota_db.raza
            or
            raza
        )


        # ====================================================
        # CREAR PROYECTO
        # ====================================================

        proyecto = preparar_proyecto_video(

            mascota_id=
                mascota_db.id,

            mascota=
                mascota_nombre,

            especie=
                especie,

            raza=
                raza,

            escena=
                escena,

            formato=
                formato,

            duracion=
                duracion,

            prompt_usuario=
                prompt_usuario,

            imagen=
                imagen

        )


        # ====================================================
        # ENVIAR AL SERVICIO IA
        # ====================================================

        resultado = generar_video_ia(
            proyecto
        )


        return jsonify({

            "ok":
                True,

            "estado":
                resultado.get(
                    "estado",
                    "preparado"
                ),

            "project_id":
                proyecto[
                    "project_id"
                ],

            "mascota_id":
                mascota_db.id,

            "mascota":
                mascota_nombre,

            "escena":
                proyecto[
                    "escena"
                ],

            "formato":
                proyecto[
                    "formato"
                ],

            "duracion":
                proyecto[
                    "duracion"
                ],

            "width":
                proyecto[
                    "width"
                ],

            "height":
                proyecto[
                    "height"
                ],

            "mensaje":
                resultado.get(
                    "mensaje",
                    "Proyecto preparado correctamente."
                )

        }), 200


    except ValueError as error:

        return jsonify({

            "ok":
                False,

            "mensaje":
                str(
                    error
                )

        }), 400


    except Exception as error:

        print(
            "ERROR EN /api/ia/video:",
            error
        )


        return jsonify({

            "ok":
                False,

            "mensaje":
                (
                    "OcurriÃ³ un error al preparar "
                    "el video con IA."
                ),

            "detalle":
                str(
                    error
                )

        }), 500
    
# ============================================================
# ============================================================
# SERVIR FOTOGRAFIAS DE MASCOTAS
# ============================================================

@app.route("/uploads/mascotas/<path:nombre>")
def servir_foto_mascota(nombre):
    return send_from_directory(
        PET_UPLOAD_DIR,
        nombre
    )


# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":

    print("")

    print(
        "=========================================="
    )

    print(
        "       HUELLA - SERVIDOR INICIADO"
    )

    print(
        "=========================================="
    )

    print("")

    socketio.run(

        app,

        host=
            "0.0.0.0",

        port=
            5000,

        debug=
            True,

        allow_unsafe_werkzeug=
            True

    )
