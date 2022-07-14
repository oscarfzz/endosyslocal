YUI.add('modulo_prueba',
        function(Y) {
            Y.namespace('moduloprueba');
            Y.moduloprueba.test = function() {
                alert('hola!');
            };
        },
        '0.1.1', /* module version */
        {
            requires: ['base']
        }
    );