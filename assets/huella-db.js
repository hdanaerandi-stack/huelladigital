(function(){

    'use strict';

    let cachedContext = null;


    /* ============================================================
       NORMALIZAR TEXTO
    ============================================================ */

    function normalize(value){

        return String(
            value ?? ''
        )
        .trim()
        .toLowerCase();

    }



    /* ============================================================
       PROCESAR RESPUESTA DEL SERVIDOR
    ============================================================ */

    async function parseResponse(response){

        let data = {};


        try{

            data =
                await response.json();

        }
        catch(error){}


        if(
            !response.ok ||
            data.ok === false
        ){

            const err =
                new Error(
                    data.mensaje ||
                    (
                        'Error HTTP ' +
                        response.status
                    )
                );


            err.status =
                response.status;


            err.data =
                data;


            throw err;

        }


        return data;

    }



    /* ============================================================
       LISTAR MASCOTAS
    ============================================================ */

    async function listPets(){

        const response =
            await fetch(
                '/api/mascotas',
                {
                    credentials:
                        'same-origin'
                }
            );


        const data =
            await parseResponse(
                response
            );


        return Array.isArray(
            data.mascotas
        )
            ? data.mascotas
            : [];

    }



    /* ============================================================
       CAMBIAR TEXTO DE UN ELEMENTO
    ============================================================ */

    function setTextIfExists(
        id,
        text
    ){

        const el =
            document.getElementById(
                id
            );


        if(el){

            el.textContent =
                text;

        }

    }



    /* ============================================================
       MOSTRAR NOMBRE DE MASCOTA EN LA PÁGINA
    ============================================================ */

    function applyPetName(name){

        [

            'petName',
            'topPetName',
            'subtitlePetName',
            'modalPetName',
            'pagePetName',
            'infoName'

        ].forEach(
            id =>
                setTextIfExists(
                    id,
                    name
                )
        );

    }



    /* ============================================================
       ACTUALIZAR URL Y ENLACES
    ============================================================ */

    function updateUrlAndLinks(pet){

        if(
            !pet ||
            !pet.id
        ){

            return;

        }


        const name =
            pet.nombre ||
            pet.name ||
            'Mascota';



        /* GUARDAR MASCOTA ACTIVA */

        localStorage.setItem(
            'huella_mascota_activa_id',
            String(
                pet.id
            )
        );


        localStorage.setItem(
            'huella_mascota_activa',
            name
        );



        /* ACTUALIZAR URL */

        try{

            const u =
                new URL(
                    window.location.href
                );


            u.searchParams.set(
                'mascota_id',
                String(
                    pet.id
                )
            );


            u.searchParams.set(
                'mascota',
                name
            );


            window.history.replaceState(

                {},

                '',

                u.pathname +
                u.search +
                u.hash

            );

        }
        catch(error){}



        /* ACTUALIZAR ENLACES */

        document
            .querySelectorAll(
                'a[href], [data-pet-page]'
            )
            .forEach(
                el => {

                    let page =
                        el.getAttribute(
                            'data-pet-page'
                        ) ||
                        el.getAttribute(
                            'href'
                        );


                    if(
                        !page ||
                        page === '#' ||
                        /^https?:/i.test(
                            page
                        ) ||
                        page.startsWith(
                            'mailto:'
                        ) ||
                        page.startsWith(
                            'tel:'
                        ) ||
                        page.startsWith(
                            'javascript:'
                        )
                    ){

                        return;

                    }


                    if(
                        page.includes(
                            '../dueno.html'
                        ) ||
                        page.includes(
                            'ajustes.html'
                        )
                    ){

                        return;

                    }


                    try{

                        const temp =
                            new URL(
                                page,
                                window.location.href
                            );


                        if(
                            temp.origin !==
                            window.location.origin
                        ){

                            return;

                        }


                        temp.searchParams.set(
                            'mascota_id',
                            String(
                                pet.id
                            )
                        );


                        temp.searchParams.set(
                            'mascota',
                            name
                        );


                        const rel =
                            temp.pathname
                                .split('/')
                                .pop();


                        if(
                            el.hasAttribute(
                                'data-pet-page'
                            )
                        ){

                            el.setAttribute(
                                'href',
                                rel +
                                temp.search
                            );

                        }

                    }
                    catch(error){}

                }
            );

    }



    /* ============================================================
       RESOLVER MASCOTA ACTUAL
    ============================================================ */

    async function resolvePetContext(force){

        if(
            cachedContext &&
            !force
        ){

            return cachedContext;

        }


        const q =
            new URLSearchParams(
                window.location.search
            );


        const requestedId =
            Number(

                q.get(
                    'mascota_id'
                ) ||

                q.get(
                    'id'
                ) ||

                localStorage.getItem(
                    'huella_mascota_activa_id'
                ) ||

                0

            );


        const requestedName =
            (

                q.get(
                    'mascota'
                ) ||

                localStorage.getItem(
                    'huella_mascota_activa'
                ) ||

                ''

            ).trim();



        /* CARGAR MASCOTAS */

        const pets =
            await listPets();


        if(
            !pets.length
        ){

            throw new Error(
                'No hay mascotas registradas. Registra una mascota primero.'
            );

        }



        let pet = null;



        /* BUSCAR POR ID */

        if(
            requestedId
        ){

            pet =
                pets.find(
                    p =>
                        Number(
                            p.id
                        ) ===
                        requestedId
                ) ||
                null;

        }



        /* BUSCAR POR NOMBRE */

        if(
            !pet &&
            requestedName
        ){

            pet =
                pets.find(
                    p =>
                        normalize(
                            p.nombre ||
                            p.name
                        ) ===
                        normalize(
                            requestedName
                        )
                ) ||
                null;

        }



        /* SI NO SE ENCUENTRA,
           USAR LA PRIMERA */

        if(
            !pet
        ){

            pet =
                pets[0];

        }



        const name =
            pet.nombre ||
            pet.name ||
            'Mascota';



        /* GUARDAR CONTEXTO */

        cachedContext = {

            id:
                Number(
                    pet.id
                ),

            name:
                name,

            pet:
                pet,

            pets:
                pets

        };



        /* MOSTRAR NOMBRE */

        applyPetName(
            name
        );



        /* ACTUALIZAR ENLACES */

        updateUrlAndLinks(
            pet
        );


        return cachedContext;

    }



    /* ============================================================
       LEER DATOS ANTIGUOS DE LOCALSTORAGE
    ============================================================ */

    function readLegacy(keys){

        for(
            const key of
            (
                keys ||
                []
            )
        ){

            if(
                !key
            ){

                continue;

            }


            const raw =
                localStorage.getItem(
                    key
                );


            if(
                !raw
            ){

                continue;

            }


            try{

                return JSON.parse(
                    raw
                );

            }
            catch(error){}

        }


        return undefined;

    }



    /* ============================================================
       CARGAR MÓDULO DE UNA MASCOTA
    ============================================================ */

    async function loadPetModule(
        module,
        fallback,
        legacyKeys
    ){

        const ctx =
            await resolvePetContext();



        const response =
            await fetch(

                '/api/mascotas/' +
                encodeURIComponent(
                    ctx.id
                ) +
                '/modulos/' +
                encodeURIComponent(
                    module
                ),

                {
                    credentials:
                        'same-origin'
                }

            );



        const data =
            await parseResponse(
                response
            );



        /* SI YA EXISTE EN LA BD */

        if(
            data.existe
        ){

            return data.datos;

        }



        /* BUSCAR DATOS ANTIGUOS */

        const legacy =
            readLegacy(
                legacyKeys
            );



        if(
            legacy !==
            undefined
        ){

            await savePetModule(
                module,
                legacy
            );


            return legacy;

        }



        /* DATOS POR DEFECTO */

        return (
            typeof fallback ===
            'function'
        )
            ? fallback()
            : fallback;

    }



    /* ============================================================
       GUARDAR MÓDULO DE UNA MASCOTA
    ============================================================ */

    async function savePetModule(
        module,
        data
    ){

        const ctx =
            await resolvePetContext();



        const response =
            await fetch(

                '/api/mascotas/' +
                encodeURIComponent(
                    ctx.id
                ) +
                '/modulos/' +
                encodeURIComponent(
                    module
                ),

                {

                    method:
                        'PUT',

                    credentials:
                        'same-origin',

                    headers:{

                        'Content-Type':
                            'application/json'

                    },

                    body:
                        JSON.stringify(
                            {
                                datos:
                                    data
                            }
                        )

                }

            );


        return parseResponse(
            response
        );

    }



    /* ============================================================
       OBTENER MASCOTA ACTUAL
    ============================================================ */

    async function getPet(){

        const ctx =
            await resolvePetContext();


        return ctx.pet;

    }



    /* ============================================================
       OBTENER CONTEXTO ACTUAL
    ============================================================ */

    function currentContext(){

        return cachedContext;

    }



    /* ============================================================
       EXPORTAR FUNCIONES
    ============================================================ */

    window.HuellaDB = {

        resolvePetContext:
            resolvePetContext,

        loadPetModule:
            loadPetModule,

        savePetModule:
            savePetModule,

        getPet:
            getPet,

        currentContext:
            currentContext,

        applyPetName:
            applyPetName,

        updateUrlAndLinks:
            updateUrlAndLinks

    };


})();