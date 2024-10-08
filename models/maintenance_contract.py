# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class MaintenanceContract(models.Model):
    _name = 'maintenance.contract'
    _description = 'Contrat de Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    # Champ company_id avec valeur par défaut (la société de l'utilisateur qui crée le contrat)
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company, invisible=True)
    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default=lambda self: _('Nouveau'))
    partner_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True, index=True)
    type = fields.Selection([
        ('standard', 'Standard'),
        ('extended', 'Étendu'),
        ('premium', 'Premium')
    ], string='Type de contrat', required=True, default='standard', tracking=True)
    start_date = fields.Date(string='Date de début', required=True, tracking=True, index=True)
    end_date = fields.Date(string='Date de fin', required=True, tracking=True, index=True)
    total_amount = fields.Float(string='Montant total', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Devise', default=lambda self: self.env.company.currency_id)
    monthly_amount = fields.Float(string='Montant mensuel', compute='_compute_monthly_amount', store=True)
    remaining_days = fields.Integer(string='Jours restants', compute='_compute_remaining_days', store=True)
    equipment_ids = fields.Many2many('maintenance.equipment', string='Équipements couverts', tracking=True)
    note = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Actif'),
        ('expired', 'Expiré'),
        ('cancelled', 'Annulé')
    ], string='État', default='draft', tracking=True, index=True)
    responsible_id = fields.Many2one('res.users', string='Responsable du contrat', tracking=True)
    contract_documents = fields.Many2many('ir.attachment', string='Documents du contrat')
    previous_contract_id = fields.Many2one('maintenance.contract', string='Contrat précédent')
    alert_delay = fields.Selection([
        ('1month', '1 mois'),
        ('2months', '2 mois'),
        ('3months', '3 mois')
    ], string='Délai d\'alerte', default='1month', required=True)
    expiration_status = fields.Selection([
        ('normal', 'Normal'),
        ('attention', 'Attention'),
        ('alert', 'Alerte')
    ], string='Statut d\'expiration', compute='_compute_expiration_status', store=True)

    @api.model
    def create(self, vals):
        try:
            # Génère une référence automatique pour chaque nouveau contrat si elle n'est pas définie
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('maintenance.contract') or _('Nouveau')
            return super(MaintenanceContract, self).create(vals)
        except Exception as e:
            raise UserError(_("Erreur lors de la création du contrat : %s" % str(e)))

    @api.depends('total_amount', 'start_date', 'end_date')
    def _compute_monthly_amount(self):
        try:
            for contract in self:
                if contract.start_date and contract.end_date and contract.total_amount:
                    months = (contract.end_date.year - contract.start_date.year) * 12 + contract.end_date.month - contract.start_date.month
                    contract.monthly_amount = contract.total_amount / months if months > 0 else 0
                else:
                    contract.monthly_amount = 0
        except Exception as e:
            raise UserError(_("Erreur lors du calcul du montant mensuel : %s" % str(e)))

    @api.depends('end_date')
    def _compute_remaining_days(self):
        try:
            today = fields.Date.today()
            for contract in self:
                if contract.end_date:
                    contract.remaining_days = (contract.end_date - today).days
                else:
                    contract.remaining_days = 0
        except Exception as e:
            raise UserError(_("Erreur lors du calcul des jours restants : %s" % str(e)))

    @api.depends('end_date', 'alert_delay')
    def _compute_expiration_status(self):
        try:
            today = fields.Date.today()
            for contract in self:
                if contract.end_date:
                    days_to_expiration = (contract.end_date - today).days
                    if days_to_expiration <= 30:
                        contract.expiration_status = 'alert'
                    elif days_to_expiration <= 60:
                        contract.expiration_status = 'attention'
                    else:
                        contract.expiration_status = 'normal'
                else:
                    contract.expiration_status = 'normal'
        except Exception as e:
            raise UserError(_("Erreur lors de la mise à jour du statut d'expiration : %s" % str(e)))

    def action_activate(self):
        try:
            for contract in self:
                if contract.state == 'draft':
                    contract.state = 'active'
        except Exception as e:
            raise UserError(_("Erreur lors de l'activation du contrat : %s" % str(e)))

    def action_expire(self):
        try:
            for contract in self:
                if contract.state == 'active':
                    contract.state = 'expired'
        except Exception as e:
            raise UserError(_("Erreur lors de la mise à expiration du contrat : %s" % str(e)))

    def action_cancel(self):
        try:
            for contract in self:
                if contract.state in ['draft', 'active']:
                    contract.state = 'cancelled'
        except Exception as e:
            raise UserError(_("Erreur lors de l'annulation du contrat : %s" % str(e)))

    def action_reset_to_draft(self):
        try:
            for contract in self:
                if contract.state in ['cancelled', 'expired']:
                    contract.state = 'draft'
        except Exception as e:
            raise UserError(_("Erreur lors de la réinitialisation du contrat : %s" % str(e)))

    def action_renew(self):
        try:
            self.ensure_one()
            return {
                'name': _('Renouveler le contrat'),
                'type': 'ir.actions.act_window',
                'res_model': 'maintenance.contract.renew.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_contract_id': self.id}
            }
        except Exception as e:
            raise UserError(_("Erreur lors de la préparation du renouvellement du contrat : %s" % str(e)))

    @api.model
    def _cron_check_expiring_contracts(self):
        """
        Cron pour vérifier les contrats qui expirent dans les trois prochains mois.
        Envoie une notification à tous les utilisateurs définis dans le template d'email.
        """
        try:
            today = fields.Date.today()
            # Recherche des contrats actifs qui expirent dans les 3 mois
            contracts_to_notify = self.search([
                ('state', '=', 'active'),
                ('end_date', '>', today),
                ('end_date', '<=', today + relativedelta(months=3))
            ])

            for contract in contracts_to_notify:
                # Vérifie si une notification a déjà été envoyée cette semaine
                last_notification = self.env['mail.mail'].search([
                    ('model', '=', 'maintenance.contract'),
                    ('res_id', '=', contract.id),
                    ('date', '>=', fields.Datetime.now() - relativedelta(weeks=1))
                ], limit=1)
                if not last_notification:
                    # Envoie une notification à tous les utilisateurs définis dans le template de mail
                    contract._send_expiration_notification()
        except Exception as e:
            raise UserError(_("Erreur lors de la vérification des contrats expirants : %s" % str(e)))

    def _send_expiration_notification(self):
        """
        Envoie une notification d'expiration aux utilisateurs définis dans le modèle d'email.
        """
        try:
            template = self.env.ref('gmao_suite.email_template_contract_expiration')
            if template:
                template.send_mail(self.id, force_send=True)
        except Exception as e:
            raise UserError(_("Erreur lors de l'envoi de la notification d'expiration : %s" % str(e)))

    def print_contract(self):
        """
        Génère le rapport du contrat.
        """
        try:
            return self.env.ref('gmao_suite.action_report_maintenance_contract').report_action(self)
        except Exception as e:
            raise UserError(_("Erreur lors de l'impression du contrat : %s" % str(e)))
