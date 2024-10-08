# File: wizards/maintenance_parts_used_report_wizard.py

from odoo import models, fields, api

class MaintenancePartsUsedReportWizard(models.TransientModel):
    _name = 'maintenance.parts.used.report.wizard'
    _description = 'Assistant de rapport des pièces utilisées en maintenance'

    date_from = fields.Date(string='Date de début')
    date_to = fields.Date(string='Date de fin')
    product_ids = fields.Many2many('product.product', string='Produits')
    technician_ids = fields.Many2many('hr.employee', string='Techniciens')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('reserved', 'Réservé'),
        ('used', 'Utilisé'),
        ('cancelled', 'Annulé')
    ], string='État')
    groupby = fields.Selection([
        ('product_id', 'Produit'),
        ('technician_id', 'Technicien'),
        ('state', 'État'),
        ('intervention_id', 'Intervention')
    ], string='Grouper par')

    
    def generate_report(self):
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'maintenance.parts.used'),
            'form': self.read(['date_from', 'date_to', 'product_ids', 'technician_ids', 'state', 'groupby'])[0]
        }
        return self.env.ref('gmao_suite.action_report_maintenance_parts_used').report_action(self, data=data)