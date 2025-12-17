from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    pronosticado_sap = fields.Float(
        string="Pronosticado SAP",
        help="Cantidad pronosticada enviada desde SAP."
    )

    id_secundario_sap = fields.Char(
        string="ID Secundario SAP",
        help="Identificador único del producto proveniente de SAP."
    )
