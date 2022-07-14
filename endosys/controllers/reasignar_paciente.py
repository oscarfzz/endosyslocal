

import logging

from endosys.lib.base import *
from pylons import config
import datetime

from endosys.lib.checks import check_cache_dir
from endosys.lib.misc import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

import sqlalchemy as sa
import sqlalchemy.databases.mssql as mssql
import sqlalchemy.databases.oracle as oracle
import sqlalchemy.databases.mysql as mysql

log = logging.getLogger(__name__)


class ReasignarPacienteController(BaseController):

	@authorize(UserIn(['sysadmin']))
	def index(self):
		response.content_type = "text/html"
		s = '<html><head>'
##		s += '<script type="text/javascript" src="/lib/jquery/js/jquery-1.8.2.js"></script>'
		s += '<script data-main="/web/" type="text/javascript" src="/lib/jquery/require-jquery.js"></script>'



		s += '<title>Endosys App - Reasignación de pacientes</title>'
		s += '</head><body>'

		s += '<h1>Reasignación de pacientes</h1>'
		s += '<h2>Notas</h2>'
		s += '<p>'
		s += """
		El objetivo de esta utilidad es modificar el paciente de una exploración, además a lo largo del proceso se
		puede regenerar el el informe con el nuevo paciente y en el caso de que exista integración reenviar la
		mensajeria correspondiente
		<br>
		"""
		s += '</p>'
		s += '<div>'
		s += '<label>Numero exploración</label>'
		s +=  '<input id="numero_exploracion"></input>'
		s += '<button id="get_exploracion" type="button">--></button>'

		s += '</div>'

		s += '<div id="detalle_exploracion">'
		s += '</div>'
		s += '<div id="link_informes">'
		s += '</div>'
		s += '<div id="msg_link" style="color:red;">'
		s += '</div>'
		s += '<div id="check_options"">'
		s += '</div>'
		s += '<div id="input_new_patient">'
		s += '</div>'
		s += '<div id="detalle_paciente">'
		s += '</div>'
		s += '<div id="zona_boton_ejecutar">'
		s += '</div>'
		s += '<script>'
		s += """
			$(function() {

				$('#get_exploracion').click(function(e) {

					var num_expl = $("#numero_exploracion").val();

					$.ajax({
						type: 'GET',
						//url: '/reasignar_paciente/get_exploracion',
						url: '/rest/exploraciones',
						data: {'numero': num_expl},
						processData: true,
						//contentType: 'text/plain; charset=UTF-8',
						contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
						success: function(exploraciones) {
							if($(exploraciones).find("exploracion").length > 0){
								var detalle_exploracion = {};

								var exploracion = $(exploraciones).find("exploracion")[0];

								detalle_exploracion.id = $(exploracion).attr("id")
								detalle_exploracion.numero = $(exploracion).find("exploracion>numero").text();
								detalle_exploracion.fecha = $(exploracion).find("exploracion>fecha").text();
								detalle_exploracion.tipo_exploracion_desc = $(exploracion).find("exploracion>tipoExploracion>nombre").text();

								detalle_exploracion.paciente_id = $(exploracion).find("exploracion>paciente").attr("id")
								detalle_exploracion.paciente_nhc = $(exploracion).find("exploracion>paciente>historia").text();
								detalle_exploracion.paciente_cip= $(exploracion).find("exploracion>paciente>CIP").text();
								detalle_exploracion.paciente_nombre= $(exploracion).find("exploracion>paciente>nombre").text();
								detalle_exploracion.paciente_apellido1= $(exploracion).find("exploracion>paciente>apellido1").text();
								detalle_exploracion.paciente_apellido2= $(exploracion).find("exploracion>paciente>apellido2").text();

								detalle_exploracion.medico_nombre = $(exploracion).find("exploracion>medico>nombre").text();

								var html_detalle_exploracion ="<p>Número exploración = " + detalle_exploracion.numero +  "<br>" +
								"ID exploración = " + detalle_exploracion.id + "<br>" +
								"Fecha exploración = " + detalle_exploracion.fecha + "<br>" +
								"Tipo exploración = " + detalle_exploracion.tipo_exploracion_desc + "<br>" +
								"Paciente id = " + detalle_exploracion.paciente_id + "<br>" +
								"Paciente nhc = " + detalle_exploracion.paciente_nhc + "<br>" +
								"Paciente CIP = " + detalle_exploracion.paciente_cip + "<br>" +
								"Paciente Nombre = " + detalle_exploracion.paciente_nombre+" "+ detalle_exploracion.paciente_apellido1+" "+detalle_exploracion.paciente_apellido2 + "<br>" +
								"Medico username = " + detalle_exploracion.medico_nombre + "<br>" +
								"</p>"
								;

								$("#detalle_exploracion").data("detalle_exploracion",detalle_exploracion)
								$("#detalle_exploracion").html(html_detalle_exploracion)

								var html_new_patient = "<label>Paciente correcto</label>"+
								"<input id='numero_paciente_correcto'></input>"+
								"<button id='get_paciente_correcto' type='button'>--></button>";

								$("#input_new_patient").html(html_new_patient)

								$.ajax({
									type: 'GET',
									url: '/rest/informes',
									data: {'exploracion_id': detalle_exploracion.id},
									processData: true,
									contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
									success: function(informes) {
										var link = "";
										var data_link = [];
										for(var i= 0; i < $(informes).find("informe").length; i++){
											var informe =  $(informes).find("informe")[i];
											link =  link + "<a target='_blank' href='rest/informes/"+$(informe).attr("id")+".pdf'>rest/informes/"+$(informe).attr("id")+".pdf</a><br>";
											data_link.push($(informe).attr("id"));

										}

										link = link + "<br>"
										$("#link_informes").html(link);
										$("#link_informes").data("link_informes", data_link);
										var zona_check="";
										if($(informes).find("informe").length > 0){
											$("#msg_link").html("<p>Advertencia! la exploración contiene informes que es posible que tengan información erronea del paciente, en este caso, debe seleccionar la opción de invalidar informes, para inhabilitar estos informes</p>");
											zona_check = "<input type='checkbox' id='invalidar_informes' checked >Invalidar informes<br>"

										}
		 								zona_check = zona_check + "<input type='checkbox' id='generar_informe' checked >Generar nuevo informe<br>"+
													"Plantilla nuevo informe <select id ='plantilla_informe'></select><br><br>";
										$("#check_options").html(zona_check);

											$.ajax({
												type: 'GET',
												url: '/rest/plantillas',
												data: {'exploracion_id': detalle_exploracion.id},
												processData: true,
												contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
												success: function(plantillas) {
													var select_plantillas = $('#plantilla_informe');
													for(var i= 0; i < $(plantillas).find("plantilla").length; i++){
														var plantilla =  $(plantillas).find("plantilla")[i];
														var option = $('<option value='+$(plantilla).text()+'>'+$(plantilla).text()+'</option>');
														option.appendTo( select_plantillas );




													}
												},
												error: function(plantillas) {
													alert('No se han encontrado plantillas');
												}
											});

									},
									error: function(informes) {
										alert('No se han encontrado informes');
									}
								});

							}



						},
						error: function(exploraciones) {
							alert('Ha ocurrido un error al cargar la exploracion');
						}
					});

				});

				$( "#input_new_patient" ).on( "click", "#get_paciente_correcto", function() {
					var numero_historia = $("#numero_paciente_correcto").val();
						$.ajax({
							type: 'GET',
							url: '/rest/pacientes',
							data: {'historia': numero_historia},
							processData: true,
							//contentType: 'text/plain; charset=UTF-8',
							contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
							success: function(pacientes) {

								if($(pacientes).find("paciente").length > 0){
									var detalle_paciente = {};

									var paciente = $(pacientes).find("paciente")[0];

									detalle_paciente.id = $(paciente).attr("id")
									detalle_paciente.historia = $(paciente).find("paciente>historia").text();
									detalle_paciente.CIP = $(paciente).find("paciente>CIP").text();
									detalle_paciente.nombre = $(paciente).find("paciente>nombre").text();
									detalle_paciente.apellido1 = $(paciente).find("paciente>apellido1").text();
									detalle_paciente.apellido2 = $(paciente).find("paciente>apellido2").text();

									var html_detalle_paciente ="<p>ID paciente = " + detalle_paciente.id +  "<br>" +
										"historia = " + detalle_paciente.historia + "<br>" +
										"CIP paciente = " + detalle_paciente.CIP + "<br>" +
										"Nombre paciente = " + detalle_paciente.nombre+" "+ detalle_paciente.apellido1+" "+detalle_paciente.apellido2 + "<br>" +
										"</p>"
										;

									$("#detalle_paciente").data("detalle_paciente_correcto",detalle_paciente);
									$("#detalle_paciente").html(html_detalle_paciente);

									html_zona_boton = "<button id='ejecutar_reasginacion' type='button'>Reasignar paciente</button>";
									$("#zona_boton_ejecutar").html(html_zona_boton);
								}

							},
							error: function(pacientes) {
								alert('Ha ocurrido un error al cargar el paciente');
							}

						});
				});
				$( "#zona_boton_ejecutar" ).on( "click", "#ejecutar_reasginacion", function() {
					var detalle_exploracion = $("#detalle_exploracion").data("detalle_exploracion");
					var detalle_paciente_correcto = $("#detalle_paciente").data("detalle_paciente_correcto");
					var text_confirm = "Se dispone a moficar el paciente de la exploración número "+ detalle_exploracion.numero+",\\n"+
										"que tiene asingado el paciente con número de historia "+detalle_exploracion.paciente_nhc+",\\n"+
										"por el paciente correcto con numero de historia " +detalle_paciente_correcto.historia+"\\n";


					if ($("#invalidar_informes").is(':checked')){
						text_confirm = text_confirm + "- Recuerda que se van a invalidar los informes existentes que supuestamente corresponden al paciente erroneo\\n"
					}
					if ($("#generar_informe").is(':checked')){
						text_confirm = text_confirm + "- Recuerda que se va a generar un informe nuevo con los datos de paciente correcto\\n"
					}
					var repuesta=confirm(text_confirm);

					if (repuesta==true){
						$.ajax({
							type: 'POST',
							url: '/rest/exploraciones/'+detalle_exploracion.id,
							data: {'_method':'put', 'paciente_id': detalle_paciente_correcto.id},
							processData: true,
							//contentType: 'text/plain; charset=UTF-8',
							contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
							success: function(o) {
								if ($("#invalidar_informes").is(':checked')){
									var ids_informes = $("#link_informes").data("link_informes");
									for(var i = 0; i < ids_informes.length; i++){


										$.ajax({
											type: 'POST',
											url: '/rest/informes/'+ids_informes[i],
											data: {'_method':'put', 'invalido': 1},
											processData: true,
											//contentType: 'text/plain; charset=UTF-8',
											contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
											success: function(o) {
												alert("informe anulado");


											},
											error: function(o) {
												alert('Ha ocurrido un error al modificar el paciente');
											}
						  				});


									}
								}
								var plantilla = $('#plantilla_informe').find("option:selected").html();
								if ($("#generar_informe").is(':checked') && plantilla != ''){
									$.ajax({
											type: 'POST',
											url: '/rest/informes',
											data: {'exploracion_id': detalle_exploracion.id, 'plantilla': plantilla},
											processData: true,
											//contentType: 'text/plain; charset=UTF-8',
											contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
											success: function(o) {
												alert("informe GENERADO");


											},
											error: function(o) {
												alert('Ha ocurrido un error al generar el nuevo informe');
											}
					  				});

								}


							},
							error: function(o) {
								alert('Ha ocurrido un error al modificar el paciente');
							}
		  				});
					}
				});

			});
		"""
		s += '</script>'


		s += '</body></html>'
		return s

##	def get_exploracion(self):
##		numero_exploracion = request.params["num_expl"]
##		print "numero_exploracion" + numero_exploracion


