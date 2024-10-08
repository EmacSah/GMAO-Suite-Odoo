# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ConformiteSecurite(models.Model):
    _name = 'maintenance.conformite.securite'
    _description = 'Conformité et Sécurité'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='New')
    category = fields.Selection([
        ('equipment', 'Équipement'),
        ('other', 'Autre')
    ], string='Catégorie d\'inspection', required=True, tracking=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Équipement')
    inspection_object = fields.Char(string='Objet d\'inspection')
    inspection_date = fields.Date(string='Date d\'inspection', required=True)
    inspector_id = fields.Many2one('res.partner', string='Inspecteur', required=True)
    
    result = fields.Selection([
        ('conforme', 'Conforme'),
        ('non_conforme', 'Non Conforme'),
        ('action_requise', 'Action Requise')
    ], string='Résultat', required=True)
    
    observations = fields.Text(string='Observations')
    next_inspection_date = fields.Date(string='Prochaine date d\'inspection')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé')
    ], string='Statut', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('maintenance.conformite.securite') or 'New'
        return super(ConformiteSecurite, self).create(vals)

    @api.onchange('category')
    def _onchange_category(self):
        if self.category == 'equipment':
            self.inspection_object = False
        else:
            self.equipment_id = False

    @api.constrains('category', 'equipment_id', 'inspection_object', 'result')
    def _check_category_fields(self):
        for record in self:
            if record.category == 'equipment' and not record.equipment_id:
                raise ValidationError("Un équipement doit être sélectionné pour la catégorie 'Équipement'.")
            elif record.category == 'other' and not record.inspection_object:
                raise ValidationError("L'objet d'inspection doit être spécifié pour la catégorie 'Autre'.")
            if record.category and not record.result:
                raise ValidationError("Le résultat doit être sélectionné une fois que la catégorie est remplie.")

    @api.onchange('result')
    def _onchange_result(self):
        if self.result:
            if not self.inspection_date:
                raise ValidationError("Veuillez d'abord remplir le champ 'Date d'inspection'.")
            if self.result == 'conforme':
                self.next_inspection_date = fields.Date.add(self.inspection_date, months=12)
            elif self.result == 'action_requise':
                self.next_inspection_date = fields.Date.add(self.inspection_date, months=1)
            else:
                self.next_inspection_date = False  # Pour le cas 'non_conforme' ou autre

    @api.constrains('inspection_date', 'next_inspection_date', 'inspector_id', 'category', 'result')
    def _check_inspection_dates(self):
        for record in self:
            if not record.inspector_id:
                raise ValidationError("L'inspecteur doit être sélectionné.")
            if not record.inspection_date:
                raise ValidationError("La date d'inspection doit être remplie.")
            if not record.category:
                raise ValidationError("La catégorie doit être remplie.")
            if not record.result:
                raise ValidationError("Le résultat doit être sélectionné.")
            if record.next_inspection_date and record.inspection_date > record.next_inspection_date:
                raise ValidationError("La prochaine date d'inspection doit être postérieure à la date d'inspection actuelle.")
