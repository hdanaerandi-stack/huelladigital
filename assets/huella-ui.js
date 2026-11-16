(function(){

    "use strict";


    /* =========================================================
       HUELLA · SISTEMA GLOBAL DE APARIENCIA V30
    ========================================================= */


    const SCRIPT_SRC =
        document.currentScript
            ? document.currentScript.src
            : "";


    const THEMES = [

    "normal",

    "negro-profundo",

    "futurista",

    "futurista-neon",

    "futurista-dorado",

    "minimal-pastel",

    "oceano-turquesa",

    "costa-natural",

    "bosque-verde",

    "brote-oliva",

    "personalizado"

];


    const DEFAULTS = {

        theme:
            "normal",

        motion:
            true

    };


    /* =========================================================
       DETECTAR PERFIL
    ========================================================= */

    function detectRole(){

        const path =
            decodeURIComponent(
                window.location.pathname ||
                ""
            )
            .toLowerCase()
            .replace(
                /\\/g,
                "/"
            );


        if(
            path.includes(
                "/perfiles/dueno/"
            )
            ||
            path.endsWith(
                "/perfiles/dueno.html"
            )
        ){

            return "dueno";

        }


        if(
            path.includes(
                "/perfiles/veterinario/"
            )
            ||
            path.endsWith(
                "/perfiles/veterinario.html"
            )
        ){

            return "veterinario";

        }


        if(
            path.includes(
                "/perfiles/proveedor/"
            )
            ||
            path.endsWith(
                "/perfiles/proveedor.html"
            )
        ){

            return "proveedor";

        }


        if(
            path.includes(
                "/perfiles/administrador/"
            )
            ||
            path.endsWith(
                "/perfiles/administrador.html"
            )
        ){

            return "administrador";

        }


        return "general";

    }


    const ROLE =
        detectRole();


    const STORAGE_KEY =

        ROLE === "general"

        ?

        "huellaAppearance"

        :

        "huellaAppearance:" +
        ROLE;


    const CUSTOM_KEY =

        ROLE === "general"

        ?

        "huellaCustomTheme"

        :

        "huellaCustomTheme:" +
        ROLE;


    const COOKIE_KEY =

        "huellaAppearance_" +
        ROLE;


    /* =========================================================
       NORMALIZAR
    ========================================================= */

    function normalize(
        raw
    ){

        let theme =

            raw &&
            typeof raw.theme ===
            "string"

            ?

            raw.theme

            :

            "normal";


        if(
            theme ===
            "future"
        ){

            theme =
                "futurista";

        }


        /*
            IMPORTANTE:

            negro-profundo ahora SÍ está
            incluido en la lista válida.
        */

        if(
            !THEMES.includes(
                theme
            )
        ){

            theme =
                "normal";

        }


        return {

            theme:
                theme,

            motion:
                !(
                    raw &&
                    raw.motion ===
                    false
                )

        };

    }


    /* =========================================================
       COOKIE
    ========================================================= */

    function readCookie(){

        try{

            const prefix =
                COOKIE_KEY +
                "=";


            const item =
                document.cookie
                    .split(";")
                    .map(
                        value =>
                            value.trim()
                    )
                    .find(
                        value =>
                            value.startsWith(
                                prefix
                            )
                    );


            if(!item){

                return null;

            }


            return normalize(

                JSON.parse(

                    decodeURIComponent(

                        item.substring(
                            prefix.length
                        )

                    )

                )

            );

        }
        catch(error){

            return null;

        }

    }


    function writeCookie(
        settings
    ){

        try{

            const data =
                encodeURIComponent(

                    JSON.stringify(

                        normalize(
                            settings
                        )

                    )

                );


            document.cookie =

                COOKIE_KEY +
                "=" +
                data +
                ";" +

                "Max-Age=31536000;" +

                "Path=/;" +

                "SameSite=Lax";


            return true;

        }
        catch(error){

            console.warn(
                "No se pudo guardar la apariencia.",
                error
            );


            return false;

        }

    }


    /* =========================================================
       LEER CONFIGURACIÓN
    ========================================================= */

    function readSettings(){

        /*
            1. LOCAL STORAGE
        */

        try{

            const raw =
                localStorage.getItem(
                    STORAGE_KEY
                );


            if(raw){

                const settings =
                    normalize(
                        JSON.parse(
                            raw
                        )
                    );


                writeCookie(
                    settings
                );


                return settings;

            }

        }
        catch(error){}


        /*
            2. COOKIE
        */

        const cookie =
            readCookie();


        if(cookie){

            try{

                localStorage.setItem(

                    STORAGE_KEY,

                    JSON.stringify(
                        cookie
                    )

                );

            }
            catch(error){}


            return cookie;

        }


        /*
            3. SESSION STORAGE
        */

        try{

            const raw =
                sessionStorage.getItem(
                    STORAGE_KEY
                );


            if(raw){

                const settings =
                    normalize(
                        JSON.parse(
                            raw
                        )
                    );


                return settings;

            }

        }
        catch(error){}


        /*
            4. CONFIGURACIÓN ANTIGUA
        */

        if(
            ROLE !==
            "general"
        ){

            try{

                const old =
                    localStorage.getItem(
                        "huellaAppearance"
                    );


                if(old){

                    const settings =
                        normalize(
                            JSON.parse(
                                old
                            )
                        );


                    saveSettings(
                        settings
                    );


                    return settings;

                }

            }
            catch(error){}

        }


        return {
            ...DEFAULTS
        };

    }


    /* =========================================================
       GUARDAR CONFIGURACIÓN
    ========================================================= */

    function saveSettings(
        settings
    ){

        const normalized =
            normalize(
                settings
            );


        try{

            localStorage.setItem(

                STORAGE_KEY,

                JSON.stringify(
                    normalized
                )

            );

        }
        catch(error){}


        try{

            sessionStorage.setItem(

                STORAGE_KEY,

                JSON.stringify(
                    normalized
                )

            );

        }
        catch(error){}


        writeCookie(
            normalized
        );


        return normalized;

    }


    /* =========================================================
       DISEÑO PERSONALIZADO
    ========================================================= */

    function getCustomTheme(){

        try{

            const raw =
                JSON.parse(

                    localStorage.getItem(
                        CUSTOM_KEY
                    )

                    ||

                    "{}"

                );


            return {

                name:
                    String(
                        raw.name ||
                        "Mi diseño"
                    ),

                image:
                    typeof raw.image ===
                    "string"
                        ?
                        raw.image
                        :
                        "",

                accent:
                    /^#[0-9a-f]{6}$/i.test(
                        raw.accent ||
                        ""
                    )
                        ?
                        raw.accent
                        :
                        "#61d8ff",

                background:
                    /^#[0-9a-f]{6}$/i.test(
                        raw.background ||
                        ""
                    )
                        ?
                        raw.background
                        :
                        "#02060a",

                panel:
                    /^#[0-9a-f]{6}$/i.test(
                        raw.panel ||
                        ""
                    )
                        ?
                        raw.panel
                        :
                        "#091016",

                text:
                    /^#[0-9a-f]{6}$/i.test(
                        raw.text ||
                        ""
                    )
                        ?
                        raw.text
                        :
                        "#f7fbff"

            };

        }
        catch(error){

            return {

                name:
                    "Mi diseño",

                image:
                    "",

                accent:
                    "#61d8ff",

                background:
                    "#02060a",

                panel:
                    "#091016",

                text:
                    "#f7fbff"

            };

        }

    }


    function applyCustomVariables(){

        const data =
            getCustomTheme();


        const root =
            document.documentElement;


        root.style.setProperty(

            "--huella-custom-accent",

            data.accent

        );


        root.style.setProperty(

            "--huella-custom-bg",

            data.background

        );


        root.style.setProperty(

            "--huella-custom-panel",

            data.panel

        );


        root.style.setProperty(

            "--huella-custom-text",

            data.text

        );


        if(
            data.image
        ){

            const safe =
                data.image.replace(
                    /"/g,
                    '\\"'
                );


            root.style.setProperty(

                "--huella-custom-image",

                `url("${safe}")`

            );

        }
        else{

            root.style.setProperty(

                "--huella-custom-image",

                "none"

            );

        }

    }


    /* =========================================================
       QUITAR CLASES VIEJAS
    ========================================================= */

    function clearThemeClasses(
        element
    ){

        if(
            !element ||
            !element.classList
        ){

            return;

        }


        Array.from(
            element.classList
        )
        .filter(

            item =>
                item.startsWith(
                    "huella-theme-"
                )

        )
        .forEach(

            item =>
                element.classList.remove(
                    item
                )

        );

    }


    /* =========================================================
       APLICAR TEMA
    ========================================================= */

    function applySettings(
        settings
    ){

        const config =
            normalize(
                settings
            );


        const root =
            document.documentElement;


        root.setAttribute(

            "data-huella-role",

            ROLE

        );


        root.setAttribute(

            "data-huella-theme",

            config.theme

        );


        root.setAttribute(

            "data-huella-motion",

            config.motion
                ?
                "on"
                :
                "off"

        );


        clearThemeClasses(
            root
        );


        root.classList.add(

            "huella-theme-" +
            config.theme

        );


        applyCustomVariables();


        function applyBody(){

            if(
                !document.body
            ){

                return;

            }


            clearThemeClasses(
                document.body
            );


            document.body.classList.add(

                "huella-theme-" +
                config.theme

            );


            document.body.setAttribute(

                "data-huella-theme",

                config.theme

            );


            document.body.setAttribute(

                "data-huella-role",

                ROLE

            );


            document.body.setAttribute(

                "data-huella-motion",

                config.motion
                    ?
                    "on"
                    :
                    "off"

            );

        }


        if(
            document.body
        ){

            applyBody();

        }
        else{

            document.addEventListener(

                "DOMContentLoaded",

                applyBody,

                {
                    once:true
                }

            );

        }

    }


    /* =========================================================
       CARGAR CSS FINAL AL ÚLTIMO

       Esto evita que el CSS propio de Expediente,
       Vacunas, GPS, Telemedicina, etc. tape el tema.
    ========================================================= */

    function loadFinalThemeCSS(){

        if(
            document.getElementById(
                "huellaFinalThemeCSS"
            )
        ){

            return;

        }


        let href =
            "";


        try{

            if(
                SCRIPT_SRC
            ){

                href =
                    new URL(

                        "dueno-theme-force.css?v=30",

                        SCRIPT_SRC

                    ).href;

            }

        }
        catch(error){}


        if(
            !href
        ){

            href =
                "/assets/dueno-theme-force.css?v=30";

        }


        const link =
            document.createElement(
                "link"
            );


        link.id =
            "huellaFinalThemeCSS";


        link.rel =
            "stylesheet";


        link.href =
            href;


        /*
            Se inserta DESPUÉS de que el HTML
            ya terminó de cargar.
        */

        document.head.appendChild(
            link
        );

    }


    /* =========================================================
       ESTADO ACTUAL
    ========================================================= */

    let settings =
        readSettings();


    applySettings(
        settings
    );


    if(
        document.readyState ===
        "loading"
    ){

        document.addEventListener(

            "DOMContentLoaded",

            function(){

                loadFinalThemeCSS();

                applySettings(
                    settings
                );

            },

            {
                once:true
            }

        );

    }
    else{

        loadFinalThemeCSS();

        applySettings(
            settings
        );

    }


    /* =========================================================
       EVENTO GLOBAL
    ========================================================= */

    function emitChange(){

        window.dispatchEvent(

            new CustomEvent(

                "huella:appearancechange",

                {

                    detail:{

                        ...settings,

                        role:
                            ROLE

                    }

                }

            )

        );

    }


    /* =========================================================
       CAMBIAR TEMA
    ========================================================= */

    function setTheme(
        theme
    ){

        settings = {

            ...settings,

            theme:
                THEMES.includes(
                    theme
                )
                    ?
                    theme
                    :
                    "normal"

        };


        settings =
            saveSettings(
                settings
            );


        applySettings(
            settings
        );


        loadFinalThemeCSS();


        requestAnimationFrame(

            function(){

                applySettings(
                    settings
                );

            }

        );


        setTimeout(

            function(){

                applySettings(
                    settings
                );

            },

            40

        );


        emitChange();


        return {
            ...settings
        };

    }


    /* =========================================================
       ANIMACIONES
    ========================================================= */

    function setMotion(
        enabled
    ){

        settings = {

            ...settings,

            motion:
                Boolean(
                    enabled
                )

        };


        settings =
            saveSettings(
                settings
            );


        applySettings(
            settings
        );


        emitChange();


        return {
            ...settings
        };

    }


    /* =========================================================
       PERSONALIZADO
    ========================================================= */

    function setCustomTheme(
        custom,
        applyNow = true
    ){

        const current =
            getCustomTheme();


        const merged = {

            ...current,

            ...custom

        };


        try{

            localStorage.setItem(

                CUSTOM_KEY,

                JSON.stringify(
                    merged
                )

            );

        }
        catch(error){

            console.error(
                error
            );

        }


        applyCustomVariables();


        if(
            applyNow
        ){

            setTheme(
                "personalizado"
            );

        }


        return merged;

    }


    /* =========================================================
       RESTABLECER
    ========================================================= */

    function reset(){

        settings = {
            ...DEFAULTS
        };


        settings =
            saveSettings(
                settings
            );


        applySettings(
            settings
        );


        emitChange();


        return {
            ...settings
        };

    }


    /* =========================================================
       SI CAMBIA EN OTRA PESTAÑA
    ========================================================= */

    window.addEventListener(

        "storage",

        function(event){

            if(
                event.key !==
                STORAGE_KEY
            ){

                return;

            }


            settings =
                readSettings();


            applySettings(
                settings
            );

        }

    );


    /* =========================================================
       API GLOBAL
    ========================================================= */

    window.HuellaAppearance = {

        role:
            ROLE,


        themes:
            [...THEMES],


        get(){

            return {
                ...settings
            };

        },


        setTheme:
            setTheme,


        setMotion:
            setMotion,


        getCustomTheme:
            getCustomTheme,


        setCustomTheme:
            setCustomTheme,


        reset:
            reset,


        apply(){

            applySettings(
                settings
            );

        }

    };


})();