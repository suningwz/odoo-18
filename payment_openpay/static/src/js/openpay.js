odoo.define('payment_openpay.openpay', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require("web.Dialog");
    var publicWidget = require('web.public.widget');
    var qweb = core.qweb;
    var _t = core._t;

    publicWidget.registry.websiteOpenpay = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        read_events: {
            'change .select_payment_method': '_onSelectPaymentMethod',
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * @private
         * @param {Event} ev
         */

        init: function (parent, options) {
            this.pass_submit = false;
            this._super.apply(this, arguments);
        },

        _onSelectPaymentMethod: function (ev) {
            ev.preventDefault();
            var self = this;
            var $element = $(ev.currentTarget).val();
            var partner_info;
            if ($element == "card") {
                $('#payment-paynet').hide();
                $('#payment-card').show();
                $('#payment_method').val('card');

                var $partner_id = $('#partner_id').val();
                var result = ajax.jsonRpc("/openpay/card/address", 'call', {
                    'partner_id': $partner_id
                }, {
                    'async': false
                }).then(function (data) {
                    partner_info = data;
                });

                $('#openpay-checkout-card').submit(function (ev) {
                    if (self.pass_submit) {
                        return true;
                    }

                    if (partner_info) {
                        let data_partner = JSON.parse(partner_info);
                        let acquirer_form = $('#openpay-checkout-card');
                        let inputs_form = $('input', acquirer_form);
                        let form_data = self.getFormData(inputs_form);
                        setTimeout(function () {
                            self._GenerateTocken({
                                ...form_data,
                                ...data_partner
                            });
                        }, 5);
                    }
                    return false; // return false to cancel form action
                });

            } else if ($element == "store") {
                $('#payment-paynet').show();
                $('#payment-card').hide();
                $('#payment_method').val('store');
            } else {
                $('#payment-paynet').hide();
                $('#payment-card').hide();
            }
        },

        _GenerateTocken: function (data_info) {
            var self = this;
            let dt = data_info;

            OpenPay.setId(dt.merchant_id);
            OpenPay.setApiKey(dt.public_key);
//            var sandbox_mode = true
//            if (dt.payment_mode_state == "enabled") {
//                $sandbox_mode = false
//            }

            OpenPay.setSandboxMode();
            var deviceSessionId = OpenPay.deviceData.setup("openpay-checkout", "device-session-id");

            let create_parameters_object = {
                "card_number": dt.cardnumber,
                "holder_name": dt.holdername,
                "expiration_year": dt.cardExpiryYear,
                "expiration_month": dt.cardExpiryMonth,
                "cvv2": dt.cardCVC,
                "address": {
                    "city": dt.city,
                    "line3": dt.line3,
                    "postal_code": dt.postal_code,
                    "line1": dt.line1,
                    "line2": dt.line2,
                    "state": dt.state,
                    "country_code": dt.country_code
                }
            }

            OpenPay.token.create(create_parameters_object,
                function (result) {
                    $('#token_id').val(result.data.id);
                    $('#device-session-id-card').val(deviceSessionId)
                    self.pass_submit = true;
                    $('.js_pay').click();
                },
                function (error) {
                    alert(error);
                    console.error(error);
                });
        },

        getFormData: function ($form) {
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function (n, i) {
                indexed_array[n.name] = n.value;
            });
            return indexed_array;
        }
    });

    $(document).ready(function () {
        var $modal;
        $('#o_payment_form_pay').on('click', function (ev) {

            var $checkedRadio = this.$('input[type="radio"]:checked');

            // first we check that the user has selected a openpay
            // as s2s payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'openpay') {
                this._createOpenpayToken(ev, $checkedRadio);

                OpenPay.setId(dt.merchant_id);
                OpenPay.setApiKey(dt.public_key);
                return false;
            }
        });
        /*
        function create_draft_transaction() {
            var $payment_method = $('#payment_method');
            var $checked_radio = $payment_method.find('input[type="radio"]:checked');
            var acquirer_id = get_acquirer_id_from_radio($checked_radio);
            var $tx_url = $payment_method.find('input[name="prepare_tx_url"]');
            if ($checked_radio.length === 1) {
                $checked_radio = $checked_radio[0];
                if ($tx_url.length === 1) {
                    return ajax.jsonRpc($tx_url[0].value, 'call', {
                        'acquirer_id': parseInt(acquirer_id),
                    }).then(function (result) {
                        if (result) {
                            $('#payment_data').html(result);
                        } else {
                            payment_display_error(
                                _t('Server Error'),
                                _t("We are not able to redirect you to the payment form.")
                            );
                        }
                    });
                } else {
                    // we append the form to the body and send it.
                    payment_display_error(
                        _t("Cannot set-up the payment"),
                        _t("We're unable to process your payment.")
                    );
                }
            } else {
                payment_display_error(
                    _t('No payment method selected'),
                    _t('Please select a payment method.')
                );
            }
        }

        function is_new_payment_radio(element) {
            return $(element).data('s2s-payment') === 'True';
        }

        function is_form_payment_radio(element) {
            return $(element).data('form-payment') === 'True';
        }

        function get_acquirer_id_from_radio(element) {
            return $(element).data('acquirer-id');
        }

        function payment_display_error(title, message) {
            var $payment_method = $('#payment_method');
            var $checked_radio = $payment_method.find('input[type="radio"]:checked'),
                acquirer_id = get_acquirer_id_from_radio($checked_radio[0]);

            var $acquirer_form;
            if (is_new_payment_radio($checked_radio[0])) {
                $acquirer_form = $payment_method.find('#o_payment_add_token_acq_' + acquirer_id);
            } else if (is_form_payment_radio($checked_radio[0])) {
                $acquirer_form = $payment_method.find('#o_payment_form_acq_' + acquirer_id);
            }

            if ($checked_radio.length === 0) {
                payment_dialog_message(title, message);
            } else {
                $('#payment_error').remove();
                var message_result = '<div class="alert alert-danger mb4" id="payment_error">';
                if (title != '') {
                    message_result = message_result + '<b>' + _.str.escapeHTML(title) + ':</b></br>';
                }
                message_result = message_result + _.str.escapeHTML(message) + '</div>';
                $acquirer_form.append(message_result);
            }
        }*/

        /*function payment_dialog_message(title, message) {
            return new Dialog(null, {
                title: _t('Error: ') + _.str.escapeHTML(title),
                size: 'medium',
                $content: "<p>" + (_.str.escapeHTML(message) || "") + "</p>",
                buttons: [{
                    text: _t('Ok'),
                    close: true
                }]
            }).open();
        }*/

       /* var $payment = $("#payment_method");
        $payment.on("click", "input[name='pm_id']", function (ev) {
            var provider = $(this).attr('data-provider');
            if (provider !== "openpay" && ($modal)) {
                $modal.hide();
                $('#o_payment_form_pay').show();
                return;
            } else if (provider === "openpay" && ($modal)) {
                $modal.show();
                $('#o_payment_form_pay').hide();
                return;
            }
        });*/
    });

});
