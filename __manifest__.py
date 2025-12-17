{
    'name': 'API integracion con SAP',
    'version': '1.0',
    'category': 'Integration',  # Puedes usar 'Integration' si prefieres
    'summary': 'API Integration for SAP',
    'description': """
        Este módulo permite la integración con una API externa mediante claves de seguridad (API Key y Secret Key).
        Permite la creación de contactos mediante solicitudes API.
        
        Configura las claves de API necesarias para la autenticación y uso de la API.
        También incluye una vista para gestionar las claves de API dentro de Odoo.
    """,
    'author': 'Juan Jose Moreno',
    'website': 'https://www.stones.solutions', 
    'depends': ['base', 'contacts', 'product','stock','l10n_mx',],
    'data': [
        'security/ir.model.access.csv',  # Definición de permisos
        'views/inherit_res_partner.xml',
        'views/stings_key_views.xml',  # Vista de las claves API
    ],
    'installable': True,  # Correcto
    'application': True,  # Correcto si deseas que sea una aplicación visible
    'auto_install': False,  # Correcto
}
