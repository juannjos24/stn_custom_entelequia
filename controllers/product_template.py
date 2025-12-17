from odoo import http
from odoo.http import request, Response
import json
from odoo.exceptions import AccessDenied

# ============================================
#   CONFIGURACIÓN CORS
# ============================================
ALLOWED_ORIGIN = "*"  


def make_cors_headers():
    return [
        ('Access-Control-Allow-Origin', ALLOWED_ORIGIN),
        ('Access-Control-Allow-Methods', 'POST, GET, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type, apiKey, secretKey'),
        ('Access-Control-Allow-Credentials', 'true'),
        ('Access-Control-Max-Age', '3600'),
    ]


# ============================================
#   CONTROLADOR PRINCIPAL
# ============================================
class ApiController(http.Controller):
    # Función de ayuda para construir respuestas HTTP
    def _create_response(self, data, status_code):
        headers = make_cors_headers()
        headers.append(('Content-Type', 'application/json'))
        return Response(json.dumps(data), status=status_code, headers=headers)

    @http.route('/api/create_product',type='http', auth='public', methods=['POST'],csrf=False)
    def create_product(self, **kwargs):

        api_key = request.httprequest.headers.get('apiKey')
        secret_key = request.httprequest.headers.get('secretKey')

        # 1. Validar headers
        if not api_key or not secret_key:
            return self._create_response(
                {"status": "error", "message": "Missing required headers (apiKey and/or secretKey)"},
                400
            )

        api_record = request.env['stings.key'].sudo().search([
            ('key', '=', api_key),
            ('secret_key', '=', secret_key)
        ], limit=1)

        if not api_record:
            return self._create_response(
                {"status": "error", "message": "Invalid API Key or Secret Key"},
                401
            )

        # 2. Leer JSON
        try:
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return self._create_response(
                {"status": "error", "message": "Invalid JSON payload format"},
                400
            )

        product_data = data.get('product_data')

        if not product_data or not isinstance(product_data, dict):
            return self._create_response(
                {"status": "error", "message": "No valid product_data provided"},
                400
            )
        
        # 3. Validación mínima de campos requeridos
        required_fields = {
            "name": "Nombre del producto",
            "id_secundario_sap": "ID Secundario SAP"
        }

        missing_fields = [label for field, label in required_fields.items() if not product_data.get(field)]

        if missing_fields:
            return self._create_response(
                {
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                },
                400
            )

        # ============================================
        # 4. Conversión SAT → UNSPSC interno
        # ============================================
        unspsc_id = False
        sat_id = product_data.get('unspsc_code_sat_id')

        if sat_id:
            sat_code = str(sat_id).strip().zfill(
                8)  # Normalizar a 8 dígitos UNSPSC

            unspsc = request.env['product.unspsc.code'].sudo().search([
                ('code', '=', sat_code)
            ], limit=1)

            if not unspsc:
                return self._create_response(
                    {
                        "status": "error",
                        "message": f"UNSPSC code {sat_code} not found in product_unspsc_code table"
                    },
                    400
                )

            unspsc_id = unspsc.id

        # ============================================
        # 5. Crear producto
        # ============================================
        try:
            # Forzar compañía antes del create (EVITA Expected singleton)
            company = request.env['res.company'].sudo().search([], limit=1)
            env_product = request.env['product.template'].sudo().with_company(company)

            product = env_product.create({
                'name': product_data.get('name'),
                'sale_ok': product_data.get('sale_ok', True),
                'purchase_ok': product_data.get('purchase_ok', True),
                'type': product_data.get('type', 'consu'),
                'invoice_policy': product_data.get('invoice_policy', 'order'),
                'list_price': product_data.get('list_price', 0.0),
                'uom_id': product_data.get('uom_id'),
                'taxes_id': [(6, 0, product_data.get('taxes_id', []))],
                'standard_price': product_data.get('standard_price', 0.0),
                'categ_id': product_data.get('categ_id'),
                'default_code': product_data.get('default_code'),                
                'unspsc_code_id': unspsc_id,
                'is_storable':product_data.get('is_storable'),
                'qty_available':product_data.get('qty_available'),
                # Campos SAP
                'pronosticado_sap': product_data.get('pronosticado_sap'),
                'id_secundario_sap': product_data.get('id_secundario_sap'),
            })

        except Exception as e:
            return self._create_response(
                {"status": "error", "message": f"Creation failed: {str(e)}"},
                500
            )

        # ============================================
        # 6. Respuesta final
        # ============================================
        return self._create_response(
            {"status": "success", "product_id": product.id},201
        )
