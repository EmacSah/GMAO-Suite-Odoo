# Dans le fichier models/maintenance_graph_wizard.py

from odoo import models, fields

class MaintenanceGraphWizard(models.TransientModel):
    _name = 'maintenance.graph.wizard'
    _description = 'Wizard de personnalisation du graphique de maintenance'

    measure = fields.Selection([
        ('quantity', 'Quantité'),
        ('cost', 'Coût'),
        ('interventions', 'Nombre d\'interventions'),
        ('min_stock', 'Stock minimum'),
    ], string='Mesure', required=True, default='quantity')

    groupby = fields.Selection([
        ('product_id', 'Pièce'),
        ('state', 'État'),
        ('technician_id', 'Technicien'),
        ('intervention_id', 'Intervention'),
        ('withdrawal_date', 'Date de retrait'),
    ], string='Grouper par', required=True, default='product_id')

    graph_type = fields.Selection([
        ('bar', 'Histogramme'),
        ('line', 'Ligne'),
        ('pie', 'Camembert'),
    ], string='Type de graphique', required=True, default='bar')