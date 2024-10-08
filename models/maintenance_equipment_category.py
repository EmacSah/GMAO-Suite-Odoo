from odoo import models, fields

class MaintenanceEquipmentCategory(models.Model):
    _name = 'maintenance.equipment.category'
    _description = 'Catégorie d\'équipement GMAO'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('maintenance.equipment.category', string='Catégorie parente')
    child_ids = fields.One2many('maintenance.equipment.category', 'parent_id', string='Sous-catégories')
    equipment_count = fields.Integer(string='Nombre d\'équipements', compute='_compute_equipment_count')

    def _compute_equipment_count(self):
        for category in self:
            category.equipment_count = self.env['maintenance.equipment'].search_count([('category_id', '=', category.id)])