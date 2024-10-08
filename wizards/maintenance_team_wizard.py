# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MaintenanceTeamWizard(models.TransientModel):
    _name = 'maintenance.team.wizard'
    _description = 'Assistant Équipe de Maintenance'

    team_id = fields.Many2one('maintenance.team', string='Équipe', required=True)
    action_type = fields.Selection([
        ('plan', 'Planification'),
        ('assign', 'Affectation en masse')
    ], string='Type d\'action', required=True)
    
    # Champs pour la planification
    start_date = fields.Date(string='Date de début')
    end_date = fields.Date(string='Date de fin')
    
    # Champs pour l'affectation en masse
    member_ids = fields.Many2many('hr.employee', string='Membres à ajouter')

    @api.onchange('action_type')
    def _onchange_action_type(self):
        if self.action_type == 'plan':
            self.member_ids = False
        elif self.action_type == 'assign':
            self.start_date = False
            self.end_date = False

    def action_apply(self):
        self.ensure_one()
        if self.action_type == 'plan':
            if not self.start_date or not self.end_date:
                raise UserError(_("Veuillez spécifier les dates de début et de fin pour la planification."))
            self.team_id.write({
                'date_start': self.start_date,
                'date_end': self.end_date,
            })
            return {'type': 'ir.actions.act_window_close'}
        elif self.action_type == 'assign':
            if not self.member_ids:
                raise UserError(_("Veuillez sélectionner au moins un membre à ajouter à l'équipe."))
            self.team_id.write({
                'member_ids': [(4, member.id) for member in self.member_ids]
            })
            return {'type': 'ir.actions.act_window_close'}