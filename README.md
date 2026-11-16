# HUELLA DIGITAL

Plataforma web para la gestión integral y el seguimiento de mascotas.

## Descripción
Proyecto de software orientado a centralizar información de mascotas, propietarios, atención veterinaria y servicios para animales.

## Tecnologías
- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- HTML5
- CSS3
- JavaScript
- Gunicorn
- Docker

## Perfiles
- Dueño o tutor.
- Médico veterinario.
- Proveedor.
- Administrador.

## Funcionalidades contempladas
- Registro y gestión de mascotas.
- Información de salud y expedientes veterinarios.
- Citas y tratamientos.
- Servicios y productos.
- Administración de usuarios.
- Funciones de ubicación y seguimiento.

La disponibilidad de cada función depende de su implementación y configuración.

## Estructura
- backend/: lógica y servidor.
- assets/: imágenes, estilos y JavaScript.
- index.html: página principal.
- login.html: acceso.
- registro.html: registro.
- app.html: interfaz principal.
- requirements.txt: dependencias.
- Dockerfile: configuración de Docker.

## Ejecución
Construir la imagen con Docker mediante:
docker build -t huella-digital .

La aplicación utiliza el puerto 5000 dentro del contenedor.

## Privacidad
La publicación comienza con una base de datos limpia. No se deben incluir bases de datos personales, fotografías privadas, contraseñas ni credenciales.

## Estado
Proyecto en preparación para despliegue y validación en servidor.
