/* ============================================================
   HUELLA · CONTROL GLOBAL DE MEMBRESÍAS
============================================================ */

(function(){

    "use strict";


    const MEMBERSHIP_KEY =
        "huella_membresia";


    const PERMISSIONS_KEY =
        "huella_permisos_membresia";


    /* ========================================================
       REGLAS DE ACCESO
    ======================================================== */

    const PAGE_RULES = {

        "expediente.html":
            "expediente",

        "vacunas.html":
            "vacunas",

        "citas.html":
            "citas",

        "estudios.html":
            "documentos",

        "gps.html":
            "gps",

        "geocercas.html":
            "geocercas",

        "reportes.html":
            "reportes",

        "familia.html":
            "accesoFamiliar"

    };


    /* ========================================================
       PLAN MÍNIMO PARA CADA FUNCIÓN
    ======================================================== */

    const FEATURE_PLAN_NAME = {

        expediente:
            "Plan Básico",

        vacunas:
            "Plan Básico",

        citas:
            "Plan Básico",

        recordatorios:
            "Plan Básico",

        documentos:
            "Plan Esencial",

        gps:
            "Huella Plus",

        geocercas:
            "Huella Plus",

        historialGps:
            "Huella Plus",

        reportes:
            "Plan Premium",

        accesoFamiliar:
            "Plan Premium",

        veterinario:
    "Plan Premium",

telemedicina:
    "Plan Premium",

soportePrioritario:
    "Huella Pro"

    };


    /* ========================================================
       OBTENER MEMBRESÍA
    ======================================================== */

    function getMembership(){

        try{

            const membership =
                JSON.parse(

                    localStorage.getItem(
                        MEMBERSHIP_KEY
                    )

                    ||

                    "null"

                );


            if(!membership){

                return null;

            }


            return membership;

        }
        catch(error){

            console.error(
                "No fue posible leer la membresía:",
                error
            );


            return null;

        }

    }


    /* ========================================================
       ¿ESTÁ ACTIVA?
    ======================================================== */

    function isMembershipActive(){

        const membership =
            getMembership();


        if(!membership){

            return false;

        }


        if(
            membership.status !==
            "Activa"
        ){

            return false;

        }


        if(!membership.expiry){

            return false;

        }


        const expiry =
            new Date(
                membership.expiry
            );


        if(
            Number.isNaN(
                expiry.getTime()
            )
        ){

            return false;

        }


        if(
            expiry.getTime() <
            Date.now()
        ){

            membership.status =
                "Vencida";


            localStorage.setItem(

                MEMBERSHIP_KEY,

                JSON.stringify(
                    membership
                )

            );


            return false;

        }


        return true;

    }


    /* ========================================================
       COMPROBAR PERMISO
    ======================================================== */

    function hasFeature(
        feature
    ){

        const membership =
            getMembership();


        if(
            !membership
            ||
            !isMembershipActive()
        ){

            return false;

        }


        return Boolean(

            membership.permissions

            &&

            membership.permissions[
                feature
            ] ===
            true

        );

    }


    /* ========================================================
       LÍMITE DE MASCOTAS
    ======================================================== */

    function getPetLimit(){

        const membership =
            getMembership();


        if(
            !membership
            ||
            !isMembershipActive()
        ){

            return 0;

        }


        return Number(
            membership.maxPets ??
            0
        );

    }


    /* ========================================================
       ¿PUEDE AGREGAR OTRA MASCOTA?
    ======================================================== */

    function canAddPet(
        currentPetCount
    ){

        const limit =
            getPetLimit();


        /*
            -1 significa ilimitado.
        */

        if(
            limit ===
            -1
        ){

            return true;

        }


        return (

            Number(
                currentPetCount
            )

            <

            limit

        );

    }


    /* ========================================================
       NOMBRE DEL PLAN NECESARIO
    ======================================================== */

    function requiredPlanName(
        feature
    ){

        return (

            FEATURE_PLAN_NAME[
                feature
            ]

            ||

            "un plan superior"

        );

    }


    /* ========================================================
       MOSTRAR BLOQUEO
    ======================================================== */

    function showBlockedScreen(
        feature
    ){

        const minimumPlan =
            requiredPlanName(
                feature
            );


        const membership =
            getMembership();


        let currentText =
            "Sin membresía activa";


        if(membership){

            currentText =

                membership.name

                ?

                "Plan actual: " +
                membership.name

                :

                "Membresía no disponible";

        }


        const overlay =
            document.createElement(
                "div"
            );


        overlay.id =
            "huellaMembershipBlock";


        overlay.innerHTML = `

            <div
                style="
                    position:fixed;
                    inset:0;
                    z-index:999999;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    padding:25px;
                    background:rgba(0,34,44,.78);
                    backdrop-filter:blur(7px);
                "
            >

                <div
                    style="
                        width:min(520px,100%);
                        padding:32px;
                        border-radius:24px;
                        background:white;
                        box-shadow:0 30px 80px rgba(0,0,0,.28);
                        text-align:center;
                        font-family:'Plus Jakarta Sans',Arial,sans-serif;
                    "
                >

                    <div
                        style="
                            width:70px;
                            height:70px;
                            margin:0 auto;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            border-radius:50%;
                            background:#eef6f7;
                            color:#07505e;
                        "
                    >

                        <span
                            class="material-symbols-outlined"
                            style="font-size:38px;"
                        >
                            lock
                        </span>

                    </div>


                    <h2
                        style="
                            margin-top:18px;
                            color:#00303c;
                            font-family:'Playfair Display',serif;
                            font-size:30px;
                        "
                    >
                        Función no incluida
                    </h2>


                    <p
                        style="
                            margin-top:10px;
                            color:#657277;
                            font-size:13px;
                            line-height:1.7;
                        "
                    >

                        Esta función requiere

                        <strong
                            style="
                                color:#00303c;
                            "
                        >
                            ${escapeHTML(minimumPlan)}
                        </strong>

                        o un plan superior.

                    </p>


                    <div
                        style="
                            margin-top:16px;
                            padding:12px;
                            border-radius:11px;
                            background:#f5f8f9;
                            color:#637176;
                            font-size:12px;
                        "
                    >

                        ${escapeHTML(currentText)}

                    </div>


                    <div
                        style="
                            margin-top:22px;
                            display:flex;
                            justify-content:center;
                            gap:10px;
                            flex-wrap:wrap;
                        "
                    >


                        <button
                            type="button"
                            id="huellaMembershipBack"
                            style="
                                border:0;
                                padding:11px 16px;
                                border-radius:10px;
                                background:#edf3f5;
                                color:#00303c;
                                font-weight:800;
                                cursor:pointer;
                            "
                        >

                            Volver

                        </button>


                        <button
                            type="button"
                            id="huellaMembershipUpgrade"
                            style="
                                border:0;
                                padding:11px 16px;
                                border-radius:10px;
                                background:#073d49;
                                color:white;
                                font-weight:800;
                                cursor:pointer;
                            "
                        >

                            Ver membresías

                        </button>


                    </div>


                </div>

            </div>

        `;


        document.body.appendChild(
            overlay
        );


        document.getElementById(
            "huellaMembershipBack"
        )
        .addEventListener(
            "click",
            function(){

                if(
                    window.history.length >
                    1
                ){

                    window.history.back();

                }
                else{

                    window.location.href =
                        "../dueno.html";

                }

            }
        );


        document.getElementById(
            "huellaMembershipUpgrade"
        )
        .addEventListener(
            "click",
            function(){

                const params =
                    new URLSearchParams(
                        window.location.search
                    );


                let url =
                    "membresias.html";


                if(
                    params.toString()
                ){

                    url +=

                        "?"

                        +

                        params.toString();

                }


                window.location.href =
                    url;

            }
        );

    }


    /* ========================================================
       PROTEGER FUNCIÓN MANUALMENTE
    ======================================================== */

    function requireFeature(
        feature
    ){

        if(
            hasFeature(
                feature
            )
        ){

            return true;

        }


        showBlockedScreen(
            feature
        );


        return false;

    }


    /* ========================================================
       PROTEGER PÁGINA ACTUAL
    ======================================================== */

    function protectCurrentPage(){

        const page =
            window.location.pathname
            .split("/")
            .pop()
            .toLowerCase();


        const feature =
            PAGE_RULES[
                page
            ];


        /*
            Si la página no tiene regla,
            no se bloquea.
        */

        if(!feature){

            return true;

        }


        if(
            hasFeature(
                feature
            )
        ){

            return true;

        }


        showBlockedScreen(
            feature
        );


        return false;

    }


    /* ========================================================
       DESHABILITAR ENLACES DEL MENÚ
    ======================================================== */

    function updateMenuLinks(){

        const links =
            document.querySelectorAll(
                "a"
            );


        links.forEach(
            function(link){

                const href =
                    link.getAttribute(
                        "href"
                    );

                if(!href){

                    return;

                }


                const clean =
                    href
                    .split("?")[0]
                    .split("/")
                    .pop()
                    .toLowerCase();


                const feature =
                    PAGE_RULES[
                        clean
                    ];


                if(!feature){

                    return;

                }


                if(
                    hasFeature(
                        feature
                    )
                ){

                    link.classList.remove(
                        "huella-plan-locked"
                    );


                    return;

                }


                link.classList.add(
                    "huella-plan-locked"
                );


                link.style.opacity =
                    ".55";


                link.style.position =
                    "relative";


                link.title =

                    "Requiere " +

                    requiredPlanName(
                        feature
                    );


                /*
                    No anulamos el onclick original,
                    porque algunas páginas usan goPage().
                    Añadimos captura antes.
                */

                link.addEventListener(

                    "click",

                    function(event){

                        event.preventDefault();

                        event.stopImmediatePropagation();


                        showBlockedScreen(
                            feature
                        );

                    },

                    true

                );

            }
        );

    }


    /* ========================================================
       OBTENER INFORMACIÓN DEL PLAN
    ======================================================== */

    function getPlanInfo(){

        const membership =
            getMembership();


        if(!membership){

            return {

                active:
                    false,

                name:
                    "Sin membresía",

                permissions:
                    {},

                maxPets:
                    0

            };

        }


        return {

            active:
                isMembershipActive(),

            name:
                membership.name,

            id:
                membership.id,

            expiry:
                membership.expiry,

            permissions:
                membership.permissions ||
                {},

            maxPets:
                Number(
                    membership.maxPets ??
                    0
                )

        };

    }


    /* ========================================================
       ESCAPAR HTML
    ======================================================== */

    function escapeHTML(
        value
    ){

        return String(
            value ??
            ""
        )

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );

    }


/* ============================================================
   COMPROBAR PERMISO REAL DESDE FLASK / SQLITE
============================================================ */

async function checkFeatureServer(feature){

    try{

        const response = await fetch(

            "/api/membresia/permiso/"
            +
            encodeURIComponent(feature),

            {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    "Accept": "application/json"
                }
            }

        );


        const data = await response.json();


        if(response.status === 401){

            return {
                ok: false,
                permitido: false,
                mensaje: "Debes iniciar sesión"
            };

        }


        if(
            !response.ok
            ||
            data.ok === false
        ){

            return {
                ok: false,
                permitido: false,
                mensaje:
                    data.mensaje
                    ||
                    "No fue posible comprobar la membresía"
            };

        }


        return data;

    }
    catch(error){

        console.error(
            "Error verificando permiso:",
            error
        );


        return {
            ok: false,
            permitido: false,
            mensaje:
                "No fue posible conectar con el servidor"
        };

    }

}


/* ============================================================
   EXIGIR PERMISO REAL DEL SERVIDOR
============================================================ */

async function requireFeatureServer(feature){

    const result =
        await checkFeatureServer(feature);


    if(result.permitido){

        return true;

    }


    showBlocked(feature);

    return false;

}


    /* ========================================================
       API GLOBAL
    ======================================================== */

    window.HuellaMembership = {

        

        getMembership:
            getMembership,

        isActive:
            isMembershipActive,

        hasFeature:
            hasFeature,

        requireFeature:
            requireFeature,

        protectCurrentPage:
            protectCurrentPage,

        getPetLimit:
            getPetLimit,

        canAddPet:
            canAddPet,

        requiredPlanName:
            requiredPlanName,

        getPlanInfo:
            getPlanInfo,

         checkFeatureServer,
requireFeatureServer,

        updateMenuLinks:
            updateMenuLinks

    };


    /* ========================================================
       INICIO AUTOMÁTICO
    ======================================================== */

    document.addEventListener(

        "DOMContentLoaded",

        function(){

            protectCurrentPage();

            updateMenuLinks();

        }

    );

})();