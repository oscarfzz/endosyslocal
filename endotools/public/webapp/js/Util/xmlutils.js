xmlu = function() {

	return {
	
		element_text: function(el, defaultvalue) {
			if (defaultvalue == undefined) defaultvalue = '';
			if (el.firstChild)
				return el.firstChild.data;
			else
				return defaultvalue;	
		},
		
		set_element_text: function(el, value) {
			if (el.firstChild)
				el.firstChild.data = value;
		}		
	}

}();