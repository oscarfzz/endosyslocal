"""
Utilidades de acceso por dicom, mediante dcm4che.

Notas:
	- el nombre correcto de un registro del worklist podría ser "worklist item"
	  o "task"... "work" tampoco está mal.

"""
import logging
import sys
import os
from time import strptime
from datetime import date, time, datetime
from endotools.lib.dicom.util import *
try:
    import Image
except ImportError:
    from PIL import Image
import jpype
from pylons import config

log = logging.getLogger(__name__)

def inicializar():
	jvmPath = jpype.getDefaultJVMPath()

	# Ruta base de la instalación de dcm4che-2.0.27
	#   XXX por defecto la busca a la altura de portablepython, etc...
	#		debería ser configurable... en el INI?
	s = os.path.split( config['pylons.paths']['root_parent'] )[0]
	dcm4che_path = os.path.join(s, 'dcm4che-2.0.27')

	# estas son las clases de java utilizadas por la herramienta dcmmwl
	classpath = ';'.join((
    	os.path.join(dcm4che_path, 'etc'),
    	os.path.join(dcm4che_path, 'lib', 'dcm4che-tool-dcmmwl-2.0.27.jar'),
    	os.path.join(dcm4che_path, 'lib', 'dcm4che-core-2.0.27.jar'),
    	os.path.join(dcm4che_path, 'lib', 'dcm4che-net-2.0.27.jar'),
    	os.path.join(dcm4che_path, 'lib', 'slf4j-log4j12-1.6.1.jar'),
    	os.path.join(dcm4che_path, 'lib', 'slf4j-api-1.6.1.jar'),
    	os.path.join(dcm4che_path, 'lib', 'log4j-1.2.16.jar'),
    	os.path.join(dcm4che_path, 'lib', 'commons-cli-1.2.jar'),
	))
	jpype.startJVM(jvmPath,'-Djava.class.path=%s' % classpath)


def finalizar():
	# XXX   cuando se ejecuta? es necesario? se queda si no una JVM en memoria corriendo...?
	#   doc. de JPYPE: For the most part, this method does nto have to be called. It will
	#	be automatically executed when the jpype module is unloaded at python's exit.
	jpype.shutdownJVM()


class WLWork_dcm4che(WLWork):
	"""
	Son los objetos devueltos por obtenerWorkList().
	"""

	def __init__(self, dicomObject):
		"""
		dicomObject		son los objetos de Java devueltos por dcm4che al obtener
						el worklist (org.dcm4che2.data.DicomObject)
		"""
		WLWork.__init__(self)

		# inicializar a partir de un dicomObject
		if dicomObject:
			#   XXX revisar mejor como funciona dicomObject.getString()... :
			#		dicomObject.get(0x00100010)	//	devuelve un org.dcm4che2.data.DicomElement
			#		dicomObject.getString(0x00100010)	//	devuelve un string

			Tag = jpype.JPackage('org').dcm4che2.data.Tag
			JInteger = jpype.java.lang.Integer
			JArrayInt = jpype.JArray(JInteger)

            #	nombre y apellidos
			self.patientName = dicomObject.getString(Tag.PatientName, '') or None
			# segun formato del H. de santiago -> "apellido1 apellido2^nombre"
			# aunque en los apellidos puede haber varios espacios, claro...
			# XXX procesar correctamente
##			s = patientName.split('^')
##			c.paciente.nombre = s[1]
##			c.paciente.apellido1 = s[0]
##			c.paciente.apellido2 = ''
			#   NHC
			self.patientID = dicomObject.getString(Tag.PatientID, '') or None
			#   Fecha de nacimiento
			self.patientBirthDate = dicomObject.getString(Tag.PatientBirthDate, '') or None
			#   Sexo
			self.patientSex = dicomObject.getString(Tag.PatientSex, '') or None
			#   AccessionNumber (identificador de la cita)
			self.accessionNumber = dicomObject.getString(Tag.AccessionNumber, '') or None

			#   StudyInstanceUID
			self.studyInstanceUID = dicomObject.getString(Tag.StudyInstanceUID, '') or None
			#   ...?
			self.referringPhysiciansName = dicomObject.getString(Tag.ReferringPhysicianName, '') or None
			#   Medico peticionario
			self.requestingPhysician = dicomObject.getString(Tag.RequestingPhysician, '') or None
			#   Servicio peticionario
			self.requestingService = dicomObject.getString(Tag.RequestingService, '') or None

			# Valores dentro de ScheduledProcedureStepSequence:
			#   Fecha
			self.scheduledProcedureStepStartDate = dicomObject.getString(Tag.toTagPath("ScheduledProcedureStepSequence/ScheduledProcedureStepStartDate"), '') or None
			#   Hora
			self.scheduledProcedureStepStartTime = dicomObject.getString(Tag.toTagPath("ScheduledProcedureStepSequence/ScheduledProcedureStepStartTime"), '') or None
			print 'HORAAAAAAAA:', self.scheduledProcedureStepStartTime
			#	prestacion
			self.scheduledProcedureStepID = dicomObject.getString(Tag.toTagPath("ScheduledProcedureStepSequence/ScheduledProcedureStepID"), '') or None
			self.scheduledProcedureStepDescription = dicomObject.getString(Tag.toTagPath("ScheduledProcedureStepSequence/ScheduledProcedureStepDescription"), '') or None
			# XXX
			# quedaria pendiente extraer (si es posible): el tipo de exploracion, la sala y el medico

	def __str__(self):
		s = super(WLWork, self).__str__() + '\n'
		for k in self.__dict__:
##			s += '\t' + k + '=' + str(self.__dict__[k]) + '\n'
			val = self.__dict__[k]
			if isinstance(val, unicode):
				val = val.encode('latin_1') # xxx
			s += '\t' + k + '=' + str(val) + '\n'
		return s



def obtenerWorkList(callingAE, calledAE, server, port, fecha, modality):
	"""
	utilizando dcm4che, mediante JPype

	se conecta al worklist mediante DICOM y obtiene las tasks, filtrando por fecha.

	parametros:
		callingAE, calledAE, server, port:
				config de conexión al servidor de worklist
		fecha:  La fecha de la que se quiere obtener el worklist.
				Puede ser de tipo datetime.date o str. Si es str tiene que ser con el formato "YYYYMMDD"

	devuelve un list de WLWorks

	importante:
		caso multihilo: tener en cuenta que se crea un archivo .dcm de la plantilla
	"""
	log.debug('Ejecutar obtenerWorkList mediante dcm4che/JPype...')
	log.debug('parametro "fecha": ' + str(fecha) + ' (' + str(type(fecha)) + ')')
	log.debug('parametro "modality": ' + str(modality) + ' (' + str(type(modality)) + ')')

	#	no sirve llamar al metodo estatico DcmMWL.main(), que es el que se ejecuta
	#	cuando se llama a la utilidad de command-line, ya que solo muestra los
	#	resultados por pantalla.
	#	por lo tanto se implementa la llamada basandose en el codigo fuente de DcmMWL.main()

	#	este codigo es equivalente a ejecutar dcmmwl.bat -device {calling_AE} {called_AE}@{host}:{port}
	#       clase para crear Array de Java de 1 o 2 dimensiones

##	print 'isThreadAttachedToJVM', jpype.isThreadAttachedToJVM()
	if not jpype.isThreadAttachedToJVM():
		jpype.attachThreadToJVM()

	Tag = jpype.JPackage('org').dcm4che2.data.Tag
	JArrayStr = jpype.JArray(jpype.java.lang.String)
##	JArrayStr2D = jpype.JArray(jpype.java.lang.String, 2)

	#	definidos en dcm4che2.data.UID: (XXX	probar jpype.JPackage('org').dcm4che2.data.UID...)
	#		Implicit VR Little Endian - Transfer Syntax
	ImplicitVRLittleEndian = "1.2.840.10008.1.2"
	#		Explicit VR Little Endian - Transfer Syntax
	ExplicitVRLittleEndian = "1.2.840.10008.1.2.1"
	# ////////////////////////
	dcmmwl = jpype.JPackage('org').dcm4che2.tool.dcmmwl.DcmMWL(callingAE)
	dcmmwl.setCalledAET(calledAE)
	dcmmwl.setRemoteHost(server)
	dcmmwl.setRemotePort(int(port))

	#	parametros (fecha, modality)
	#	NOTAS:
	#       addMatchingKey()        añade una clave de query en la raiz
	#       addSpsMatchingKey()     añade una clave de query dentro de ScheduledProcedureStepSequence
	#dcmmwl.addMatchingKey(Tag.toTagPath(''), '') # para añadir claves seria asi
	dcmmwl.addSpsMatchingKey(Tag.ScheduledProcedureStepStartDate, date_to_DICOM(fecha))
	dcmmwl.addSpsMatchingKey(Tag.Modality, modality)

	a = JArrayStr( [ExplicitVRLittleEndian, ImplicitVRLittleEndian] )
	dcmmwl.setTransferSyntax(a)

	#	no estoy seguro si son necesarios:
	dcmmwl.setPackPDV(True)
	dcmmwl.setTcpNoDelay(True)
	# ////////////////////////

	#	no necesarios:
	##dcmmwl.setCalling('')		#	por defecto utiliza el parametro del constructor de DcmMWL
	##dcmmwl.setLocalHost('')	#	por defecto usa cualquier puerto libre
	# ////////////////////////

	try:
		dcmmwl.open()
	except Exception as e:
		log.error("ERROR: Failed to establish association: %s" % e)
	log.info("Connected to %s" % calledAE)

	works = []
	try:
		result = dcmmwl.query()		#	devuelve una lista (java.util.List) de objetos
		log.info("Received %s matching entries" % result.size())
		#	iterar los resultados
		for i in range(result.size()):
			dicomObject = result.get(i) #	org.dcm4che2.data.DicomObject
##			log.info('resultado %s (%s)' % (i, dicomObject.getClass()))
			log.info(dicomObject)
			w = WLWork_dcm4che(dicomObject)
			log.debug(str(w))
			works.append(w)

			#	dicomObject.get(0x00100010)	//	devuelve un org.dcm4che2.data.DicomElement
			#	dicomObject.getString(0x00100010)	//	devuelve un string

##			log.info('patientName: %s' % dicomObject.getString(0x00100010, '-'))
##			log.info('patientID: %s' % dicomObject.getString(0x00100020, '-'))
			log.info('-------------------')
	except Exception as e:
##		raise
		log.error("ERROR EJECUTANDO dcmmwl.query(): %s" % e)

	try:
		dcmmwl.close()
	except Exception as e:
		log.error("ERROR EJECUTANDO dcmmwl.close(): %s" % e)
	log.info("Released connection to %s" % calledAE)

	jpype.java.lang.System.gc() # sugiere al garbage collector de Jaa que haga limpieza...

	return works


inicializar()




"""
ASI ES COMO LO HACE DESDE MIRTH:

	//	acceso a Worklist

	var DcmMWL = Packages.org.dcm4che2.tool.dcmmwl.DcmMWL;
	var Array = Packages.java.lang.reflect.Array;
	var String = Packages.java.lang.String;

	//	no sirve llamar al metodo estatico DcmMWL.main(), que es el que se ejecuta
	//	cuando se llama a la utilidad de command-line, ya que solo muestra los
	//	resultados por pantalla.
	//	por lo tanto se implementa la llamada basandose en el codigo fuente de DcmMWL.main()

	var calling_AE = 'dev';
	var called_AE = 'PRUEBAS_MIRTH';
	var host = '127.0.0.1';
	var port = '104';

	//	este codigo es equivalente a ejecutar dcmmwl.bat -device {calling_AE} {called_AE}@{host}:{port}
	var a;
	//	definidos en dcm4che2.data.UID:
	//		Implicit VR Little Endian - Transfer Syntax
	var ImplicitVRLittleEndian = "1.2.840.10008.1.2";
	//		Explicit VR Little Endian - Transfer Syntax
	var ExplicitVRLittleEndian = "1.2.840.10008.1.2.1";
	///////////////////////////////////

	var dcmmwl = new DcmMWL(calling_AE);
	dcmmwl.setCalledAET(called_AE);
	dcmmwl.setRemoteHost(host);
	dcmmwl.setRemotePort(port);
	a = Array.newInstance(String, 2);
	a[0] = ExplicitVRLittleEndian;
	a[1] = ImplicitVRLittleEndian;
	dcmmwl.setTransferSyntax(a);

	//	no estoy seguro si son necesarios:
	dcmmwl.setPackPDV(true);
	dcmmwl.setTcpNoDelay(true);
	////////////////////////

	//	no necesarios:
	/*
	dcmmwl.setCalling('');		//	por defecto utiliza el parametro del constructor de DcmMWL
	dcmmwl.setLocalHost('');	//	por defecto usa cualquier puerto libre
	*/
	////////////////////////

	try {
		dcmmwl.open();
	} catch (e) {
		logger.error("ERROR: Failed to establish association: " + e);
	//	System.err.println("ERROR: Failed to establish association:");
	//	e.printStackTrace(System.err);
	//	System.exit(2);
	}

	logger.info("Connected to " + called_AE);

	try {
		var result = dcmmwl.query();	//	devuelve una lista (java.util.List) de objetos
		logger.info("Received " + result.size() + " matching entries");
		//	iterar los resultados
		var dicomObject;	//	org.dcm4che2.data.DicomObject
		for (var i = 0; i < result.size(); i++) {
			dicomObject = result.get(i);
			logger.info('resultado ' + i + ' (' + dicomObject.getClass() + ')');
			logger.info(dicomObject);

			//	dicomObject.get(0x00100010)	//	devuelve un org.dcm4che2.data.DicomElement
			//	dicomObject.getString(0x00100010)	//	devuelve un string

			logger.info('patientName: ' + dicomObject.getString(0x00100010, '-'));
			logger.info('patientID: ' + dicomObject.getString(0x00100020, '-'));
	//		logger.info('patientName: ' + dicomObject.get(0x00100010));
	//		logger.info('patientID: ' + dicomObject.get(0x00100020));
			logger.info('-------------------');
		}
	} catch (e) {
		logger.error("ERROR EJECUTANDO dcmmwl.query(): " + e);
	}

	try {
		dcmmwl.close();
	} catch (e) {
		logger.error("ERROR EJECUTANDO dcmmwl.close(): " + e);
	}
	logger.info("Released connection to " + called_AE);



	/*

		//	DcmMWL.main(), extraido de DcmMWL.java

	    public static void main(String[] args) {
	        CommandLine cl = parse(args);
	        DcmMWL dcmmwl = new DcmMWL(cl.hasOption("device")
	                ? cl.getOptionValue("device") : "DCMMWL");
	        final List<String> argList = cl.getArgList();
	        String remoteAE = argList.get(0);
	        String[] calledAETAddress = split(remoteAE, '@');
	        dcmmwl.setCalledAET(calledAETAddress[0]);
	        if (calledAETAddress[1] == null) {
	            dcmmwl.setRemoteHost("127.0.0.1");
	            dcmmwl.setRemotePort(104);
	        } else {
	            String[] hostPort = split(calledAETAddress[1], ':');
	            dcmmwl.setRemoteHost(hostPort[0]);
	            dcmmwl.setRemotePort(toPort(hostPort[1]));
	        }
	        if (cl.hasOption("L")) {
	            String localAE = cl.getOptionValue("L");
	            String[] callingAETHost = split(localAE, '@');
	            dcmmwl.setCalling(callingAETHost[0]);
	            if (callingAETHost[1] != null) {
	                dcmmwl.setLocalHost(callingAETHost[1]);
	            }
	        }
	        if (cl.hasOption("username")) {
	            String username = cl.getOptionValue("username");
	            UserIdentity userId;
	            if (cl.hasOption("passcode")) {
	                String passcode = cl.getOptionValue("passcode");
	                userId = new UserIdentity.UsernamePasscode(username,
	                        passcode.toCharArray());
	            } else {
	                userId = new UserIdentity.Username(username);
	            }
	            userId.setPositiveResponseRequested(cl.hasOption("uidnegrsp"));
	            dcmmwl.setUserIdentity(userId);
	        }
	        if (cl.hasOption("connectTO"))
	            dcmmwl.setConnectTimeout(parseInt(cl.getOptionValue("connectTO"),
	                    "illegal argument of option -connectTO", 1, Integer.MAX_VALUE));
	        if (cl.hasOption("reaper"))
	            dcmmwl.setAssociationReaperPeriod(parseInt(cl.getOptionValue("reaper"),
	                    "illegal argument of option -reaper", 1, Integer.MAX_VALUE));
	        if (cl.hasOption("rspTO"))
	            dcmmwl.setDimseRspTimeout(parseInt(cl.getOptionValue("rspTO"),
	                    "illegal argument of option -rspTO", 1, Integer.MAX_VALUE));
	        if (cl.hasOption("acceptTO"))
	            dcmmwl.setAcceptTimeout(parseInt(cl.getOptionValue("acceptTO"),
	                    "illegal argument of option -acceptTO", 1, Integer.MAX_VALUE));
	        if (cl.hasOption("releaseTO"))
	            dcmmwl.setReleaseTimeout(parseInt(cl.getOptionValue("releaseTO"),
	                    "illegal argument of option -releaseTO", 1, Integer.MAX_VALUE));
	        if (cl.hasOption("soclosedelay"))
	            dcmmwl.setSocketCloseDelay(parseInt(cl.getOptionValue("soclosedelay"),
	                    "illegal argument of option -soclosedelay", 1, 10000));
	        if (cl.hasOption("rcvpdulen"))
	            dcmmwl.setMaxPDULengthReceive(parseInt(cl.getOptionValue("rcvpdulen"),
	                    "illegal argument of option -rcvpdulen", 1, 10000) * KB);
	        if (cl.hasOption("sndpdulen"))
	            dcmmwl.setMaxPDULengthSend(parseInt(cl.getOptionValue("sndpdulen"),
	                    "illegal argument of option -sndpdulen", 1, 10000) * KB);
	        if (cl.hasOption("sosndbuf"))
	            dcmmwl.setSendBufferSize(parseInt(cl.getOptionValue("sosndbuf"),
	                    "illegal argument of option -sosndbuf", 1, 10000) * KB);
	        if (cl.hasOption("sorcvbuf"))
	            dcmmwl.setReceiveBufferSize(parseInt(cl.getOptionValue("sorcvbuf"),
	                    "illegal argument of option -sorcvbuf", 1, 10000) * KB);
	        dcmmwl.setPackPDV(!cl.hasOption("pdv1"));
	        dcmmwl.setTcpNoDelay(!cl.hasOption("tcpdelay"));
	        if (cl.hasOption("C"))
	            dcmmwl.setCancelAfter(parseInt(cl.getOptionValue("C"),
	                    "illegal argument of option -C", 1, Integer.MAX_VALUE));
	        if (cl.hasOption("lowprior"))
	            dcmmwl.setPriority(CommandUtils.LOW);
	        if (cl.hasOption("highprior"))
	            dcmmwl.setPriority(CommandUtils.HIGH);
	        if (cl.hasOption("fuzzy"))
	            dcmmwl.setFuzzySemanticPersonNameMatching(true);
	        if (cl.hasOption("q")) {
	            String[] matchingKeys = cl.getOptionValues("q");
	            for (int i = 1; i < matchingKeys.length; i++, i++)
	                dcmmwl.addMatchingKey(Tag.toTagPath(matchingKeys[i - 1]), matchingKeys[i]);
	        }
	        if (cl.hasOption("r")) {
	            String[] returnKeys = cl.getOptionValues("r");
	            for (int i = 0; i < returnKeys.length; i++)
	                dcmmwl.addReturnKey(Tag.toTagPath(returnKeys[i]));
	        }
	        if (cl.hasOption("date")) {
	            dcmmwl.addSpsMatchingKey(Tag.ScheduledProcedureStepStartDate,
	                    cl.getOptionValue("date"));
	        }
	        if (cl.hasOption("time")) {
	            dcmmwl.addSpsMatchingKey(Tag.ScheduledProcedureStepStartTime,
	                    cl.getOptionValue("time"));
	        }
	        if (cl.hasOption("mod")) {
	            dcmmwl.addSpsMatchingKey(Tag.Modality, cl.getOptionValue("mod"));
	        }
	        if (cl.hasOption("aet")) {
	            dcmmwl.addSpsMatchingKey(Tag.ScheduledStationAETitle,
	                    cl.getOptionValue("aet"));
	        }

	        dcmmwl.setTransferSyntax(cl.hasOption("ivrle") ? IVRLE_TS : LE_TS);


	        if (cl.hasOption("tls")) {
	            String cipher = cl.getOptionValue("tls");
	            if ("NULL".equalsIgnoreCase(cipher)) {
	                dcmmwl.setTlsWithoutEncyrption();
	            } else if ("3DES".equalsIgnoreCase(cipher)) {
	                dcmmwl.setTls3DES_EDE_CBC();
	            } else if ("AES".equalsIgnoreCase(cipher)) {
	                dcmmwl.setTlsAES_128_CBC();
	            } else {
	                exit("Invalid parameter for option -tls: " + cipher);
	            }
	            if (cl.hasOption("tls1")) {
	                dcmmwl.setTlsProtocol(TLS1);
	            } else if (cl.hasOption("ssl3")) {
	                dcmmwl.setTlsProtocol(SSL3);
	            } else if (cl.hasOption("no_tls1")) {
	                dcmmwl.setTlsProtocol(NO_TLS1);
	            } else if (cl.hasOption("no_ssl3")) {
	                dcmmwl.setTlsProtocol(NO_SSL3);
	            } else if (cl.hasOption("no_ssl2")) {
	                dcmmwl.setTlsProtocol(NO_SSL2);
	            }
	            dcmmwl.setTlsNeedClientAuth(!cl.hasOption("noclientauth"));
	            if (cl.hasOption("keystore")) {
	                dcmmwl.setKeyStoreURL(cl.getOptionValue("keystore"));
	            }
	            if (cl.hasOption("keystorepw")) {
	                dcmmwl.setKeyStorePassword(
	                        cl.getOptionValue("keystorepw"));
	            }
	            if (cl.hasOption("keypw")) {
	                dcmmwl.setKeyPassword(cl.getOptionValue("keypw"));
	            }
	            if (cl.hasOption("truststore")) {
	                dcmmwl.setTrustStoreURL(
	                        cl.getOptionValue("truststore"));
	            }
	            if (cl.hasOption("truststorepw")) {
	                dcmmwl.setTrustStorePassword(
	                        cl.getOptionValue("truststorepw"));
	            }
	            long t1 = System.currentTimeMillis();
	            try {
	                dcmmwl.initTLS();
	            } catch (Exception e) {
	                System.err.println("ERROR: Failed to initialize TLS context:"
	                        + e.getMessage());
	                System.exit(2);
	            }
	            long t2 = System.currentTimeMillis();
	            System.out.println("Initialize TLS context in "
	                    + ((t2 - t1) / 1000F) + "s");
	        }

	        long t1 = System.currentTimeMillis();
	        try {
	            dcmmwl.open();
	        } catch (Exception e) {
	            System.err.println("ERROR: Failed to establish association:");
	            e.printStackTrace(System.err);
	            System.exit(2);
	        }
	        long t2 = System.currentTimeMillis();
	        System.out.println("Connected to " + remoteAE + " in "
	                + ((t2 - t1) / 1000F) + "s");

	        try {
	            List<DicomObject> result = dcmmwl.query();
	            long t3 = System.currentTimeMillis();
	            System.out.println("Received " + result.size()
	                    + " matching entries in " + ((t3 - t2) / 1000F) + "s");
	        } catch (IOException e) {
	            // TODO Auto-generated catch block
	            e.printStackTrace();
	        } catch (InterruptedException e) {
	            // TODO Auto-generated catch block
	            e.printStackTrace();
	        }
	        try {
	            dcmmwl.close();
	        } catch (InterruptedException e) {
	            // TODO Auto-generated catch block
	            e.printStackTrace();
	        }
	        System.out.println("Released connection to " + remoteAE);
	}
	*/
"""
