odoo.define('payment_openpay.processing', function (require) {
    'use strict';

var publicWidget = require('web.public.widget');
    

var PaymentProcessing = publicWidget.registry.PaymentProcessing;
return PaymentProcessing.include({
	processPolledData: function(transactions) {
        if (transactions.length > 0 && ['paynet'].indexOf(transactions[0].acquirer_provider) >= 0) {
            window.location = transactions[0].return_url;
            return;
        }
		else{
			return this._super.apply(this, arguments);
		}
	},
});
    
});
