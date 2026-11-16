# ============================================================
# HUELLA
# PROMPTS PARA GENERACIÓN DE VIDEO IA
# ============================================================


SCENE_PROMPTS = {

    "Saludo": """
The same pet from the reference image looks directly at the camera
and performs a friendly greeting.

The pet naturally raises one front paw and waves several times.

Maintain exactly the same:
- face
- eyes
- fur color
- markings
- breed
- ears
- body proportions
- physical identity

Natural realistic animal movement.
Smooth body motion.
Stable camera.
High visual consistency.
Do not change the identity of the pet.
""",


    "Cumpleaños": """
The same pet from the reference image celebrates a birthday party.

The pet moves happily near a birthday cake,
looks around excitedly,
raises its front paws naturally
and interacts with colorful balloons and confetti.

Maintain exactly the same:
- face
- eyes
- fur
- breed
- markings
- body proportions
- physical identity

Fun birthday atmosphere.
Natural realistic motion.
Cinematic lighting.
Stable camera.
""",


    "Baile": """
The same pet from the reference image performs a playful energetic dance.

The pet stands up naturally,
moves its front paws rhythmically,
moves its body from side to side,
moves its head with the rhythm
and looks toward the camera.

The movement should look fun,
expressive and physically believable.

Maintain exactly the same:
- face
- eyes
- fur color
- markings
- breed
- ears
- body proportions
- physical identity

Natural realistic movement.
Smooth animation.
Stable camera.
Do not create another animal.
""",


    "Cocina": """
The same pet from the reference image behaves like a cheerful cook
inside a cozy modern kitchen.

The pet wears a small chef hat
and naturally interacts with safe cooking utensils.

The pet moves its paws as if preparing food,
looks at the ingredients
and performs playful cooking movements.

Maintain exactly the same:
- face
- eyes
- fur
- breed
- markings
- body proportions
- physical identity

Wholesome humorous scene.
Natural movement.
Cinematic lighting.
Stable camera.
""",


    "Vacaciones": """
The same pet from the reference image enjoys a sunny beach vacation.

The pet walks naturally on the beach,
looks around happily,
plays near the water
and moves its body naturally.

The pet may wear small sunglasses
while keeping its original physical identity.

Maintain exactly the same:
- face
- eyes
- fur
- breed
- markings
- body proportions

Sunny tropical environment.
Natural realistic movement.
Stable cinematic camera.
""",


    "Superhéroe": """
The same pet from the reference image becomes a friendly superhero.

The pet wears a small superhero cape
and performs confident heroic movements.

The cape moves naturally with the motion.

The pet looks toward the camera,
raises a paw
and makes a heroic pose.

Maintain exactly the same:
- face
- eyes
- fur
- breed
- markings
- body proportions
- physical identity

Cinematic superhero atmosphere.
Natural movement.
Stable camera.
""",


    "Baño divertido": """
The same pet from the reference image takes a playful bath.

The pet is surrounded by soft soap bubbles
and moves its paws and head naturally.

The pet interacts playfully with the bubbles
while remaining comfortable and happy.

Maintain exactly the same:
- face
- eyes
- fur
- breed
- markings
- body proportions
- physical identity

Cute wholesome atmosphere.
Natural realistic motion.
Stable camera.
""",


    "Personalizada": """
Create a realistic video using the exact same pet
from the reference image.

Follow the user's requested action and environment.

Maintain exactly the same:
- face
- eyes
- fur color
- markings
- breed
- ears
- body proportions
- physical identity

Natural realistic animal movement.
Smooth animation.
Stable camera.
High visual consistency.
"""

}


# ============================================================
# PROMPT NEGATIVO
# ============================================================

NEGATIVE_PROMPT = """
deformed animal,
distorted face,
different animal,
duplicate animal,
extra legs,
extra paws,
extra ears,
extra eyes,
missing legs,
missing paws,
wrong anatomy,
mutated body,
bad anatomy,
morphing face,
identity change,
different fur color,
different breed,
blurry,
low quality,
flickering,
warped body,
unrealistic deformation,
multiple animals,
duplicate body,
broken limbs,
floating limbs
"""


# ============================================================
# GENERAR PROMPT FINAL
# ============================================================

def obtener_prompt_video(
    escena,
    prompt_usuario="",
    mascota="Mascota",
    especie="animal",
    raza=""
):

    escena = str(
        escena or "Personalizada"
    ).strip()

    prompt_usuario = str(
        prompt_usuario or ""
    ).strip()

    mascota = str(
        mascota or "Mascota"
    ).strip()

    especie = str(
        especie or "animal"
    ).strip()

    raza = str(
        raza or ""
    ).strip()


    prompt_base = SCENE_PROMPTS.get(
        escena,
        SCENE_PROMPTS["Personalizada"]
    )


    informacion_mascota = f"""
Pet information:

Name:
{mascota}

Animal:
{especie}

Breed:
{raza if raza else "Not specified"}

The animal shown in the reference image
must remain visually recognizable
throughout the entire video.
"""


    instrucciones_usuario = ""

    if prompt_usuario:

        instrucciones_usuario = f"""
Additional user instructions:

{prompt_usuario}
"""


    prompt_final = f"""
{informacion_mascota}

{prompt_base}

{instrucciones_usuario}

Important final requirements:

Use the reference image as the identity source.

The pet must remain the same individual animal
from beginning to end.

Generate real body movement,
not only camera zoom or image panning.

The animal should visibly perform
the requested action.

Keep the scene family-friendly.

High temporal consistency.
Natural motion.
Detailed fur.
Realistic anatomy.
"""


    return prompt_final.strip()


# ============================================================
# OBTENER NEGATIVE PROMPT
# ============================================================

def obtener_negative_prompt():

    return NEGATIVE_PROMPT.strip()


# ============================================================
# PRUEBA
# ============================================================

if __name__ == "__main__":

    prompt = obtener_prompt_video(
        escena="Baile",
        prompt_usuario=(
            "Que baile alegremente "
            "y mire a la cámara."
        ),
        mascota="Vainilla",
        especie="Perro",
        raza="Labrador Retriever"
    )

    print(
        "\nPROMPT:\n"
    )

    print(
        prompt
    )

    print(
        "\nNEGATIVE PROMPT:\n"
    )

    print(
        obtener_negative_prompt()
    )