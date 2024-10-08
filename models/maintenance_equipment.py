# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class MaintenanceEquipment(models.Model):
    _name = 'maintenance.equipment'
    _description = 'Équipement de Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom de l\'équipement', required=True, tracking=True)
    code = fields.Char(string='Code de l\'équipement', required=True, tracking=True)
    category_id = fields.Many2one('maintenance.equipment.category', string='Catégorie', required=True)
    model = fields.Char(string='Modèle')
    serial_number = fields.Char(string='Numéro de série')
    vendor_id = fields.Many2one('res.partner', string='Fournisseur')
    
    site_id = fields.Many2one('maintenance.site', string='Site', required=True)
    location = fields.Char(string='Emplacement précis')
    
    purchase_date = fields.Date(string='Date d\'achat')
    warranty_expiration_date = fields.Date(string='Date d\'expiration de la garantie')
    
    cost = fields.Float(string='Coût d\'achat')
    currency_id = fields.Many2one('res.currency', string='Devise', default=lambda self: self.env.company.currency_id)
    
    maintenance_team_id = fields.Many2one('maintenance.team', string='Équipe de maintenance')
    technician_user_id = fields.Many2one('res.users', string='Technicien responsable')
    
    maintenance_count = fields.Integer(string='Nombre de maintenances', compute='_compute_maintenance_count')
    maintenance_open_count = fields.Integer(string='Maintenances ouvertes', compute='_compute_maintenance_count')
    
    period = fields.Integer(string='Périodicité de maintenance préventive (jours)')
    next_maintenance_date = fields.Date(string='Prochaine maintenance prévue', compute='_compute_next_maintenance')
    
    effective_date = fields.Date(string='Date de mise en service')
    scrap_date = fields.Date(string='Date de mise au rebut')
    
    active = fields.Boolean(default=True, string='Actif')
    state = fields.Selection([
        ('operational', 'Opérationnel'),
        ('in_repair', 'En réparation'),
        ('standby', 'En attente'),
        ('scrapped', 'Mis au rebut')
    ], string='État', default='operational', tracking=True)
    
    notes = fields.Text(string='Notes')
    
    maintenance_ids = fields.One2many('maintenance.request', 'equipment_id', string='Demandes de maintenance')
    
    conformite_securite_ids = fields.One2many('maintenance.conformite.securite', 'equipment_id', string='Inspections de conformité et sécurité')

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('maintenance.equipment') or 'New'
        return super(MaintenanceEquipment, self).create(vals)
    
    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for equipment in self:
            equipment.maintenance_count = len(equipment.maintenance_ids)
            equipment.maintenance_open_count = len(equipment.maintenance_ids.filtered(lambda m: m.state != 'done'))

    @api.depends('period', 'maintenance_ids.close_date')
    def _compute_next_maintenance(self):
        for equipment in self:
            if equipment.period:
                last_maintenance = equipment.maintenance_ids.filtered(lambda m: m.state == 'done').sorted('close_date', reverse=True)[:1]
                if last_maintenance:
                    equipment.next_maintenance_date = last_maintenance.close_date + timedelta(days=equipment.period)
                else:
                    equipment.next_maintenance_date = fields.Date.today() + timedelta(days=equipment.period)
            else:
                equipment.next_maintenance_date = False

    @api.constrains('effective_date', 'scrap_date')
    def _check_dates(self):
        for equipment in self:
            if equipment.effective_date and equipment.scrap_date and equipment.effective_date > equipment.scrap_date:
                raise ValidationError("La date de mise en service doit être antérieure à la date de mise au rebut.")

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            'name': 'Maintenances',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'tree,form',
            'domain': [('equipment_id', '=', self.id)],
        }

    def action_start_maintenance(self):
        self.write({'state': 'in_repair'})

    def action_end_maintenance(self):
        self.write({'state': 'operational'})

    def action_scrap(self):
        self.write({'state': 'scrapped', 'scrap_date': fields.Date.today(), 'active': False})

    # Méthodes pour le rapport natif Odoo
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'maintenance.equipment',
            'docs': docs,
            'data': data,
        }

    # Vue de recherche pour le rapport
    @api.model
    def _get_search_domain(self, domain, context):
        if context.get('search_default_active'):
            domain = [('active', '=', True)] + domain
        return domain

    # Vue de liste pour le rapport
    @api.model
    def _get_report_tree_view(self):
        return """
            <tree string="Rapport Équipements" create="false" edit="false" delete="false">
                <field name="name"/>
                <field name="code"/>
                <field name="category_id"/>
                <field name="site_id"/>
                <field name="state"/>
                <field name="maintenance_count"/>
                <field name="next_maintenance_date"/>
            </tree>
        """

    # Action pour le rapport
    @api.model
    def action_equipment_report(self):
        return {
            'name': 'Rapport Équipements',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.equipment',
            'view_mode': 'tree,form,pivot,graph',
            'view_id': False,
            'domain': [],
            'context': {'search_default_active': 1},
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    Aucun équipement trouvé
                </p>
            """
        }
