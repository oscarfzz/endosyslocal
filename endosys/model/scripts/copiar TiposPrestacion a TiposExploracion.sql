-- convierte los TiposPrestacion en tiposExploracion con un Formulario.

--	VACIAR TABLAS
delete from rel_campos_formularios
delete from rel_Formularios_TiposExploracion
delete from formularios
delete from tiposexploracion

--	COPIAR
insert into tiposexploracion select _codigo, nombre, color, activo from tiposprestacion
insert into formularios select nombre as titulo from tiposprestacion

insert into rel_Formularios_TiposExploracion
	select tiposexploracion.id as tipoexploracion_id, formularios.id as formulario_id, 0
	from tiposexploracion, formularios
	where tiposexploracion.nombre = formularios.titulo

insert into rel_campos_formularios
	select formularios.id as formulario_id, campo_id, grupocampos_id, orden
	from rel_campos_tiposprestacion, tiposprestacion, formularios
	where rel_campos_tiposprestacion.tipoprestacion_id = tiposprestacion.id
		and tiposprestacion.nombre = formularios.titulo