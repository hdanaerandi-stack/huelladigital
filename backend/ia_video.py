# ============================================================
# HUELLA
# SERVICIO DE GENERACIÓN DE VIDEO IA
# ============================================================

from pathlib import Path
from datetime import datetime
import uuid

from prompts_video import (
    obtener_prompt_video,
    obtener_negative_prompt
)


# ============================================================
# RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

VIDEO_OUTPUT_DIR = (
    BASE_DIR
    / "uploads"
    / "videos_ia"
)

VIDEO_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# ESCENAS PERMITIDAS
# ============================================================

ESCENAS_PERMITIDAS = {
    "Saludo",
    "Cumpleaños",
    "Baile",
    "Cocina",
    "Vacaciones",
    "Superhéroe",
    "Baño divertido",
    "Personalizada"
}


# ============================================================
# FORMATOS
# ============================================================

FORMATOS = {

    "9:16": {
        "width": 576,
        "height": 1024
    },

    "1:1": {
        "width": 768,
        "height": 768
    },

    "16:9": {
        "width": 1024,
        "height": 576
    }

}


# ============================================================
# VALIDAR DATOS
# ============================================================

def validar_solicitud_video(
    mascota_id,
    escena,
    formato,
    duracion
):

    if not mascota_id:

        raise ValueError(
            "No se recibió el ID de la mascota."
        )


    escena = str(
        escena or ""
    ).strip()


    if escena not in ESCENAS_PERMITIDAS:

        raise ValueError(
            "La escena seleccionada no es válida."
        )


    formato = str(
        formato or ""
    ).strip()


    if formato not in FORMATOS:

        raise ValueError(
            "El formato de video no es válido."
        )


    try:

        duracion = int(
            duracion
        )

    except (
        TypeError,
        ValueError
    ):

        duracion = 5


    if duracion not in {
        5,
        8,
        10
    }:

        raise ValueError(
            "La duración debe ser 5, 8 o 10 segundos."
        )


    return {
        "escena": escena,
        "formato": formato,
        "duracion": duracion
    }


# ============================================================
# PREPARAR PROYECTO
# ============================================================

def preparar_proyecto_video(
    mascota_id,
    mascota,
    especie,
    raza,
    escena,
    formato,
    duracion,
    prompt_usuario="",
    imagen=""
):

    validado = validar_solicitud_video(

        mascota_id,
        escena,
        formato,
        duracion

    )


    escena = validado[
        "escena"
    ]

    formato = validado[
        "formato"
    ]

    duracion = validado[
        "duracion"
    ]


    prompt_final = obtener_prompt_video(

        escena=escena,

        prompt_usuario=prompt_usuario,

        mascota=mascota,

        especie=especie,

        raza=raza

    )


    negative_prompt = (
        obtener_negative_prompt()
    )


    dimensiones = FORMATOS[
        formato
    ]


    project_id = (
        "huella_"
        +
        uuid.uuid4().hex
    )


    nombre_archivo = (

        project_id
        +
        ".mp4"

    )


    ruta_salida = (
        VIDEO_OUTPUT_DIR
        /
        nombre_archivo
    )


    proyecto = {

        "project_id":
            project_id,

        "mascota_id":
            mascota_id,

        "mascota":
            str(
                mascota
                or
                "Mascota"
            ),

        "especie":
            str(
                especie
                or
                "Animal"
            ),

        "raza":
            str(
                raza
                or
                ""
            ),

        "escena":
            escena,

        "formato":
            formato,

        "duracion":
            duracion,

        "width":
            dimensiones[
                "width"
            ],

        "height":
            dimensiones[
                "height"
            ],

        "prompt":
            prompt_final,

        "negative_prompt":
            negative_prompt,

        "imagen":
            imagen,

        "nombre_archivo":
            nombre_archivo,

        "ruta_salida":
            str(
                ruta_salida
            ),

        "creado_en":
            datetime.now()
            .isoformat()

    }


    return proyecto


# ============================================================
# GENERADOR IA
# ============================================================

def generar_video_ia(
    proyecto
):

    """
    Esta función será la encargada de enviar
    el proyecto al motor real de generación
    Image-to-Video.

    Por ahora comprobamos que Huella reciba
    correctamente todos los datos.

    En el siguiente paso se conecta aquí
    el proveedor/motor de video IA.
    """


    if not proyecto:

        raise ValueError(
            "El proyecto de video está vacío."
        )


    print(
        "\n"
        +
        "=" * 60
    )

    print(
        "HUELLA · PROYECTO VIDEO IA"
    )

    print(
        "=" * 60
    )


    print(
        "Proyecto:",
        proyecto.get(
            "project_id"
        )
    )


    print(
        "Mascota:",
        proyecto.get(
            "mascota"
        )
    )


    print(
        "Escena:",
        proyecto.get(
            "escena"
        )
    )


    print(
        "Formato:",
        proyecto.get(
            "formato"
        )
    )


    print(
        "Resolución:",
        proyecto.get(
            "width"
        ),
        "x",
        proyecto.get(
            "height"
        )
    )


    print(
        "Duración:",
        proyecto.get(
            "duracion"
        ),
        "segundos"
    )


    print(
        "\nPROMPT:\n"
    )


    print(
        proyecto.get(
            "prompt"
        )
    )


    print(
        "\nNEGATIVE PROMPT:\n"
    )


    print(
        proyecto.get(
            "negative_prompt"
        )
    )


    print(
        "\n"
        +
        "=" * 60
    )


    return {

        "ok":
            True,

        "estado":
            "preparado",

        "project_id":
            proyecto[
                "project_id"
            ],

        "mensaje":
            (
                "Proyecto de video IA "
                "preparado correctamente."
            )

    }


# ============================================================
# PRUEBA LOCAL
# ============================================================

if __name__ == "__main__":

    proyecto = preparar_proyecto_video(

        mascota_id=4,

        mascota="Vainilla",

        especie="Perro",

        raza="Labrador Retriever",

        escena="Baile",

        formato="9:16",

        duracion=5,

        prompt_usuario=(
            "Que baile alegremente "
            "y mire a la cámara."
        ),

        imagen=(
            "/uploads/mascotas/"
            "vainilla.jpg"
        )

    )


    resultado = generar_video_ia(
        proyecto
    )


    print(
        "\nRESULTADO:\n"
    )


    print(
        resultado
    )