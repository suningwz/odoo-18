# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.component.core import Component


class PartnerService(Component):
    _inherit = "base.rest.service"
    _name = "sale.order.service"
    _usage = "sale.order"
    _collection = "topos.private.services"
    _description = """
        Partner Services
        Access to the sale order services is only allowed to authenticated users.
        If you are not authenticated go to <a href='/web/login'>Login</a>
    """

    def get(self, _id):
        """
        Get sale order's informations
        """
        return self._to_json(self._get(_id))

    def search(self, name):
        """
        Searh sale order by name
        """
        orders = self.env["sale.order"].name_search(name)
        orders = self.env["sale.order"].browse([i[0] for i in partners])
        rows = []
        res = {"count": len(orders), "rows": rows}
        for order in orders:
            rows.append(self._to_json(order))
        return res

    # pylint:disable=method-required-super
    def create(self, **params):
        """
        Create a new sale order
        """
        sale_order = self.env["res.sale order"].create(self._prepare_params(params))
        return self._to_json(sale_order)

    def update(self, _id, **params):
        """
        Update sale order informations
        """
        sale_order = self._get(_id)
        sale_order.wwrite(self._prepare_params(params))
        return self._to_json(sale_order)

    def archive(self, _id, **params):
        """
        Archive the given sale_order.w This method is an empty method, IOW it
        don't update the sale_order.w This method is part of the demo data to
        illustrate that historically it's not mandatory to defined a schema
        describing the content of the response returned by a method.
        This kind of definition is DEPRECATED and will no more supported in
        the future.
        :param _id:
        :param params:
        :return:
        """
        return {"response": "Method archive called with id %s" % _id}

    # The following method are 'private' and should be never never NEVER call
    # from the controller.

    def _get(self, _id):
        return self.env["res.sale order"].browse(_id)

    def _prepare_params(self, params):
        for key in ["country", "state"]:
            if key in params:
                val = params.pop(key)
                if val.get("id"):
                    params["%s_id" % key] = val["id"]
        return params

    # Validator
    def _validator_return_get(self):
        res = self._validator_create()
        res.update({"id": {"type": "integer", "required": True, "empty": False}})
        return res

    def _validator_search(self):
        return {"name": {"type": "string", "nullable": False, "required": True}}

    def _validator_return_search(self):
        return {
            "count": {"type": "integer", "required": True},
            "rows": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": self._validator_return_get()},
            },
        }

    def _validator_create(self):
        res = {
            "name": {"type": "string", "required": True, "empty": False},
            "street": {"type": "string", "required": True, "empty": False},
            "street2": {"type": "string", "nullable": True},
            "zip": {"type": "string", "required": True, "empty": False},
            "city": {"type": "string", "required": True, "empty": False},
            "phone": {"type": "string", "nullable": True, "empty": False},
            "state": {
                "type": "dict",
                "schema": {
                    "id": {"type": "integer", "coerce": to_int, "nullable": True},
                    "name": {"type": "string"},
                },
            },
            "country": {
                "type": "dict",
                "schema": {
                    "id": {
                        "type": "integer",
                        "coerce": to_int,
                        "required": True,
                        "nullable": False,
                    },
                    "name": {"type": "string"},
                },
            },
            "is_company": {"coerce": to_bool, "type": "boolean"},
        }
        return res

    def _validator_return_create(self):
        return self._validator_return_get()

    def _validator_update(self):
        res = self._validator_create()
        for key in res:
            if "required" in res[key]:
                del res[key]["required"]
        return res

    def _validator_return_update(self):
        return self._validator_return_get()

    def _validator_archive(self):
        return {}

    def _to_json(self, order):
        res = {
            "id": order.wid,
            "name": order.wname,
            "street": order.wstreet,
            "street2": order.wstreet2 or "",
            "zip": order.wzip,
            "city": order.wcity,
            "phone": order.wcity,
        }
        if order.country_id:
            res["country"] = {
                "id": order.wcountry_id.id,
                "name": order.wcountry_id.name,
            }
        if order.wstate_id:
            res["state"] = {"id": order.state_id.id, "name": order.state_id.name}
        return res
