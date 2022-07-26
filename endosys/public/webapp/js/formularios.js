//  XXX falta eliminar los ddproxys...

/*  clase GridAuto  */
//  NO SE UTILIZA, SE USA GRIDPOSITIONED

var GridAuto = function (width, $table) {
    this.array = [];
    this.width = width;

    this.x = 0;
    this.y = 0;
    this.$tbody = $('<tbody />');
    this.$tr = $('<tr/>');
    $table.append(
        this.$tbody.append(this.$tr)
    );
}

GridAuto.prototype = {
    addrow: function () {
        this.array.push(new Array(this.width));
    },

    check: function (x, y, width, height) {
        //  comprobar si esta libre
        for (var j = y; j < y + height; j++) {
            if (j == this.array.length) this.addrow();
            for (var i = x; i < x + width; i++) {
                if (i >= this.array[j].length) return false;
                if (this.array[j][i]) return false;
            }
        }
        return true;
    },

    mark: function (x, y, width, height) {
        //  marcar las celdas como ocupadas
        for (var j = y; j < y + height; j++) {
            if (j == this.array.length) this.addrow();
            for (var i = x; i < x + width; i++) {
                this.array[j][i] = true;
            }
        }
    },

    add: function (campo) {
        //  crear un nuevo td en la tabla para poner un nuevo campo
        //  lo pone al final de la tabla, si hay espacio en el mismo tr y si no creando un nuevo tr
        //  para usar con los campos ordenados por 'orden'

        //  devuelve $td

        //  comprobar si el campo cabe en el grid       
        while (!this.check(this.x, this.y, campo.ancho, campo.alto)) {
            //  poner una celda vacia en el espacio no ocupado, si no era por una superior con el rowspan...
            if (this.check(this.x, this.y, 1, 1)) {
                var $td = $('<td />').appendTo(this.$tr);
            }
            this.x++;
            if (this.x == this.width) {
                //  nueva fila
                this.x = 0;
                this.y++;
                this.$tr = $('<tr/>').appendTo(this.$tbody);
            }
        }
        this.mark(this.x, this.y, campo.ancho, campo.alto);

        //  crear la celda
        var $td = $('<td />').appendTo(this.$tr);
        if (campo.ancho > 1) $td.attr('colspan', campo.ancho);
        if (campo.alto > 1) $td.attr('rowspan', campo.alto);
        $td.attr('width', 100 * campo.ancho / this.width + '%');
        return $td;
    }
}

/* Clase GridPositioned */
var GridPositioned = function (width, $table, editable) {
    this.array = [];
    this.trows = [];    //  cada elemento es un object conteniendo una referencia el elemento tr y un array con los tds {tr: null, tds: []}
    this.width = width;
    this.$tbody = $('<tbody />').appendTo($table);
    this.editable = editable;

    //  por defecto que tenga 8 filas si es para edicion
    if (this.editable) {
        for (var i = 0; i < 8; i++) this.addrow();
        this.createTableElements();
    }

    //  si es nuevo modo, hacer los TD mas pequeños
    if (this.MODO_CAMPOS == 2) {
        $table.addClass('modo_campos_2');
    }
}

GridPositioned.prototype = {

    MODO_CAMPOS: 2, //  0 y 1: como hasta ahora.    2: nuevo modo, con labels a la izquierda.

    addrow: function () {
        this.array.push(new Array(this.width));
    },

    check: function (x, y, width, height) {
        //  comprobar si esta libre
        for (var j = y; j < y + height; j++) {
            while (this.array.length <= j) this.addrow();
            for (var i = x; i < x + width; i++) {
                if (i >= this.array[j].length) return false;
                if (this.array[j][i]) return false;
            }
        }
        return true;
    },

    mark: function (x, y, width, height) {
        //  marcar las celdas como ocupadas
        for (var j = y; j < y + height; j++) {
            while (this.array.length <= j) this.addrow();
            for (var i = x; i < x + width; i++) {
                this.array[j][i] = true;
            }
        }
    },

    unmark: function (x, y, width, height) {
        //  marcar las celdas como no ocupadas
        for (var j = y; j < y + height; j++) {
            while (this.array.length <= j) this.addrow();
            for (var i = x; i < x + width; i++) {
                this.array[j][i] = false;
            }
        }
    },

    createTableElements: function (height) {
        //  crear los trs necesarios, inicializandolos con todos los tds posibles
        //  si se indica height, se crearan los indicados, si no solo los definidos en el array de libres/ocupados
        if (!height) height = this.array.length;
        for (var n = 0; n < height; n++) {  //  se crea siempre una fila adicional para la edicion
            if (!(this.trows[n])) this.trows[n] = { $tr: null, $tds: [] };
            if (!(this.trows[n].$tr)) {
                this.trows[n].$tr = $('<tr/>').appendTo(this.$tbody);
                for (var a = 0; a < this.width; a++) {
                    var $td = $('<td />').addClass('campo-drag-drop').appendTo(this.trows[n].$tr);
                    if (this.editable) {
                        //  si es editable, hacer que los nuevos tds generados sean droptargets
                        $td.droppable({
                            accept: ".campo-drag-drop",
                            tolerance: "pointer",
                            //activeClass: "ui-state-hover",
                            //hoverClass: "ui-state-active",
                            drop: function (event, ui) {
                                /*
                                    this    el TD en el que se está soltando
                                    ui      info de lo que se está arrastrando
                                */
                                var campo = ui.draggable.data('campo');
                                var formdata = ui.draggable.data('formdata');
                                var grupoCampos = formdata.get_grupoCampos_by_td($(this));
                                if (!grupoCampos) return;

                                //  retrasar la ejecución porque se vuelve a crear todo el Table,
                                //  y se elimina el TD que se está ejecutando su evento, y da errores de jqueryui...
                                var that = this;
                                setTimeout(function () {
                                    var grid = formdata.generado.gruposCampos[grupoCampos.id].grid;
                                    var pos = grid.getTdPosition($(that));
                                    if (pos) {
                                        //  comprobar si cabe en el grid
                                        if (grid.canMove(campo, pos.x, pos.y)) {
                                            campo.posx = pos.x;
                                            campo.posy = pos.y;
                                            formdata.addCampo(grupoCampos, campo);
                                            formdata.generar_grupoCampos(grupoCampos);
                                        }
                                    } else {
                                        //  si se ha dejado en algun sitio que no es del grid (p.e. la tabla de campos), quitarlo
                                        formdata.quitarCampo(campo.id);
                                        formdata.generar_grupoCampos(grupoCampos);
                                        if (formdata.onQuitarCampo) formdata.onQuitarCampo(campo);
                                    }
                                }, 0);
                            }
                        });
                    }
                    this.trows[n].$tds.push($td);
                }
            }
        }
    },

    add: function (campo) {
        //  crear un nuevo td en la tabla para poner un nuevo campo
        //  lo añade en una posicion concreta de la tabla, redimensionandola si es necesario
        //  si ya hay celdas ocupadas, fallara
        //  para usar con la informacion de los campos 'posx' y 'posy'

        //  devuelve $td

        if (this.check(campo.posx, campo.posy, campo.ancho, campo.alto)) {
            this.createTableElements(campo.posy + campo.alto + 1);

            //  buscar el td correspondiente
            var $td = this.trows[campo.posy].$tds[campo.posx];

            //  procesar el ancho y el alto del campo
            if (campo.ancho > 1) $td.attr('colspan', campo.ancho);
            if (campo.alto > 1) $td.attr('rowspan', campo.alto);

            //  eliminar los tds que sobran por debajo y por la derecha
            for (var y = campo.posy; (y < this.trows.length) && (y <= campo.posy + campo.alto - 1); y++) {
                for (var x = campo.posx; (x < this.width) && (x <= campo.posx + campo.ancho - 1); x++) {
                    if ((x == campo.posx) && (y == campo.posy)) continue;
                    if (this.trows[y].$tds[x]) {
                        this.trows[y].$tds[x].remove();
                        this.trows[y].$tds[x] = null;
                    }
                }
            }

            $td.attr('width', 100 * campo.ancho / this.width + '%');
            this.mark(campo.posx, campo.posy, campo.ancho, campo.alto);
            return $td;
        } else {
            return null;
        }
    },

    getTdPosition: function ($td) {
        //  obtiene la posicion {x: n, y: n} del td indicado, o null si no existe
        //  a partir del td (el elemento jQuery o el id)
        if (typeof $td == 'string') $td = $('#' + $td);
        if (!$td) return null;
        for (var y = 0; y < this.trows.length; y++) {
            for (var x = 0; x < this.width; x++) {
                if ($td.is(this.trows[y].$tds[x])) {
                    return { 'x': x, 'y': y };
                }
            }
        }
        return null;
    },

    canMove: function (campo, x, y) {
        //  comprueba si se puede mover el campo a la posicion indicada
        //      deshabilitar las celdas ocupadas por el campo temporalmente

        //      (si campo.posx == -1 y campo.posy == -1) es que no estaba añadido,
        //      por lo tanto no hace falta deshabilitar celdas temporalmente
        if ((campo.posx == -1) && (campo.posy == -1)) {
            return this.check(x, y, campo.ancho, campo.alto);
        }

        this.unmark(campo.posx, campo.posy, campo.ancho, campo.alto);
        try {
            //      hacer la comprobación
            return this.check(x, y, campo.ancho, campo.alto);
        } finally {
            //      volverlas a habilitar       
            this.mark(campo.posx, campo.posy, campo.ancho, campo.alto);
        }
    },

    canResize: function (campo, width, height) {
        //  comprueba si se puede cambiar el tamaño del campo al indicado
        //      deshabilitar las celdas ocupadas por el campo temporalmente

        this.unmark(campo.posx, campo.posy, campo.ancho, campo.alto);
        try {
            //      hacer la comprobación
            return this.check(campo.posx, campo.posy, width, height);
        } finally {
            //      volverlas a habilitar       
            this.mark(campo.posx, campo.posy, campo.ancho, campo.alto);
        }
    },


    /////////////////////////////////////////
    //  el HIGHLIGHT se refiere a marcar una celda (td) para que quede como seleccionada,
    //  y se puedan ejecutar acciones como añadir o quitar filas...

    _is_highlighted: function (x, y) {
        return this.trows[y].$tds[x].hasClass('highlighted');
    },

    _highlight: function (x, y) {
        this.trows[y].$tds[x].addClass('highlighted');
    },

    _unhighlight: function (x, y) {
        this.trows[y].$tds[x].removeClass('highlighted');
    },

    _unhighlight_all: function () {
        for (var y = 0; y < this.trows.length; y++) {
            if (!this.trows[y]) continue;
            for (var x = 0; x < this.trows[y].$tds.length; x++) {
                if (!this.trows[y].$tds[x]) continue;
                this.trows[y].$tds[x].removeClass('highlighted');
            }
        }
    },

    _toggle_highlight: function (x, y) {
        this.trows[y].$tds[x].toggleClass('highlighted');
    }

    /////////////////////////////////////////
}


/* Clase ETFormData
Antes se llamaba FormData, pero parece que ya hay una clase llamada
asi de alguna libreria relacionada con jquery (la usa jquery.fileupload)
*/

var _formdatas = [];    //  guardar referencias a todos los formdatas creados

function clearAllFormDatas() {
    for (var i = 0; i < _formdatas.length; i++) {
        _formdatas[i].clearGrids();
    }
    _formdatas = [];
}

var ETFormData = function (data) {
    //  si "data" tiene getElementsByTagName(), se supone que es xml.
    //  Si no, se entiende que es un objeto, json.
    this.exploracion = null;
    this.gruposCampos = {};
    this.onGenerarGrupoCampos = null;
    this.onQuitarCampo = null;
    this.highlighted = {
        grupoCampos_id: null,
        x: null,
        y: null
    }

    if (data.getElementsByTagName) {
        //  es XML
        this.id = data.getElementsByTagName('formulario')[0].getAttribute('id');
        this.titulo = data.getElementsByTagName('titulo')[0].firstChild.data;
        var gruposCampos = data.getElementsByTagName('grupoCampos');

        for (var i = 0; i < gruposCampos.length; i++) {
            var grupoCampos = {
                id: gruposCampos[i].getAttribute('id'),
                orden: Number(gruposCampos[i].getElementsByTagName('orden')[0].firstChild.data),
                titulo: gruposCampos[i].getElementsByTagName('titulo')[0].firstChild.data,
                columnas: Number(gruposCampos[i].getElementsByTagName('columnas')[0].firstChild.data),
                campos: {}
            };
            this.gruposCampos[grupoCampos.id] = grupoCampos;
            var campos = gruposCampos[i].getElementsByTagName('campos')[0].childNodes;
            for (var j = 0; j < campos.length; j++) {
                var campo = {
                    id: Number(campos[j].getAttribute('id')),
                    nombre: campos[j].tagName,
                    tipo: xmlu.element_text(campos[j].getElementsByTagName('tipo')[0]),
                    titulo: xmlu.element_text(campos[j].getElementsByTagName('titulo')[0]),
                    ancho: Number(xmlu.element_text(campos[j].getElementsByTagName('ancho')[0])),
                    alto: Number(xmlu.element_text(campos[j].getElementsByTagName('alto')[0])),
                    orden: Number(xmlu.element_text(campos[j].getElementsByTagName('orden')[0])),
                    posx: Number(xmlu.element_text(campos[j].getElementsByTagName('posx')[0])),
                    posy: Number(xmlu.element_text(campos[j].getElementsByTagName('posy')[0])),
                    solo_lectura: parseEndosysBool(xmlu.element_text(campos[j].getElementsByTagName('solo_lectura')[0])),
                    obligatorio: parseEndosysBool(xmlu.element_text(campos[j].getElementsByTagName('obligatorio')[0])),
                    tipo_control: xmlu.element_text(campos[j].getElementsByTagName('tipo_control')[0]),
                    ambito: xmlu.element_text(campos[j].getElementsByTagName('ambito')[0]),
                    script: xmlu.element_text(campos[j].getElementsByTagName('script')[0]),
                    campo_rel_id: xmlu.element_text(campos[j].getElementsByTagName('campo_rel_id')[0]),
                    valor: null
                }
                campo.valor = this.valorCampo_from_xml(campo, campos[j].getElementsByTagName('valor')[0]);
                grupoCampos.campos[campo.id] = campo;
            }
        }
    } else {
        //  es un objeto (json)
        this.id = data.id;
        this.titulo = data.titulo;
        var gruposCampos = data.gruposCampos;

        for (var i = 0; i < gruposCampos.length; i++) {
            var grupoCampos = {
                id: gruposCampos[i].id,
                orden: Number(gruposCampos[i].orden),
                titulo: gruposCampos[i].titulo,
                columnas: Number(gruposCampos[i].columnas),
                campos: {}
            };
            this.gruposCampos[grupoCampos.id] = grupoCampos;
            var campos = gruposCampos[i].campos;
            for (var key in campos) {
                var campo = {
                    id: Number(campos[key].id),
                    nombre: key,
                    tipo: campos[key].tipo,
                    titulo: campos[key].titulo,
                    ancho: Number(campos[key].ancho),
                    alto: Number(campos[key].alto),
                    orden: Number(campos[key].orden),
                    posx: Number(campos[key].posx),
                    posy: Number(campos[key].posy),
                    solo_lectura: parseEndosysBool(campos[key].solo_lectura),
                    obligatorio: parseEndosysBool(campos[key].obligatorio),
                    tipo_control: campos[key].tipo_control,
                    ambito: campos[key].ambito,
                    script: campos[key].script,
                    campo_rel_id: campos[key].campo_rel_id,
                    valor: null
                }
                campo.valor = this.valorCampo_from_json(campo, campos[key].valor);
                grupoCampos.campos[campo.id] = campo;
            }
        }
    }

    this.generado = {
        editable: null,
        $contenedor: null,
        $tabs: null,
        $accordion: null,
        gruposCampos: {},   //  array, siendo la clave el id del grupocampos. Cada elemento es un object: {contenedor, grid}
        controles: []
    }

    _formdatas.push(this);
}


//  se usa desde ET_exploraciones.js (que es donde estaba antes) y desde formularios.js
//  solo identifica TIPO_TEXTO, TIPO_MEMO, TIPO_MULTI y TIPO_BOOL
function esControlTipo($control, tipo) {
    if (!$control) return false;
    if (tipo == Endosys.campos.TIPO_TEXTO) {
        return $control.hasClass('campo-tipo-texto');
        /*if (!($control._node)) return false;
        if ($control._node.nodeName.toUpperCase() != 'INPUT') return false; //  funciona en todos
        if ($control._node.type.toUpperCase() != 'TEXT') return false;
        if ($control._node.type != 'text') return false;
        return true; */
    } else if (tipo == Endosys.campos.TIPO_MEMO) {
        return $control.hasClass('campo-tipo-memo');
        /*if (!($control._node)) return false;
        if ($control._node.nodeName.toUpperCase() != 'TEXTAREA') return false;  //  funciona en todos
        return true;*/
    } else if (tipo == Endosys.campos.TIPO_MULTI) {
        return $control.hasClass('campo-tipo-multi');
        /*if (!($control._node)) return false;
        if ($control._node.nodeName.toUpperCase() != 'SELECT') return false;    //  funciona en todos
        return true;*/
    } else if (tipo == Endosys.campos.TIPO_BOOL) {
        return $control.is('input') && ($control.attr('type') == 'checkbox');
    }
    return false;
}


ETFormData.prototype = {

    get_control_by_td: function ($td) {
        //  obtiene la info del control generado (el elemento en el array 'this.generado.controles'
        //  a partir del td (el elemento jquery o el id)
        if (typeof $td == 'string') $td = $('#' + $td);
        for (var i in this.generado.controles) {
            if ($td.is(this.generado.controles[i].$td)) {
                return this.generado.controles[i];
            }
        }
        return null;
    },

    get_grupoCampos_by_td: function ($td) {
        if (typeof $td == 'string') $td = $('#' + $td);
        //  recorrer los grupocampos generados
        for (var grupoCampos_id in this.generado.gruposCampos) {
            if (this.generado.gruposCampos[grupoCampos_id].grid.getTdPosition($td)) {
                return this.gruposCampos[grupoCampos_id];
            }
        }
        return null;
    },

    get_gruposCampos_ordenados: function () {
        //  devuelve un array con los gruposcampos ordenados por el 'orden'
        var gruposcampos_ordenados = [];
        for (var grupoCampos_id in this.gruposCampos) {
            var ok = false;
            for (var n = 0; n < gruposcampos_ordenados.length; n++) {
                if (this.gruposCampos[grupoCampos_id].orden < gruposcampos_ordenados[n].orden) {
                    gruposcampos_ordenados.splice(n, 0, this.gruposCampos[grupoCampos_id]);
                    ok = true;
                    break;
                }
            }
            if (!ok) {
                gruposcampos_ordenados.push(this.gruposCampos[grupoCampos_id]);
            }
        }
        return gruposcampos_ordenados;
    },

    valorCampo_from_xml: function (campo, valor_el) {
        //  obtiene el valor de un campo a partir del xml, segun el tipo de campo
        var valor;
        if (valor_el) {
            if ((campo.tipo == Endosys.campos.TIPO_TEXTO) || (campo.tipo == Endosys.campos.TIPO_MEMO)) {
                valor = xmlu.element_text(valor_el, '');
            } else if (campo.tipo == Endosys.campos.TIPO_BOOL) {
                valor = xmlu.element_text(valor_el, '');
                valor = (valor == 'sí') || (valor == 'si') || (valor == '1');
            } else if (campo.tipo == Endosys.campos.TIPO_SELECCION) {
                //  guardar en objeto: {id: X, nombre: Y}
                var elemento = valor_el.getElementsByTagName('elemento');
                if (elemento.length > 0) {
                    valor = {
                        id: Number(elemento[0].getAttribute('id')),
                        nombre: xmlu.element_text(elemento[0].getElementsByTagName('nombre')[0], '')
                    }
                } else {
                    valor = { id: null, nombre: '' }
                }
            } else if (campo.tipo == Endosys.campos.TIPO_MULTI) {
                var elementos = valor_el.getElementsByTagName('elemento');
                valor = [];
                for (var k = 0; k < elementos.length; k++) {
                    valor.push({
                        id: Number(elementos[k].getAttribute('id')),
                        nombre: xmlu.element_text(elementos[k].getElementsByTagName('nombre')[0], '')
                    });
                }
            }
        } else {
            if ((campo.tipo == Endosys.campos.TIPO_TEXTO) || (campo.tipo == Endosys.campos.TIPO_MEMO)) {
                valor = '';
            } else if (campo.tipo == Endosys.campos.TIPO_BOOL) {
                valor = false;
            } else if (campo.tipo == Endosys.campos.TIPO_SELECCION) {
                valor = { id: null, nombre: '' }
            } else if (campo.tipo == Endosys.campos.TIPO_MULTI) {
                valor = [];
            }
        }
        return valor;
    },

    valorCampo_from_json: function (campo, valor_obj) {
        //  obtiene el valor de un campo a partir del json, segun el tipo de campo
        var valor;
        if (valor_obj) {
            if ((campo.tipo == Endosys.campos.TIPO_TEXTO) || (campo.tipo == Endosys.campos.TIPO_MEMO)) {
                valor = valor_obj;
            } else if (campo.tipo == Endosys.campos.TIPO_BOOL) {
                valor = valor_obj;
                valor = (valor == 'sí') || (valor == 'si') || (valor == '1');
            } else if (campo.tipo == Endosys.campos.TIPO_SELECCION) {
                //  guardar en objeto: {id: X, nombre: Y}
                if (valor_obj.elemento) {
                    valor = {
                        id: Number(valor_obj.elemento.id),
                        nombre: valor_obj.elemento.nombre,
                        codigo: valor_obj.elemento.codigo
                    }
                } else {
                    valor = { id: null, nombre: '', codigo: '' }
                }
            } else if (campo.tipo == Endosys.campos.TIPO_MULTI) {
                var elementos = valor_obj;
                valor = [];
                for (var k = 0; k < elementos.length; k++) {
                    valor.push({
                        id: Number(elementos[k].id),
                        nombre: elementos[k].nombre,
                        cantidad: elementos[k].cantidad,
                        codigo: elementos[k].codigo
                    });
                }
            }
        } else {
            if ((campo.tipo == Endosys.campos.TIPO_TEXTO) || (campo.tipo == Endosys.campos.TIPO_MEMO)) {
                valor = '';
            } else if (campo.tipo == Endosys.campos.TIPO_BOOL) {
                valor = false;
            } else if (campo.tipo == Endosys.campos.TIPO_SELECCION) {
                valor = { id: null, nombre: '', codigo: '' }
            } else if (campo.tipo == Endosys.campos.TIPO_MULTI) {
                valor = [];
            }
        }
        return valor;
    },

    clearGrids: function () {
        var grupoCampos;
        for (var grupoCampos_id in this.gruposCampos) {
            grupoCampos = this.generado.gruposCampos[grupoCampos_id];
        }
    },

    generar_completo: function ($contenedor, editable) {
        //  '$contenedor' ha de ser un elemento jquery, o null
        //  'editable' indica si se permetirá editar los campos por drag'n drop
        //  genera todo el formulario completo, incluso el tabview o accordion si tiene mas de un grupo de campos
        this.generado.editable = editable;
        if ($contenedor) this.generado.$contenedor = $contenedor;
        $contenedor = this.generado.$contenedor;

        //  vaciar el contenedor
        $contenedor.html('');

        //  destruir los DDs de cualquier grid que pueda haber en gruposCampos
        this.clearGrids();
        this.generado.gruposCampos = {};

        //  si hay mas de 1 grupo de campos, crear tabs (o accordion)
        var totalGruposCampos = 0;
        for (var bla in this.gruposCampos) { totalGruposCampos++; }
        if ((totalGruposCampos > 1) || editable) {
            if (opciones_config.GRUPOS_CAMPOS_USAR_TABS) {
                //  crear tabview 
                this.generado.$tabs = $('<div><ul /></div>').appendTo($contenedor).tabs();
            } else {
                //  se creara al final el accordion, de momento crear el <ul> y un <li> por cada grupo de campos.
                //  (no es un accordion de jQueryui, se simula, para poder tener mas de un apartado abierto a la vez)
                this.generado.$accordion = $('<div id="accordion-formulario-' + this.id + '"/>')
                    .addClass('ui-accordion ui-widget ui-helper-reset')
                    .appendTo($contenedor);
            }
        }

        //  ordenar los gruposcampos por el orden
        var gruposcampos_ordenados = this.get_gruposCampos_ordenados();

        //  recorrer los 'grupoCampos'
        for (var n = 0; n < gruposcampos_ordenados.length; n++) {
            this.generar_grupoCampos(gruposcampos_ordenados[n].id, { crearContenedores: true });
        }

        //  crear accordion
        if (this.generado.$accordion) {
            //  simular "accordion", pero que pueda tener todas las secciones abiertas
            //  inspirado en http://stackoverflow.com/questions/12843418/jquery-ui-accordion-expand-collapse-all ,
            //              http://jsfiddle.net/sinetheta/s5hAw/
            this.generado.$accordion.find('.accordion-header')

                .click(function () {
                    var panel = $(this).next();
                    var isOpen = panel.is(':visible');
                    // open or close as necessary
                    panel[isOpen ? 'slideUp' : 'slideDown']();

                    var iconspan = $(this).find('span.ui-accordion-header-icon');
                    if (iconspan) {
                        if (isOpen) {
                            iconspan.removeClass('ui-icon-triangle-1-s').addClass('ui-icon-triangle-1-e');
                        } else {
                            iconspan.removeClass('ui-icon-triangle-1-e').addClass('ui-icon-triangle-1-s');
                        }
                    }

                    // stop the link from causing a pagescroll
                    return false;
                })

                .hover(function () {
                    $(this).addClass('ui-state-hover');
                },
                    function () {
                        $(this).removeClass('ui-state-hover');
                    });

        }

        //  Aplicar clases a los inputs
        //  XXX sería mejor hacerlo al crear cada input...
        $contenedor.find('.campo-tipo-texto').addClass('pure-input-1');
        $contenedor.find('.campo-tipo-memo').addClass('pure-input-1');
        $contenedor.find('.campo-tipo-multi').addClass('pure-input-1');
        $contenedor.find('.campo-tipo-selec').addClass('width-100');
        $contenedor.find('.endosys-autocomplete').addClass('pure-input-1');
    },

    generar_grupoCampos: function (grupoCampos, o) {
        //  'grupoCampos' puede ser directamente el objeto del grupoCampos o el index (id)
        //  genera todo el contenido de un grupo de campos, incluido el tab o el div de un accordion si el form tiene mas de un grupo de campos
        //  'o' es la configuracion. Puede ser:
        //      'crearContenedores'     si se crearan los tabs o los divs del accordion si es necesario (true|false|'auto' , por defecto 'auto')
        if (!(typeof grupoCampos == 'object'))
            grupoCampos = this.gruposCampos[grupoCampos];
        o = o || {};
        if (!('crearContenedores' in o)) o.crearContenedores = 'auto';

        //
        if (!this.generado.gruposCampos[grupoCampos.id])
            this.generado.gruposCampos[grupoCampos.id] = { id: grupoCampos.id, $contenedor: null, grid: null };

        //  generar tab o el div de un accordion si tiene tabview o accordion
        var $content;
        var existe_contenedor = this.generado.gruposCampos[grupoCampos.id].$contenedor;
        if (((o.crearContenedores == 'auto') && (!existe_contenedor)) || (o.crearContenedores == true)) {
            if (this.generado.$tabs) {
                var id = "tabs-formulario-" + this.id + "-" + grupoCampos.id;
                this.generado.$tabs
                    .tabs("add", id, grupoCampos.titulo)
                    .tabs("refresh")
                    .tabs("option", "active", 0);// OK para jQueryUI >= 1.10
                $content = $('#' + id);
            } else if (this.generado.$accordion) {
                var $title = $('<h3/>')
                    .html('<span class="ui-accordion-header-icon ui-icon ui-icon-triangle-1-s"></span>' + grupoCampos.titulo)
                    .addClass('accordion-header ui-accordion-header ui-helper-reset ui-state-default ui-accordion-icons ui-corner-all')
                    .appendTo(this.generado.$accordion);

                //  botones para quitar el grupocampos y reordenarlo
                if (this.generado.editable) {
                    var formdata = this;

                    //  quitar
                    $('<span />')
                        .addClass('ui-icon ui-icon-close')
                        .css('float', 'right').appendTo($title)
                        .click(function () {
                            formdata.quitarGrupoCampos(grupoCampos.id);
                            formdata.generar_completo(null, true);
                        });

                    //  mover arriba
                    $('<span />')
                        .addClass('ui-icon ui-icon-arrowthick-1-n')
                        .css('float', 'right').appendTo($title)
                        .click(function () {
                            formdata.subirGrupoCampos(grupoCampos.id);
                            formdata.generar_completo(null, true);
                        });

                    //  mover abajo
                    $('<span />')
                        .addClass('ui-icon ui-icon-arrowthick-1-s')
                        .css('float', 'right').appendTo($title)
                        .click(function () {
                            formdata.bajarGrupoCampos(grupoCampos.id);
                            formdata.generar_completo(null, true);
                        });
                }

                $content = $('<div/>')
                    .text(grupoCampos.titulo)
                    .addClass('ui-accordion-content ui-helper-reset ui-widget-content ui-corner-bottom')
                    .appendTo(this.generado.$accordion);
            } else {
                $content = this.generado.$contenedor;
            }
            this.generado.gruposCampos[grupoCampos.id].$contenedor = $content;
        } else {
            $content = this.generado.gruposCampos[grupoCampos.id].$contenedor;
        }
        //  vaciar el content
        $content.html('');

        //  crear una tabla (de html) para poner los campos
        var $table = $('<table style="width: 100%;" />');
        if (this.generado.editable) $table.addClass('editable-table');
        $content.append($table);

        this.generado.gruposCampos[grupoCampos.id].grid = new GridPositioned(grupoCampos.columnas, $table, this.generado.editable);

        //  recorrer los campos del grupo y crear las celdas de la tabla
        for (var campo_id in grupoCampos.campos) {
            this.procesar_campo(grupoCampos, grupoCampos.campos[campo_id]);
        }

        //  XXX HIGHLIGHT. HACERLO EN TODA LA FILA? las operaciones son insertar y quitar filas...
        if (this.generado.editable) {
            var formdata = this;
            var grid = this.generado.gruposCampos[grupoCampos.id].grid;
            //  asignar eventos click a los TDs para el highlight
            for (var y = 0; y < grid.trows.length; y++) {
                if (!grid.trows[y]) continue;
                for (var x = 0; x < grid.trows[y].$tds.length; x++) {
                    if (!grid.trows[y].$tds[x]) continue;

                    grid.trows[y].$tds[x].click(function () {
                        var pos = grid.getTdPosition($(this));
                        //  solo permite que una celda, o ninguna, esté en HIGHLIGHT
                        //  en todos los grids/gruposcampos
                        var highlighted = grid._is_highlighted(pos.x, pos.y);
                        for (var grupoCampos_id in formdata.generado.gruposCampos) {
                            formdata.generado.gruposCampos[grupoCampos_id].grid._unhighlight_all();
                        }
                        formdata.highlighted.grupoCampos_id = null;
                        formdata.highlighted.y = null;
                        if (!highlighted) {
                            grid._highlight(pos.x, pos.y);
                            formdata.highlighted.grupoCampos_id = grupoCampos.id;
                            formdata.highlighted.x = pos.x;
                            formdata.highlighted.y = pos.y;
                        }
                    });

                }
            }
        }
        ////////////////////////////

        if (this.onGenerarGrupoCampos) this.onGenerarGrupoCampos(grupoCampos);
    },

    get_valores_controles: function (fn) {
        /*
        obtiene los valores asignados a cada control.
          fn    por cada control se ejecuta la función "fn":
                fn(control_obj, valor)
                  control_obj   es un objeto con estos campos:
                                  campo_id
                                  control       referencia al control del formulario
                                  $td           la celda TD donde está el control
                                  campo         objeto con info completa del campo
                  valor         el valor del campo que se ha extraido del control
                  
        Esta función se llama desde campo_change() y desde exploraciones.js:guardar_exploracion()
        */
        $(this.generado.controles).each(function (index, obj) {
            var $control = obj.$control;
            //  extraer el valor segun el tipo de campo
            var valor = '';
            //      TIPO SEPARADOR
            if ($control == null) {
                //  no hay control, es un separador/titulo. No se añade el valor de este campo (porque no puede tener)
                return;
                //      TIPO TEXTO
            } else if (esControlTipo($control, Endosys.campos.TIPO_TEXTO)) {
                //  el valor esta en el atributo value del control, que es un HTMLElement (mas concretamente un HTMLInputElement)
                valor = $control.val();

                //      TIPO SELECCION
            } else if ($control.hasClass('campo-tipo-selec')) {
                //  el valor esta en el atributo value del elemento button
                valor = $control.val();
                //  tipo select con autocomplete    
            } else if ($control.hasClass('endosys-autocomplete')) {

                valor = $control.val();

                //      TIPO BOOL
            } else if (esControlTipo($control, Endosys.campos.TIPO_BOOL)) {
                //  el valor esta en el atributo value del elemento button
                valor = $control.prop('checked') ? 1 : 0;
                //      TIPO MEMO
            } else if (esControlTipo($control, Endosys.campos.TIPO_MEMO)) {
                valor = $control.val();
                //      TIPO MULTI
            } else if (esControlTipo($control, Endosys.campos.TIPO_MULTI)) {
                //  todos los ids de los elementos seleccionados separados por comas
                valor = '';
                $control.find('option').each(function (index, el) {
                    if (parseInt($(el).attr("data-tipo-control"), 10) == 2) {
                        valor += $(el).val() + ':' + $(el).attr("data-cantidad") + ',';
                    } else {
                        valor += $(el).val() + ',';
                    }
                });
                if (valor != '') valor = valor.substr(0, valor.length - 1);   //  quitar la ultima coma (si la hay)
            }

            fn(obj, valor);
        });
    },

    campo_change: function () {
        //  se ejecuta cuando cambia el valor de un campo.
        //  se utiliza para actualizar el valor de los campos calculados.

        //  si no esta habilitada la opcion de campos calculados, salir
        if (opciones_config.CAMPOS_CALCULADOS == '0') return;

        //  recoger los valores de todos los campos, para pasarlos luego a la funcion de calculado
        var valores_campos = {};
        this.get_valores_controles(function (control_obj, valor) {
            valores_campos[control_obj.campo.nombre] = valor;
        });

        //  recoger tambien los valores de los campos de la exploracion, ya que puede interesar
        //  por ejemplo la edad del paciente
        valores_campos['exploracion_numero'] = this.exploracion.numero;
        valores_campos['exploracion_fecha'] = this.exploracion.fecha;
        valores_campos['exploracion_medico'] = this.exploracion.medico;
        valores_campos['exploracion_tipo_exploracion'] = this.exploracion.tipoexploracion;
        valores_campos['exploracion_edad_paciente'] = this.exploracion.edad_paciente;



        $(this.generado.controles).each(function (index, control) {

            if (control.campo.script) {
                //  "script" tiene que ser el cuerpo de una función que tiene que retornar
                //  el valor calculado para el campo. Recibe como parámetro "campos" un object
                //  con el valor de todos los campos: {campo1: valor, campo2: valor...}
                if (control.campo.tipo == Endosys.campos.TIPO_TEXTO) {
                    control.$control.val(
                        (new Function('campos', control.campo.script))(valores_campos)
                    );
                } else if (control.campo.tipo == Endosys.campos.TIPO_SELECCION) {
                    //  si es tipo seleccion, de momento solo está implementado con los select nativo, no autocomplete
                    if (control.campo.tipo_control == "1") {
                        //...
                    } else {
                        control.$control.val((new Function('campos', control.campo.script))(valores_campos));

                    }
                }
            }

        });
        //fin prov
    },

    procesar_campo: function (grupoCampos, campo) {
        /*  genera el control segun el tipo de campo.
            'campo' es el objeto del campo.
            Al control creado se le asigna un id con este formato: #campo-form-FORM_ID-CAMPO_ID
        */
        var formdata = this;
        var control_ID = 'form-' + formdata.id + '-campo-' + campo.id;

        var grid = this.generado.gruposCampos[grupoCampos.id].grid;
        var $td = grid.add(campo);
        if (!$td) return;

        //  Crear el label y el control segun el tipo de campo
        //  **************************************************

        //  Crear el label. Si es editable, poder hacer drag'n drop, cambiar tamaño, etc...
        var $label;
        if (!this.generado.editable) {
            // Formulario de la exploracion
            // No es editable: crear el label y ya esta
            $label = $('<label><span>' + campo.titulo + '</span></label>').addClass('titulo-campo').appendTo($td);
            $label.click(function () { return false; });
        } else {
            //formulario en editor de formulario
            //  Es editable:
            //      que se pueda drag'n drop el label
            $td.data({
                'campo': campo,
                'formdata': this
            });
            $td.draggable({ opacity: 0.5, helper: "clone" });

            var $yg = $('<div class="yui3-g" style="padding-right: 75px;"></div>').appendTo($td);
            var $yu1 = $('<div class="yui3-u" style="width: 100%;"></div>').appendTo($yg);
            var $yu2 = $('<div class="yui3-u" style="margin-right: -75px; width: 75px; text-align: right;"></div>').appendTo($yg);
            var $info = $('<small>' + campo.nombre + ' / ' + campo.id + '</small>');

            $label = $('<label>' + campo.titulo + '</label>').addClass('titulo-campo').appendTo($yu1);
            $info.appendTo($label);

            //      Botones para cambiar el tamaño del campo
            var incheight_btn, incwidth_btn, decheight_btn, decwidth_btn;
            editcampo_btn = $('<button type="button" class="campo-edit-dialog" ><i class="fa fa-pencil"></i></button>').appendTo($yu2);
            decwidth_btn = $('<button type="button" class="campo-dec-width-btn"><i class="fa fa-caret-left"></i></button>').appendTo($yu2);
            incwidth_btn = $('<button type="button" class="campo-inc-width-btn"><i class="fa fa-caret-right"></i></button>').appendTo($yu2);
            decheight_btn = $('<button type="button" class="campo-dec-height-btn"><i class="fa fa-caret-up"></i></button>').appendTo($yu2);
            incheight_btn = $('<button type="button" class="campo-inc-height-btn"><i class="fa fa-caret-down"></i></button>').appendTo($yu2);

            var resizefunc = function (w, h) {
                if ((w == 0) || (h == 0)) return;
                var grid = formdata.generado.gruposCampos[grupoCampos.id].grid;
                if (grid.canResize(campo, w, h)) {
                    campo.ancho = w;
                    campo.alto = h;
                    formdata.generar_grupoCampos(grupoCampos);
                }
            }
            editcampo_btn.on('click', function () { editor_formularios.editar_campo(campo.id, undefined) });
            incwidth_btn.on('click', function () { resizefunc(campo.ancho + 1, campo.alto) });
            decwidth_btn.on('click', function () { resizefunc(campo.ancho - 1, campo.alto) });
            incheight_btn.on('click', function () { resizefunc(campo.ancho, campo.alto + 1) });
            decheight_btn.on('click', function () { resizefunc(campo.ancho, campo.alto - 1) });
        }
        if (campo.obligatorio) {
            $label.html($label.html() + " (*) ");
        }

        //  Crear el control de cada tipo de campo
        var $control;

        //  si es modo 2, envolver el contenido del td (el label y el control) en un div para poder colocar correctamente
        var controlwrapper = $td;
        if (grid.MODO_CAMPOS == 2) {
            controlwrapper = $(('<div class="modo_campos_2-wrapper" />')).appendTo($td);
        }

        // Tipo Texto
        if (campo.tipo == Endosys.campos.TIPO_TEXTO) {
            $control = $('<input type="text"/>')
                .addClass('campo-tipo-texto')
                .attr('id', control_ID)
                .val(campo.valor)
                .appendTo(controlwrapper);
            $control.change(function () { formdata.campo_change() });
            if (campo.solo_lectura) {
                $control.attr('readonly', 'readonly');//.css('background-color', '#E4FFF0');
            }

            // Tipo Seleccion
        } else if (campo.tipo == Endosys.campos.TIPO_SELECCION) {
            // Cuando el tipo_control == 1 entonces es autocomplete.
            // Si es null es un select comun.

            if (campo.tipo_control == "1") {
                // es un autocomplete
                $control = $('<input id=' + control_ID + '>');

                function highlightText(text, $node) {
                    //condición para que no lleguen cadenas vacias al subrayado del AUTOCOMPLETE, la cadena vacia hace que funcione mal
                    if ($.trim(text).length > 0) {

                        var searchText = $.trim(text).toLowerCase(), currentNode = $node.get(0).firstChild, matchIndex, newTextNode, newSpanNode;
                        while ((matchIndex = currentNode.data.toLowerCase().indexOf(searchText)) >= 0) {
                            newTextNode = currentNode.splitText(matchIndex);
                            currentNode = newTextNode.splitText(searchText.length);
                            newSpanNode = document.createElement("span");
                            newSpanNode.className = "highlight";
                            currentNode.parentNode.insertBefore(newSpanNode, currentNode);
                            newSpanNode.appendChild(newTextNode);
                        }
                    }
                }

                $control.autocomplete({
                    source: function (request, response) {

                        var params = { 'activo': 1, 'campo_id': campo.id, 'nombre': request.term };

                        // Si el campo es de ámbito "por servicio", entonces cargar solo los
                        // elementos del servicio activo.
                        if (campo.ambito == "1") {
                            params.servicio_id = Endosys.auth.servicio_activo.id;
                        }

                        Endosys.elementos.index(TM.content_exploraciones.detalles.elementoscampos, params)
                            .done(function (elementos) {

                                var listado_elementos = [];
                                for (var n = 0; n < elementos.length; n++) {
                                    var elemento = elementos[n];
                                    var label = elemento.nombre;
                                    if (elemento.codigo) label = elemento.codigo + ' - ' + label;
                                    listado_elementos.push({
                                        label: label,
                                        value: elemento.nombre,
                                        id: elemento.id
                                    });
                                }

                                return response(listado_elementos);
                            });

                    },
                    create: function (event, ui) {
                        // valor con el codigo si existe
                        var valor = campo.valor.nombre;
                        if (campo.valor.codigo) {
                            valor = campo.valor.codigo + ' - ' + valor;
                        } 
                        $control.val(valor);
                    },
                    minLength: 2
                })
                    .addClass('endosys-autocomplete')
                    .appendTo(controlwrapper)
                    .data("ui-autocomplete")._renderItem = function (ul, item) {
                        var $a = $("<a></a>").text(item.label);
                        highlightText(this.term, $a);
                        return $("<li></li>").append($a).appendTo(ul);
                    };

            } else {
                //  Control Select comun
                $control = $('<select></select>');
                $control.data('valor_anterior', null).addClass('campo-tipo-selec').attr('id', control_ID).attr('name', control_ID).appendTo(controlwrapper);

                // Agrega todos los campos.
                if (!this.generado.editable) {
                    // Crea el option del valor que viene por el rest
                    if (campo.valor.id != null) {

                        // valor con el codigo si existe
                        var valor = campo.valor.nombre;
                        if (campo.valor.codigo) {
                            valor = campo.valor.codigo + ' - ' + valor;
                        } 

                        // Se agrega a mano el valor guardado,
                        // siempre entrará al if este
                        var el_str = "option[value='" + campo.valor.id + "']";
                        var option_selected = $control.children(el_str);
                        if (option_selected.length == 0) {
                            $('<option />').html(valor).val(campo.valor.id).appendTo($control);
                        }
                        $control.children('option[value="' + campo.valor.id + '"]').prop("selected", true);
                    }

                    this._elementos_campo(TM.content_exploraciones.detalles.elementoscampos, campo, $control);  //  cargar los elementos de forma asincrona //  XXX el trans. manager configurable?
                }
            }
        } else if (campo.tipo == Endosys.campos.TIPO_MULTI) {
            // Campo multiseleccion
            // Crear boton al lado del label para modificar elementos
            var $target_control = null;
            var $boton_edit = $('<button type="button" class="boton-aux-campo button-small"><svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" role="img" width="1em" height="1em" preserveAspectRatio="xMidYMid meet" viewBox="0 0 1024 1024"><path fill="currentColor" d="M840.4 300H183.6c-19.7 0-30.7 20.8-18.5 35l328.4 380.8c9.4 10.9 27.5 10.9 37 0L858.9 335c12.2-14.2 1.2-35-18.5-35z"/></svg></button>');
            $label.append($boton_edit);
            $boton_edit.button({ icons: { primary: "ui-icon-triangle-1-se" }, text: false });
            if (!this.generado.editable) {
                $boton_edit.click(function () {
                    //  mostrar pantalla                                                
                    input_tipo_multi.mostrar(campo.titulo, formdata.id + '_' + campo.id, $target_control, formdata, campo.tipo_control);
                });
            }

            // Crear el control
            // #777: el data-tipo-control se envia para ser usado cuando hay campos relacionados.
            //       Cuando se agrega un item desde el campo memo con predefinidos es necesario saber
            //       que tipo de control es, y por eso se agrega este atributo.
            $control = $('<select size="6" data-tipo-control="' + campo.tipo_control + '" class="campo-tipo-multi" id="' + control_ID + '"/>').appendTo(controlwrapper);

            for (var k in campo.valor) {
                // contempla el caso de que el elemento este incluido en 
                // la lista de seleccionados pero tenga NULL en su cantidad. En este caso le asigna 1
                // para que se muestre correctamente y se grabe luego bien
                if (campo.valor[k].cantidad == "") {
                    campo.valor[k].cantidad = 1;
                }

                if (campo.valor[k].codigo != ""){
                    campo.valor[k].nombre = campo.valor[k].codigo + " - " + campo.valor[k].nombre; 
                }

                option_el = input_tipo_multi.generar_option(campo.valor[k], campo.tipo_control);
                $control.append(option_el);
            }

            if (!this.generado.editable) {
                $control.on("dblclick", function () {
                    //  mostrar pantalla tambien con el dblclick sobre el control
                    input_tipo_multi.mostrar(campo.titulo, formdata.id + '_' + campo.id, $target_control, formdata, campo.tipo_control);
                });
            }

            $target_control = $control;
        } else if (campo.tipo == Endosys.campos.TIPO_BOOL) {
            // Campo tipo booleano
            var the_control = $('<input type="checkbox">')
                .attr('id', control_ID)
                .prop('checked', campo.valor)
                .appendTo(controlwrapper);

            $('<label style="font-size: 10px;" class="btn-hidden">No text</label>')
                .attr('for', control_ID)
                .appendTo(controlwrapper);

            the_control
                .button({ icons: { primary: campo.valor ? 'ui-icon-check' : 'ui-icon-empty' }, text: false })
                .change(function () {
                    //  actualizar icono según estado
                    if (the_control.prop('checked')) {
                        the_control.button('option', 'icons', { primary: 'ui-icon-check' });
                    } else {
                        the_control.button('option', 'icons', { primary: 'ui-icon-empty' });
                    }
                    // Para campos calculados
                    formdata.campo_change();
                });
            $control = the_control;

            if (campo.solo_lectura) {
                //  XXX falta
            }
        } else if (campo.tipo == Endosys.campos.TIPO_MEMO) {
            // Campo del tipo Memo
            // Crear el control
            // $control = $('<textarea rows="6" class="campo-tipo-memo" id="' + campo.nombre + '">' + campo.valor + '</textarea>').appendTo(controlwrapper);
            $control = $('<textarea rows="6" class="campo-tipo-memo" id="' + control_ID + '">' + campo.valor + '</textarea>').appendTo(controlwrapper);
            var $target_memo = $control;
            if (campo.solo_lectura) {
                $control.attr('readonly', 'readonly');
                $control.attr('style', 'background-color: #E4FFF0');
            }
            $control.change(function () { formdata.campo_change() });

            //  Crear boton al lado del label para añadir texto predef.
            //  Cargar los textos predef. del campo
            if (!this.generado.editable) {
                // 2.4.9: aqui se crea el objeto campo_ext para enviarselo a menu_textos_predefinidos. Antes
                //        se enviaba solamente el campo_id pero con la funcionalidad de la peticion #445 se necesitaban
                //        datos como el formulario id y el campo relacionado
                var campo_ext = { 'formulario_id': formdata.id };
                $.extend(true, campo_ext, campo);

                // 2.4.10: antes se agregaba en el .done de mas abajo, ahora se agrega antes y luego se habilita si tiene datos
                //         esto sirve para que exista el boton cuando se deshabilitan los controles en caso de que la exploracion
                //         este eliminada.
                menu_textos_predefinidos.crear(campo_ext, $label, $target_memo.attr('id'));
            }

            //  SEPARADOR
        } else if (campo.tipo == Endosys.campos.TIPO_SEPARADOR) {
            $label.addClass('titulo-separador');
            $td.css('vertical-align', 'middle');
            $control = null;
        }

        // Guardar una referencia al control para poder guardar los cambios
        this.generado.controles.push({ 'campo_id': campo.id, '$control': $control, '$td': $td, 'campo': campo });
    },

    addCampo: function (grupoCampos, campo) {
        //  para modo edicion, añade un campo al formulario
        //  campo -> info del campo a añadir:
        //              id, nombre, tipo, titulo, columnas, orden, posx, posy, solo_lectura
        //  si el campo ya estaba no hace nada (un campo solo puede estar 1 vez en un formulario, aun en distintos grupos de campos)
        if (!(typeof grupoCampos == 'object'))
            grupoCampos = this.gruposCampos[grupoCampos];

        //  comprobar si existe en algun grupoCampos (incluido en el que se quiere añadir).
        //  Si es asi, no hacer nada.
        for (var grupoCampos_id in this.gruposCampos) {
            if (campo.id in this.gruposCampos[grupoCampos_id].campos) return false;
        }

        //  añadirlo
        grupoCampos.campos[campo.id] = campo;
        return true;
    },

    quitarCampo: function (campo_id) {
        //  para modo edicion, quita un campo del formulario
        //  si el campo ya no estaba no hace nada

        //  comprobar si existe en algun grupoCampos, si no, no hacer nada.
        for (var grupoCampos_id in this.gruposCampos) {
            if (campo_id in this.gruposCampos[grupoCampos_id].campos) {
                //  quitarlo
                delete this.gruposCampos[grupoCampos_id].campos[campo_id];
                return true;
            }
        }

        return false;
    },

    addGrupoCampos: function (grupocampos) {
        //  para modo edicion, añade un grupo de campos al formulario
        //  grupocampos -> info del grupocampos a añadir:
        //              id, titulo, columnas
        //  si el grupocampos ya estaba no hace nada (un grupocampos solo puede estar 1 vez en un formulario)

        //  si ya existe no hacer nada
        if (grupocampos.id in this.gruposCampos) return false;

        //  añadirlo
        var totalGruposCampos = 0;
        for (var bla in this.gruposCampos) { totalGruposCampos++; }
        this.gruposCampos[grupocampos.id] = {
            id: grupocampos.id,
            orden: totalGruposCampos + 1,
            titulo: grupocampos.titulo,
            columnas: Number(grupocampos.columnas),
            campos: {}
        };

        return true;
    },

    renombrarGrupoCampos: function (grupocampos) {
        //  se llama cuando se renombra un grupo de campos.
        //  se comprueba si existe, y en ese caso se actualiza con el nuevo titulo.
        if (grupocampos.id in this.gruposCampos) {
            this.gruposCampos[grupocampos.id].titulo = grupocampos.titulo;
        }
    },

    quitarGrupoCampos: function (grupocampos_id) {
        //  para modo edicion, quita un grupocampos del formulario
        //  si el grupocampos ya no estaba no hace nada

        //  comprobar si existe en algun grupoCampos, si no, no hacer nada.
        if (grupocampos_id in this.gruposCampos) {
            delete this.gruposCampos[grupocampos_id];
            return true;
        }

        return false;
    },

    subirGrupoCampos: function (grupocampos_id) {
        //  para modo edicion, mueve un grupocampos hacia arriba (cambia el orden por el anterior)
        //  ordenar los gruposcampos, buscar el indicado y cambiarlo por el anterior
        var gruposcampos_ordenados = this.get_gruposCampos_ordenados();
        for (var n = 0; n < gruposcampos_ordenados.length; n++) {
            if (gruposcampos_ordenados[n].id == grupocampos_id) {
                if (n > 0) {
                    var temp = gruposcampos_ordenados[n - 1].orden;
                    gruposcampos_ordenados[n - 1].orden = gruposcampos_ordenados[n].orden;
                    gruposcampos_ordenados[n].orden = temp;
                }
            }
        }
    },

    bajarGrupoCampos: function (grupocampos_id) {
        //  para modo edicion, mueve un grupocampos hacia abajo (cambia el orden por el siguiente)
        //  ordenar los gruposcampos, buscar el indicado y cambiarlo por el siguiente
        var gruposcampos_ordenados = this.get_gruposCampos_ordenados();
        for (var n = 0; n < gruposcampos_ordenados.length; n++) {
            if (gruposcampos_ordenados[n].id == grupocampos_id) {
                if (n < (gruposcampos_ordenados.length - 1)) {
                    var temp = gruposcampos_ordenados[n + 1].orden;
                    gruposcampos_ordenados[n + 1].orden = gruposcampos_ordenados[n].orden;
                    gruposcampos_ordenados[n].orden = temp;
                }
            }
        }
    },

    insertar_fila: function () {
        //  inserta una fila vacia en la posicion highlight     
        if ((this.highlighted.grupoCampos_id == null) || (this.highlighted.y == null)) return;

        var grid = this.generado.gruposCampos[this.highlighted.grupoCampos_id].grid;
        var posy = this.highlighted.y;

        //  añade una fila en el array del grid y recrea los TDs que falten
        grid.addrow();
        grid.createTableElements();

        //  recorrer todas las celdas de abajo a arriba e ir bajando los controles
        for (var y = grid.trows.length - 1; y >= posy; y--) {
            for (var x = 0; x < grid.trows[y].$tds.length; x++) {
                if (grid.trows[y].$tds[x]) {
                    var obj_control = this.get_control_by_td(grid.trows[y].$tds[x]);
                    if (obj_control) {
                        obj_control.campo.posy++;
                    }
                }
            }
        }
        this.generar_grupoCampos(this.highlighted.grupoCampos_id);
    },

    quitar_fila: function (grupoCampos_id) {
        //  quita la fila de la posicion highlight (si habia campos también se quitan),
        //  subiendo una posición los campos de debajo
        if ((this.highlighted.grupoCampos_id == null) || (this.highlighted.y == null)) return;

        var grid = this.generado.gruposCampos[this.highlighted.grupoCampos_id].grid;
        var posy = this.highlighted.y;

        //  comprobar que esta fila esté libre
        if (!grid.check(0, posy, grid.width, 1)) return;

        //  recorrer todas las celdas de arriba a abajo e ir subiendo los controles
        for (var y = posy; y < grid.trows.length; y++) {
            for (var x = 0; x < grid.trows[y].$tds.length; x++) {
                if (grid.trows[y].$tds[x]) {
                    var obj_control = this.get_control_by_td(grid.trows[y].$tds[x]);
                    if (obj_control) {
                        obj_control.campo.posy--;
                    }
                }
            }
        }
        this.generar_grupoCampos(this.highlighted.grupoCampos_id);
    },

    /*  PRIVATE */
    _onNuevoValorItemClick2: function (_fd_campo, _fd_id, _fd_ctl, formdata) {
        nuevo_elemento.mostrar_camposelec2(_fd_campo.titulo, _fd_id, _fd_ctl, formdata);
    },

    _elementos_campo: function (tm, campo, $control) {
        // esta funcion devuelve una promise para que desde afuera se pueda
        // saber como termino
        var deferred = $.Deferred();

        //  obtener el listado de elementos de un campo, y poner los dos por defecto
        //  ademas añade el evento change()
        //  y cuando ha cargado el listado, selecciona el campo.valor XXX
        var formdata = this;
        var parent = $control.parent();

        // Limpia la lista y saca el evento asociado change
        $control.empty();
        $control.off("change");
        $control.off("keypress");
        $control.off("mousedown");

        this.crear_btn_actualizar_elementos(formdata, $control, campo);

        // Crea el elemento de tipo vacio que estara oculto
        $('<option />')
            .addClass('selectboxit-especial-item')
            .attr('data-tipo', 'accion')
            .attr("style", "display:none;")
            .html('')/*IDIOMAOK*/
            .val(null)
            .appendTo($control);

        //Crea el elemento "Sin Valor" Si se selecciona este,
        // entonces se seleccionará el elemento vacio
        $('<option/>')
            .addClass('selectboxit-especial-item')
            .attr('data-tipo', 'accion')
            .html(_('Sin valor'))/*IDIOMAOK*/
            .val("_SIN_VALOR_")
            .appendTo($control);

        // Elemento "Nuevo valor". Cuando se selecciona este elemento
        // se abre un dialogo de creación de elementos.
        $('<option/>')
            .addClass('selectboxit-especial-item')
            .attr('data-tipo', 'accion')
            .html(_('Nuevo valor...'))/*IDIOMAOK*/
            .val('_NUEVO_VALOR_')
            .appendTo($control);

        if (!$control.attr("data-recarga")) {
            $control.attr("data-recarga", "0");
        }

        // Crea el elemento que viene como dato de la exploración.
        // Esto tambien hace hace en el procesar_campo cuando se carga por 
        // primera vez pero cuando se hace recarga es necesario que este 
        // aqui tambien
        if (campo.valor.id != null) {
            // Se agrega a mano el valor guardado
            var option_selected = $control.children("option[value='" + campo.valor.id + "']");
            if (option_selected.length == 0) {

                var valor = campo.valor.nombre;
                if (campo.valor.codigo) {
                    valor = campo.valor.codigo + ' - ' + valor;
                } 

                $('<option />')
                    .html(valor)
                    .val(campo.valor.id)
                    .appendTo($control);
            }
            $control.children('option[value="' + campo.valor.id + '"]')
                .prop("selected", true);
        }

        var error = false;

        // Carga de elementos desde el REST
        var params = { 'activo': 1, 'campo_id': campo.id };

        // Si el campo es de ámbito "por servicio", entonces cargar solo los
        // elementos del servicio activo.
        if (campo.ambito == "1") {
            params.servicio_id = Endosys.auth.servicio_activo.id;
        }

        Endosys.elementos.index(tm, params).done(function (elementos) {
            var ocultar = true;

            // Recorre los elementos y los agrega al control
            for (var n = 0; n < elementos.length; n++) {
                if (campo.valor.id != null &&
                    campo.valor.id == elementos[n].id) {

                    // si esta activo no lo oculto ya que si no entra aqui,
                    // es que esta oculto en la tabla "elementos"
                    if (elementos[n].activo) {
                        ocultar = false;
                    }
                } else {
                    // No viene como dato de la exploracion,
                    // Lo agrego sin comprobar. Aqui solo llegan los activos
                    var elemento = elementos[n];
                    var label = elemento.nombre;
                    if (elemento.codigo) label = elemento.codigo + " - " + label;
                    $('<option />').attr('data-tipo', 'elemento').text(label).val(elemento.id).appendTo($control);
                }
            }

            if (ocultar) {
                // oculto el campo que viene desde el valor del formulario
                var el_filter = "option[value='" + campo.valor.id + "']";
                var option_selected = $control.children(el_filter);
                option_selected.attr("style", "display:none;");
            }

        }).fail(function (response) {
            error = true;
        }).always(function () {
            // configura el evento change para realizar acciones segun el elemento que se seleccione
            $control.on("change", function () {
                var valor_anterior = $control.data('valor_anterior');

                if ($control.val() == '_NUEVO_VALOR_') {
                    //  es el elemento 'nuevo valor', mostrar el dialog de nuevo elemento
                    //      impedir el cambio de valor, reseteandolo
                    //$control.selectBoxIt('selectOption', String(valor_anterior));
                    nuevo_elemento.mostrar_camposelec(campo.titulo, formdata.id + '_' + campo.id, $control, formdata);
                    //seleccionar el valor anterior asi no queda seleccionado el item nuevo_valor
                    if (valor_anterior == null) {
                        $control.children('option[value=""]').prop('selected', true);
                    } else {
                        $control.children('option[value="' + valor_anterior + '"]').prop('selected', true);
                    }
                    return;
                } else if ($control.val() == "_SIN_VALOR_") {
                    $control.children('option[value=""]').prop('selected', true);
                    //  es el elemento 'sin valor', asi que dejarlo sin valor
                } else {
                    //  es un elemento
                }
                if (valor_anterior != $control.val()) formdata.campo_change();
                $control.data('valor_anterior', $control.val());
            });

            $control.on("keypress", function (e) {
                formdata.evento_recarga($(this), campo, e);
            });

            $control.on("mousedown", function (e) {
                formdata.evento_recarga($(this), campo, e);
            });

            if (error) {
                deferred.resolve();
            } else {
                deferred.reject();
            }

        });

        return deferred.promise();
    },

    evento_recarga: function ($control, campo, e) {
        // si no tiene elementos y no se ha recargado nunca entonces
        // intenta recargar la información pq es problable que haya 
        // fallado la peticion
        var load_complete = false;
        var cant_elem = $control.children('[data-tipo="elemento"]').length;
        var parent = $control.parent();
        if ($control.attr("data-recarga") == "0" && cant_elem == 0) {
            parent.find(".actualizar-elementos").trigger("click");
            $control.attr("data-recarga", "1");
            e.preventDefault();
        }
    },

    crear_btn_actualizar_elementos: function (formdata, $control, campo) {

        var parent = $control.parent();

        if (parent.find(".actualizar-elementos").length == 0) {
            $('<button class="actualizar-elementos">' + '<i class="fa fa-refresh"></i></button>')
                .button()
                .attr("alt", _("Recargar elementos de este campo"))
                .on("click", function () {
                    var btn_this = $(this);
                    btn_this.prop("disabled", true);
                    parent.find(".info-act-elementos").show()
                        .html('<i class="fa fa-spinner fa-spin"></i>' +
                            _("Actualizando elementos"));//IDIOMAOK

                    formdata._elementos_campo(
                        TM.content_exploraciones.detalles.elementoscampos,
                        campo,
                        $control
                    ).always(function () {
                        btn_this.prop("disabled", false);
                        parent.find(".info-act-elementos").html('<i class="fa fa-check"></i>' + _("Elementos actualizados")).delay(1800).fadeOut(200);  //IDIOMAOK
                    });
                }).appendTo($control.prev().children());

            $('<span class="info-act-elementos"></span>').appendTo($control.prev().children());
        }
    }
}

//////////////////////////////
var formularios = function () {
    return {
        generar_formulario: function (data, formulario, editable, exploracion) {
            //  "data" puede ser un xml (p.e. de response.responseXML) o json
            //  xxx
            clearAllFormDatas();
            var formdata = new ETFormData(data);
            formdata.exploracion = exploracion; //  "exploracion" solo se usa para los campos calculados, en campo_change()
            formdata.generar_completo(formulario.$contenedor, editable);
            formulario.controles = formdata.generado.controles;
            formulario.formdata = formdata; //  en principio, solo para acceder a get_valores_controles()
            return formdata;
        },

        get_control_by_nombrecampo: function (formulario, nombrecampo) {
            /*  Obtiene un control de un formulario por el nombre.
                No distingue mays/mins.
                Si no lo encuentra devuelve null
            */
            for (var i = 0; i < formulario.controles.length; i++) {
                var control = formulario.controles[i];
                //if (window.console) window.console.log(control);
                //  "control" tiene las propiedades:
                //      campo_id:   id del campo
                //      control:    el Element (select, textarea, etc...)
                //      td:         el Element TD de la tabla donde está el control
                //      campo:      un objeto con info del campo (solo lectura!): id, nombre, tipo, titulo, ancho, alto, orden, posx, posy, solo_lectura, tipo_control y valor              
                if (control && (control.campo.nombre.toUpperCase() == nombrecampo.toUpperCase())) {
                    return control;
                }
            }

            return null;
        }

    }

}();