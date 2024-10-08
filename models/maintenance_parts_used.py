# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import re
from datetime import timedelta

_logger = logging.getLogger(__name__)

class MaintenancePartsUsed(models.Model):
    _name = 'maintenance.parts.used'
    _description = 'Pièces Utilisées en Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Champs de base
    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='New', index=True)
    intervention_id = fields.Many2one('maintenance.request', string='Intervention', required=True, tracking=True, index=True)
    product_id = fields.Many2one('product.product', string='Pièce', required=True, tracking=True, index=True)
    quantity = fields.Float(string='Quantité', default=1.0, required=True, tracking=True)
    unit_price = fields.Float(string='Prix unitaire', related='product_id.list_price', readonly=True)
    total_price = fields.Float(string='Prix total', compute='_compute_total_price', store=True)
    usage_date = fields.Date(string='Date d\'utilisation', default=fields.Date.context_today, required=True)
    withdrawal_date = fields.Date(string='Date de retrait', required=True)
    technician_id = fields.Many2one('hr.employee', string='Technicien', required=True)
    
    # Nouveau champ pour la localisation du stock
    stock_location_id = fields.Many2one('stock.location', string='Emplacement du stock', required=True)
    
    # Nouveau champ pour le coût réel
    real_cost = fields.Float(string='Coût réel', help="Coût réel de la pièce au moment de l'utilisation")
    
    # Nouveau champ pour le numéro de série
    serial_number = fields.Char(string='Numéro de série', help="Numéro de série de la pièce")

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('reserved', 'Réservé'),
        ('used', 'Utilisée'),
        ('cancelled', 'Annulée')
    ], string='Statut', default='draft', tracking=True, index=True)
    notes = fields.Text(string='Notes')

    # Gestion du stock
    min_stock = fields.Float(string='Stock minimum', default=0.0, help="Le niveau minimum de stock pour ce produit.")
    current_stock = fields.Float(string='Stock actuel', compute='_compute_current_stock', store=True)
    stock_alert = fields.Boolean(string='Alerte de stock', compute='_compute_stock_alert', store=True)

    # Champ pour les prévisions de demande
    forecast_demand = fields.Float(string='Demande prévue', compute='_compute_forecast_demand', store=True)

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'La référence doit être unique.')
    ]

    @api.model
    def create(self, vals):
        """Crée un nouvel enregistrement de pièce utilisée."""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('maintenance.parts.used') or 'New'
        return super(MaintenancePartsUsed, self).create(vals)

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        """Calcule le prix total en fonction de la quantité et du prix unitaire."""
        for record in self:
            record.total_price = record.quantity * record.unit_price

    @api.depends('product_id', 'stock_location_id')
    def _compute_current_stock(self):
        """Calcule le stock actuel pour le produit dans l'emplacement de stock spécifié."""
        for record in self:
            if record.product_id and record.stock_location_id:
                record.current_stock = self.env['stock.quant']._get_available_quantity(
                    record.product_id, record.stock_location_id)
            else:
                record.current_stock = 0

    @api.depends('current_stock', 'min_stock')
    def _compute_stock_alert(self):
        """Détermine si une alerte de stock doit être déclenchée."""
        for record in self:
            record.stock_alert = record.current_stock < record.min_stock
            if record.stock_alert:
                record._send_stock_alert_email()

    @api.depends('product_id')
    def _compute_forecast_demand(self):
        """Calcule la demande prévue basée sur l'historique d'utilisation."""
        for record in self:
            # Récupérer l'historique d'utilisation des 6 derniers mois
            six_months_ago = fields.Date.today() - timedelta(days=180)
            usage_history = self.search([
                ('product_id', '=', record.product_id.id),
                ('usage_date', '>=', six_months_ago)
            ])
            
            # Calculer la moyenne d'utilisation mensuelle
            total_usage = sum(usage.quantity for usage in usage_history)
            monthly_average = total_usage / 6 if usage_history else 0
            
            # Définir la prévision comme 120% de la moyenne mensuelle
            record.forecast_demand = monthly_average * 1.2

    @api.constrains('quantity')
    def _check_quantity(self):
        """Vérifie que la quantité est valide et que le stock est suffisant."""
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_("La quantité doit être supérieure à zéro."))
            if record.quantity > record.current_stock:
                raise ValidationError(_("Stock insuffisant. Stock actuel : %s") % record.current_stock)

    def _send_stock_alert_email(self):
        """Envoie des alertes de stock par e-mail aux utilisateurs concernés."""
        template = self.env.ref('maintenance.mail_template_stock_alert')
        if template:
            valid_recipients, invalid_recipients, no_email_recipients = self._get_valid_recipients()
            if valid_recipients:
                for recipient in valid_recipients:
                    template.send_mail(self.id, force_send=True, email_values={'email_to': recipient.email})
            
            if invalid_recipients or no_email_recipients:
                self._send_invalid_recipients_notification(invalid_recipients, no_email_recipients)
        else:
            _logger.warning("Template d'alerte de stock non trouvé.")

    def _get_valid_recipients(self):
        """Filtre les destinataires avec des adresses e-mail valides."""
        all_recipients = self.env.ref('maintenance.group_parts_used_admin').users + \
                         self.env.ref('maintenance.group_parts_used_user').users
        valid_recipients = self.env['res.users']
        invalid_recipients = []
        no_email_recipients = []

        email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")
        for recipient in all_recipients:
            if not recipient.email:
                no_email_recipients.append(recipient.name)
            elif email_regex.match(recipient.email):
                valid_recipients |= recipient
            else:
                invalid_recipients.append(recipient.name)

        return valid_recipients, invalid_recipients, no_email_recipients

    def _send_invalid_recipients_notification(self, invalid_recipients, no_email_recipients):
        """Envoie une notification à l'utilisateur déclencheur concernant les destinataires non notifiés."""
        user = self.env.user
        message = _("""Des utilisateurs n'ont pas pu être notifiés :
        Sans adresse e-mail : %s
        Adresse e-mail invalide : %s""") % (', '.join(no_email_recipients), ', '.join(invalid_recipients))
        user.notify_warning(message, title=_("Notification d'alerte de stock incomplète"))

    def action_reserve(self):
        """Réserve la pièce pour l'intervention."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Cette pièce ne peut plus être réservée."))
        if self.quantity > self.current_stock:
            raise UserError(_("Stock insuffisant pour la réservation. Stock actuel : %s") % self.current_stock)
        
        self.write({'state': 'reserved'})
        self._update_stock(-self.quantity)  # Réduire le stock disponible

    def action_use(self):
        """Marque la pièce comme utilisée et met à jour le stock."""
        self.ensure_one()
        if self.state not in ['draft', 'reserved']:
            raise UserError(_("Cette pièce a déjà été utilisée ou annulée."))
        if self.intervention_id.state != 'in_progress':
            raise UserError(_("La pièce ne peut être utilisée que pour une intervention en cours."))
        if not self.withdrawal_date:
            raise UserError(_("Veuillez spécifier la date de retrait."))
        
        if self.state == 'draft':
            self._update_stock(-self.quantity)  # Réduire le stock si pas déjà réservé
        
        self.write({
            'state': 'used',
            'real_cost': self.product_id.standard_price  # Enregistrer le coût réel au moment de l'utilisation
        })
        self._send_allocation_notification()

    def action_cancel(self):
        """Annule l'utilisation de la pièce et remet à jour le stock si nécessaire."""
        self.ensure_one()
        if self.state in ['reserved', 'used']:
            self._update_stock(self.quantity)  # Remettre la quantité en stock
        self.write({'state': 'cancelled'})

    def action_draft(self):
        """Remet la pièce en état brouillon."""
        self.write({'state': 'draft'})

    def _update_stock(self, quantity_change):
        """Met à jour le stock du produit."""
        self.ensure_one()
        if self.product_id and self.stock_location_id:
            self.env['stock.quant']._update_available_quantity(
                self.product_id,
                self.stock_location_id,
                quantity_change
            )

    @api.constrains('intervention_id')
    def _check_intervention_state(self):
        """Vérifie que l'intervention associée est en cours."""
        for record in self:
            if record.intervention_id.state != 'in_progress':
                raise ValidationError(_("L'intervention sélectionnée doit être en cours de traitement."))

    def _send_allocation_notification(self):
        """Envoie une notification d'allocation de pièce aux personnes concernées."""
        template = self.env.ref('maintenance.mail_template_parts_allocation')
        if template:
            recipients = [self.env.user, self.intervention_id.team_leader_id] + \
                         self.env.ref('maintenance.group_parts_used_admin').users
            valid_recipients, invalid_recipients, no_email_recipients = self._filter_recipients(recipients)
            
            for recipient in valid_recipients:
                template.send_mail(self.id, force_send=True, email_values={'email_to': recipient.email})
            
            if invalid_recipients or no_email_recipients:
                self._send_invalid_recipients_notification(invalid_recipients, no_email_recipients)
        else:
            _logger.warning("Template de notification d'allocation non trouvé.")

    def _filter_recipients(self, recipients):
        """Filtre les destinataires en fonction de la validité de leur adresse e-mail."""
        valid_recipients = self.env['res.users']
        invalid_recipients = []
        no_email_recipients = []

        email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")
        for recipient in recipients:
            if not recipient.email:
                no_email_recipients.append(recipient.name)
            elif email_regex.match(recipient.email):
                valid_recipients |= recipient
            else:
                invalid_recipients.append(recipient.name)

        return valid_recipients, invalid_recipients, no_email_recipients

    @api.model
    def _cron_recompute_stock_alerts(self):
        """Tâche cron pour recalculer les alertes de stock."""
        parts = self.search([])
        parts._compute_stock_alert()

    @api.model
    def _cron_update_forecast_demand(self):
        """Tâche cron pour mettre à jour les prévisions de demande."""
        parts = self.search([])
        parts._compute_forecast_demand()

    # Méthodes pour les rapports et les vues

    @api.model
    def action_parts_used_report(self):
        """
        Cette fonction génère un rapport avec les vues tree, form, pivot et graph.
        """
        return {
            'name': _('Rapport Pièces Utilisées'),
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.parts.used',
            'view_mode': 'tree,form,pivot,graph',
            'view_id': False,
            'domain': [],
            'context': {
                'search_default_used': 1,
                'search_default_stock_alert': 1
            },
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    Aucune pièce utilisée trouvée
                </p>
            """
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prépare les données pour le rapport Qweb."""
        docs = self.browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'maintenance.parts.used',
            'docs': docs,
            'data': data,
        }

    
