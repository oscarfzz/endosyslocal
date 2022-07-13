var dialogo_sala = function() {

	

	return {		
	

		crear_dialogo_sala: function(centro_id, sala_id, sala_nombre, pos_row) {

			var content_form_sala = $("<div id='content_form_sala'></div>");
			content_form_sala.load("content/dialog_sala.html"+ew_version_param(),function(data,textStatus) {
			    
				if(textStatus == "success"){
					content_form_sala.i18n();
				

					$('body').append(content_form_sala);
					//$('content_form_cita').html(data);
					
					var botones = [{
						text: _('Save'),/*IDIOMAOK*/
						click: function() {
							if (content_form_sala.find("#campo-nombre-sala").val() != ""){
								var params = {};
								params.nombre = content_form_sala.find("#campo-nombre-sala").val();
								params.centro_id = centro_id;
								if(!sala_id){
									//crear sala
									var creando_sala = Endotools.salas.create(TM.content_administracion, params);
									creando_sala.done(function(sala) {

										var pos_row =$('#tabla_salas').dataTable().fnAddData( [
											sala.id,
											content_form_sala.find("#campo-nombre-sala").val()  ] );

										var newrow = $($('#tabla_salas').dataTable().fnGetNodes(pos_row[0]));	
										newrow.click( function () {
											administracion.click_salas(centro_id, this) ;
											/*var data = $('#tabla_salas').dataTable().fnGetData( this );
											var aPos = $('#tabla_salas').dataTable().fnGetPosition( this );
											dialogo_sala.crear_dialogo_sala(centro_id, data[0], data[1], aPos);*/
										});
										
									});
								}else{
									//modificar nombre de la sala
									var modificando_sala = Endotools.salas.update(TM.content_administracion, sala_id, params);
									modificando_sala.done(function() {										
										$('#tabla_salas').dataTable().fnUpdate( params.nombre, pos_row, 1 );										
									});
									
								}
							
							}else{
								alert(_('El nombre de la sala no puede estar vacio'));/*IDIOMAOK*/
							}

							$( this ).dialog( "close" );
						}
					},
					{
						text: _('Cancel'),/*IDIOMAOK*/
						click: function() {
							$( this ).dialog( "close" );
						}
					}];

					if (sala_id){
						botones.push({
						text: _('Eliminar'),/*IDIOMAOK*/
						'class': "error-button",
						click: function() {
							if(sala_id) {
								var eliminar_dialog = confirm(_("¿Esta seguro que desea eliminar la Sala?"));
								if (eliminar_dialog) {
									var eliminando_sala = Endotools.salas['delete'](TM.content_administracion, sala_id);
									eliminando_sala.done(function() {
										$('#tabla_salas').dataTable().fnDeleteRow(pos_row);
									});
									$( this ).dialog( "close" );
								}

							}
						}
						});
					}

					/*
					if(sala_id) {
						botones.eliminar = function(){
							
							
							var eliminando_sala = Endotools.salas['delete'](TM.content_administracion, sala_id);
							eliminando_sala.done(function() {
								$('#tabla_salas').dataTable().fnDeleteRow(pos_row);
							});
							$( this ).dialog( "close" );
						}
					}
					*/
					
					$('#content_form_sala').dialog({ 
						modal: true,
						autoOpen: false,
						resizable: false,						
						title: _('Datos de la sala'),/*IDIOMAOK*/
						//show: 'clip', 
						//hide: 'clip',
						height: 'auto',
						width: 500,
						close: function() {
							$('#content_form_sala').dialog( "destroy" );
							$('#content_form_sala').remove();
						},
						buttons: botones
						
					});
					
					$('#content_form_sala').dialog( "open" );
					
					if (sala_id) {
						//MODIFICAR
						content_form_sala.find("#campo-nombre-sala").val(sala_nombre);
					
					}
					
				}else{
					alert('Error loading file nueva_cita.html');
				}
			
				
			});
			

		}



		
	}


}();	