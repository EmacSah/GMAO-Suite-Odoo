# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import json
import logging

_logger = logging.getLogger(__name__)

class EfficaciteEnergetique(models.Model):
    _name = 'maintenance.efficacite.energetique'
    _description = 'Efficacité Énergétique'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='New')
    equipment_id = fields.Many2one('maintenance.equipment', string='Équipement', required=True, tracking=True, index=True)
    measurement_date = fields.Date(string='Date de mesure', required=True, tracking=True, index=True)
    evaluator_id = fields.Many2one('res.partner', string='Évaluateur', required=True, tracking=True)
    
    energy_consumption = fields.Float(string='Consommation énergétique (kWh)', required=True, tracking=True)
    previous_consumption = fields.Float(string='Consommation précédente (kWh)', readonly=True)
    consumption_variation = fields.Float(string='Variation de consommation (%)', compute='_compute_consumption_variation', store=True)
    energy_savings = fields.Float(string='Économie d\'énergie (kWh)', compute='_compute_energy_savings', store=True)
    
    efficiency_rating = fields.Selection([
        ('a', 'A - Excellent'),
        ('b', 'B - Très bon'),
        ('c', 'C - Bon'),
        ('d', 'D - Moyen'),
        ('e', 'E - Médiocre'),
        ('f', 'F - Très médiocre')
    ], string='Note d\'efficacité', required=True, tracking=True)
    
    observations = fields.Text(string='Observations')
    actions_recommended = fields.Text(string='Actions recommandées')
    next_evaluation_date = fields.Date(string='Prochaine date d\'évaluation')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé')
    ], string='Statut', default='draft', tracking=True)

    consumption_chart = fields.Text(compute='_compute_consumption_chart', string='Graphique de Consommation')
    active = fields.Boolean(default=True, string='Actif')

    @api.model
    def create(self, vals):
        """ Crée un nouvel enregistrement d'évaluation d'efficacité énergétique avec validation de l'équipement. """
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('maintenance.efficacite.energetique') or 'New'
        
        equipment = self.env['maintenance.equipment'].browse(vals.get('equipment_id'))
        if equipment.state != 'operational':
            raise UserError(_("Il n'est pas possible d'évaluer un équipement qui n'est pas opérationnel. Veuillez choisir un équipement en service."))
        
        return super(EfficaciteEnergetique, self).create(vals)

    @api.depends('energy_consumption', 'previous_consumption')
    def _compute_consumption_variation(self):
        """ Calcule la variation de consommation en pourcentage. """
        for record in self:
            if record.previous_consumption:
                record.consumption_variation = ((record.energy_consumption - record.previous_consumption) / record.previous_consumption) * 100
            else:
                record.consumption_variation = 0

    @api.depends('energy_consumption', 'previous_consumption')
    def _compute_energy_savings(self):
        """ Calcule les économies d'énergie en kWh. """
        for record in self:
            if record.previous_consumption:
                savings = record.previous_consumption - record.energy_consumption
                record.energy_savings = savings if savings > 0 else 0
            else:
                record.energy_savings = 0

    @api.depends('energy_consumption', 'previous_consumption', 'energy_savings')
    def _compute_consumption_chart(self):
        """ Génère les données du graphique de consommation en format JSON ou retourne un message s'il n'y a pas de données. """
        for record in self:
            _logger.debug(_("Computing chart for record %s"), record.id)
            if any([record.energy_consumption, record.previous_consumption, record.energy_savings]):
                chart_data = {
                    'consumptions': [record.previous_consumption, record.energy_consumption],
                    'labels': [_('Consommation précédente'), _('Consommation actuelle')],
                    'savings': record.energy_savings
                }
                record.consumption_chart = json.dumps(chart_data)
                _logger.debug(_("Chart data: %s"), record.consumption_chart)
            else:
                record.consumption_chart = _("Aucune donnée à afficher")
                _logger.debug(_("No data available for chart"))

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        """ Met à jour la consommation précédente en fonction de l'équipement sélectionné. """
        if self.equipment_id:
            if self.equipment_id.state != 'operational':
                raise UserError(_("Il n'est pas possible d'évaluer un équipement qui n'est pas opérationnel. Veuillez choisir un équipement en service."))
            
            last_evaluation = self.search([
                ('equipment_id', '=', self.equipment_id.id),
                ('state', '=', 'done')
            ], order='measurement_date desc', limit=1)
            if last_evaluation:
                self.previous_consumption = last_evaluation.energy_consumption

    def action_confirm(self):
        """ Confirme l'évaluation si l'équipement est opérationnel. """
        for record in self:
            if record.equipment_id.state != 'operational':
                raise UserError(_("Il n'est pas possible de confirmer l'évaluation d'un équipement qui n'est pas opérationnel."))
            record.state = 'confirmed'

    def action_done(self):
        """ Termine l'évaluation si l'équipement est opérationnel. """
        for record in self:
            if record.equipment_id.state != 'operational':
                raise UserError(_("Il n'est pas possible de terminer l'évaluation d'un équipement qui n'est pas opérationnel."))
            record.state = 'done'

    def action_cancel(self):
        """ Annule l'évaluation. """
        for record in self:
            record.state = 'cancelled'

    def action_draft(self):
        """ Remet l'évaluation à l'état de brouillon. """
        for record in self:
            record.state = 'draft'

    @api.constrains('measurement_date', 'next_evaluation_date')
    def _check_evaluation_dates(self):
        """ Valide que la prochaine évaluation est postérieure à la date de mesure. """
        for record in self:
            if record.next_evaluation_date and record.measurement_date > record.next_evaluation_date:
                raise UserError(_("Erreur de date : La prochaine date d'évaluation (%s) doit être postérieure à la date de mesure actuelle (%s). Veuillez corriger les dates.") % (record.next_evaluation_date, record.measurement_date))

    @api.onchange('efficiency_rating')
    def _onchange_efficiency_rating(self):
        """ Modifie la prochaine date d'évaluation en fonction de la note d'efficacité. """
        if self.efficiency_rating and self.measurement_date:
            if self.efficiency_rating in ['a', 'b', 'c']:
                self.next_evaluation_date = self.measurement_date + timedelta(days=365)
            elif self.efficiency_rating in ['d', 'e']:
                self.next_evaluation_date = self.measurement_date + timedelta(days=180)
            elif self.efficiency_rating == 'f':
                self.next_evaluation_date = self.measurement_date + timedelta(days=90)

    @api.constrains('energy_consumption', 'previous_consumption')
    def _check_energy_values(self):
        """ Valide que les consommations d'énergie sont supérieures à zéro. """
        for record in self:
            if record.energy_consumption <= 0:
                raise UserError(_("La consommation énergétique doit être supérieure à zéro."))
            if record.previous_consumption and record.previous_consumption <= 0:
                raise UserError(_("La consommation précédente doit être supérieure à zéro."))

    @api.constrains('measurement_date')
    def _check_measurement_date(self):
        """ Valide que la date de mesure ne soit pas dans le futur. """
        for record in self:
            if record.measurement_date > fields.Date.today():
                raise UserError(_("Erreur de date : La date de mesure (%s) ne peut pas être dans le futur. Veuillez sélectionner une date valide.") % record.measurement_date)

    def get_historical_data(self):
        """ Récupère les données historiques de consommation pour l'équipement sélectionné. """
        self.ensure_one()
        domain = [
            ('equipment_id', '=', self.equipment_id.id),
            ('measurement_date', '<=', self.measurement_date),
            ('state', '=', 'done')
        ]
        historical_data = self.search_read(domain, ['measurement_date', 'energy_consumption', 'energy_savings'], order='measurement_date asc')
        
        return {
            'labels': [data['measurement_date'] for data in historical_data],
            'consumptions': [data['energy_consumption'] for data in historical_data],
            'savings': [data['energy_savings'] for data in historical_data]
        }

    def archive_old_evaluations(self):
        """ Archive les évaluations terminées datant de plus d'un an. """
        one_year_ago = fields.Date.today() - timedelta(days=365)
        old_evaluations = self.search([
            ('state', '=', 'done'),
            ('measurement_date', '<', one_year_ago)
        ])
        old_evaluations.write({'active': False})
        _logger.info(_("%d old evaluations have been archived."), len(old_evaluations))