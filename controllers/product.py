from odoo import http
from odoo.http import request, Response
import json
from odoo.exceptions import AccessDenied

# ============================================
#   CONFIGURACIÓN CORS
# ============================================
ALLOWED_ORIGIN = "*"  # Cambia esto a tu dominio Angular si es necesario


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

    @http.route('/api/create_product',type='http', auth='none', methods=['POST'],csrf=False)
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

        # 3. Validación mínima
        if not product_data.get('name'):
            return self._create_response(
                {"status": "error", "message": "Missing required field: name"},
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
            product = request.env['product.template'].sudo().create({
                # ORDENADO SEGÚN TU EXCEL
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
            })

        except Exception as e:
            return self._create_response(
                {"status": "error", "message": f"Creation failed: {str(e)}"},
                500
            )

        # ============================================
        # 6. Ajuste de Inventario (si viene qty_available)
        # ============================================
        qty = product_data.get('qty_available')

        if qty and float(qty) > 0:

            # Buscar ubicación WH/Stock
            stock_location = request.env['stock.location'].sudo().search([
                ('complete_name', '=', 'WH/Stock')
            ], limit=1)

            if not stock_location:
                return self._create_response(
                    {"status": "error", "message": "Stock location WH/Stock not found"},
                    400
                )

            try:
                # Crear ajuste de inventario
                inventory = request.env['stock.inventory'].sudo().create({
                    'name': f"Ajuste API producto {product.id}",
                    'location_ids': [(6, 0, [stock_location.id])],
                    'product_ids': [(6, 0, [product.id])],
                    'company_id': request.env.company.id,
                })

                # Crear línea del ajuste
                request.env['stock.inventory.line'].sudo().create({
                    'inventory_id': inventory.id,
                    'product_id': product.id,
                    'location_id': stock_location.id,
                    'product_uom_id': product.uom_id.id,
                    'theoretical_qty': 0,
                    'product_qty': qty,
                })

                # Validar el ajuste
                inventory.action_validate()

            except Exception as e:
                return self._create_response(
                    {
                        "status": "error",
                        "message": f"Product created but inventory adjustment failed: {str(e)}"},
                    500
                )

        # ============================================
        # 7. Respuesta final
        # ============================================
        return self._create_response(
            {"status": "success", "product_id": product.id},201
        )
