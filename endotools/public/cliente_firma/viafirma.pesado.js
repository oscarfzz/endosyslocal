
var viafirmaWindow;

var viafirma = {

    init: function (options) {
        var initTime = new Date().getTime();
        var def = $.Deferred();

        var unloadedTime = 10;
        if (options.unloadedTime != null && options.unloadedTime != 0) {
            unloadedTime = options.unloadedTime;
        }
        if (!options.operationId || options.operationId == "") {
            console.error("operationId can't be empty");
            return;
        }

        if (!options.viafirmaUrl || options.viafirmaUrl == "") {
            console.error("viafirmaUrl can't be empty");
            return;
        }

        var finalOptions = {
            operationId: options.operationId,
            viafirmaUrl: options.viafirmaUrl,
        };

        if (finalOptions.viafirmaUrl.lastIndexOf("/") < finalOptions.viafirmaUrl.length - 1) {
            finalOptions.viafirmaUrl = finalOptions.viafirmaUrl + "/";
        }

        //comprobamos cada 2.5 segundos si las operaciones sobre el documento han  finalizado.
        var interval =  setInterval(function () {
            $.ajax({
                type: 'GET',
                url: finalOptions.viafirmaUrl + 'api/rest/services/operation/finished/' + finalOptions.operationId + "?t=" + (new Date()).getTime(),
                })
                .success(function (operation, code) {

                        var operation = operation;
                        if (code != "success") {
                            console.error("Operation status request error", operation);
                            clearInterval(interval);
                        } 
                        else {
                            console.debug(operation);

                            if (operation.isFinished) {
                                clearInterval(interval);

                                if (operation.isSignature) {
                                    var promise = viafirma._sign(finalOptions);
                                    promise.then(function(data){def.resolve(data);});
                                } 
                            } 
                        }
                    })
                .error(function(e){
                    alert('Error conectando con la plataforma de Viafirma')
                    clearInterval(interval)
                    def.reject(e);
                })
        }, 2500);

        return def.promise()

    },

    _sign: function (finalOptions) {
        var def = $.Deferred();
        //obtenemos el id del documento firmado        
        $.ajax({
            url: finalOptions.viafirmaUrl + 'api/rest/services/signature/' + finalOptions.operationId + "?t=" + (new Date()).getTime(),
            type: 'GET'
        }).success(function(signature,code) {
            var signature = signature;

            if (code != "success") {
                console.error("Signature operation request error", signature);
            } else {
                //viafirmaWindow.close();

                //Obtenemos el documento firmado en binario, para ello necesitamos pasar el req.responseType = "blob";
                //si lo hacemos con ajax no es capaz de pasar el fichero al callback del succes

                var req = new XMLHttpRequest();
                  req.open("GET",finalOptions.viafirmaUrl + "/v/" + signature.signatureId+"?d=true", true);
                  req.responseType = "blob";

                  req.onload = function (event) {
                    var blob = req.response;
                    def.resolve({'binaryPdf':blob})
                  };

                  req.error = function(e){
                     alert('Error conectando con la plataforma de Viafirma al obtener el documento')
                     def.reject(e)
                  }

                  req.send();

                return req;
            }
        })
        .error(function(e){
                    alert('Error contactando con la plataforma de Viafirma')
                    def.reject(e);
                })
        return def.promise();
    },

    firmar: function (options) {
        unset_prevenir_refresco_manual(1000);
        uri = "viafirmawpfclient://?url="+options.viafirmaUrl+"&operationId=" + options.operationId ;
        window.open(uri, "_self");
        return viafirma.init(options);
    },

};

