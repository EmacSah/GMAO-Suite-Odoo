# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class MaintenanceTeam(models.Model):
    _name = 'maintenance.team'
    _description = 'Équipe de Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Champs de base
    name = fields.Char(string='Nom de l\'équipe', required=True, tracking=True, index=True)
    active = fields.Boolean(default=True, tracking=True, index=True)
    color = fields.Integer(string='Couleur')
    leader_id = fields.Many2one('hr.employee', string='Chef d\'équipe', required=True, tracking=True, index=True)
    member_ids = fields.Many2many('hr.employee', string='Membres de l\'équipe', required=True, index=True)

    request_ids = fields.One2many('maintenance.request', 'team_id', string='Demandes d\'intervention')

    notes = fields.Text(string='Notes')

    # Champs calculés
    total_members = fields.Integer(string='Nombre total de membres', compute='_compute_total_members', store=True)
    open_requests_count = fields.Integer(string='Demandes ouvertes', compute='_compute_open_requests_count')
    success_rate = fields.Float(string='Taux de réussite (%)', compute='_compute_success_rate', store=True)
    workload = fields.Integer(string='Charge de travail', compute='_compute_workload', store=True)
    occupation_rate = fields.Float(string='Taux d\'occupation (%)', compute='_compute_occupation_rate', store=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé'),
    ], string='État', default='draft', tracking=True, index=True)

    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)

    date_start = fields.Date(string='Date de début', default=fields.Date.context_today)
    date_end = fields.Date(string='Date de fin', default=fields.Date.context_today)

    @api.depends('member_ids')
    def _compute_total_members(self):
        """Calcule le nombre total de membres dans l'équipe."""
        for team in self:
            team.total_members = len(team.member_ids)

    @api.depends('request_ids.state')
    def _compute_open_requests_count(self):
        """Calcule le nombre de demandes d'intervention ouvertes pour l'équipe."""
        for team in self:
            team.open_requests_count = self.env['maintenance.request'].search_count([
                ('team_id', '=', team.id),
                ('state', 'not in', ['done', 'cancel'])
            ])

    @api.depends('request_ids.state', 'request_ids.close_date')
    def _compute_success_rate(self):
        """Calcule le taux de réussite de l'équipe basé sur les interventions terminées."""
        for team in self:
            domain = [
                ('team_id', '=', team.id),
                ('close_date', '>=', team.date_start),
                ('close_date', '<=', team.date_end),
            ]
            total_requests = self.env['maintenance.request'].search_count(domain)
            successful_requests = self.env['maintenance.request'].search_count(domain + [('state', '=', 'done')])
            team.success_rate = (successful_requests / total_requests * 100) if total_requests else 0

    @api.depends('request_ids.state', 'date_start', 'date_end')
    def _compute_workload(self):
        """Calcule la charge de travail de l'équipe basée sur les demandes en cours."""
        for team in self:
            domain = [
                ('team_id', '=', team.id),
                ('create_date', '>=', team.date_start),
                ('create_date', '<=', team.date_end),
                ('state', 'not in', ['done', 'cancel']),
            ]
            team.workload = self.env['maintenance.request'].search_count(domain)

    @api.depends('member_ids', 'request_ids.state', 'request_ids.duration')
    def _compute_occupation_rate(self):
        """Calcule le taux d'occupation de l'équipe."""
        for team in self:
            try:
                total_capacity = len(team.member_ids) * 8 * 5  # 8 heures par jour, 5 jours par semaine
                occupied_hours = sum(team.request_ids.filtered(lambda r: r.state == 'in_progress').mapped('duration'))
                team.occupation_rate = (occupied_hours / total_capacity * 100) if total_capacity else 0
            except ZeroDivisionError:
                team.occupation_rate = 0
                team.message_post(body=_("Erreur dans le calcul du taux d'occupation : l'équipe n'a pas de membres."))

    @api.constrains('member_ids', 'request_ids')
    def _check_member_availability(self):
        """Vérifie la disponibilité des membres de l'équipe."""
        for team in self:
            for member in team.member_ids:
                conflicting_requests = self.env['maintenance.request'].search([
                    ('technician_id', '=', member.id),
                    ('state', 'in', ['new', 'in_progress']),
                    ('team_id', '!=', team.id)
                ])
                if conflicting_requests:
                    raise UserError(_("Le membre %s est déjà assigné à une autre tâche dans une équipe différente.") % member.name)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Vérifie que la date de fin est postérieure à la date de début."""
        for team in self:
            if team.date_start and team.date_end and team.date_start > team.date_end:
                raise ValidationError(_("La date de fin doit être postérieure à la date de début."))

    def action_validate_team(self):
        """Valide l'équipe si toutes les conditions sont remplies."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("L'équipe doit être à l'état brouillon pour être validée."))
        if not self.member_ids:
            raise UserError(_("Vous ne pouvez pas valider une équipe sans membres."))
        if not self.leader_id:
            raise UserError(_("Vous devez désigner un chef d'équipe avant de valider l'équipe."))
        self.state = 'validated'
        self._send_team_composition_notification()

    def _send_team_composition_notification(self):
        """Envoie une notification de la composition de l'équipe."""
        self.ensure_one()
        template = self.env.ref('gmao_suite.email_template_team_composition', raise_if_not_found=False)
        if not template:
            _logger.warning(_("Le template d'email pour la composition d'équipe n'a pas été trouvé."))
            return

        team_admin_group = self.env.ref('gmao_suite.group_maintenance_team_admin')
        team_user_group = self.env.ref('gmao_suite.group_maintenance_team_user')
        recipients = team_admin_group.users | team_user_group.users | self.create_uid | self.leader_id.user_id
        recipient_partners = recipients.mapped('partner_id')

        try:
            template.send_mail(self.id, force_send=True, email_values={'recipient_ids': [(6, 0, recipient_partners.ids)]})
        except Exception as e:
            _logger.error(_("Erreur lors de l'envoi de l'e-mail de composition d'équipe : %s"), str(e))

        members_without_email = self.member_ids.filtered(lambda m: not m.work_email)
        if members_without_email:
            message = _("Les membres suivants n'ont pas d'adresse e-mail : %s") % ', '.join(members_without_email.mapped('name'))
            self.message_post(body=message, message_type='comment', subtype='mail.mt_note')

    def action_mark_as_done(self):
        self.ensure_one()
        for request in self.request_ids.filtered(lambda r: r.state != 'done'):
            request.write({'state': 'done'})
        self._send_team_release_notification()

    def _send_team_release_notification(self):
        self.ensure_one()
        template = self.env.ref('gmao_suite.email_template_team_release', raise_if_not_found=False)
        if not template:
            _logger.warning(_("Le template d'email pour la libération d'équipe n'a pas été trouvé."))
            return

        team_admin_group = self.env.ref('gmao_suite.group_maintenance_team_admin')
        team_user_group = self.env.ref('gmao_suite.group_maintenance_team_user')
        recipients = team_admin_group.users | team_user_group.users | self.create_uid | self.leader_id.user_id
        recipient_partners = recipients.mapped('partner_id')

        try:
            template.send_mail(self.id, force_send=True, email_values={'recipient_ids': [(6, 0, recipient_partners.ids)]})
        except Exception as e:
            _logger.error(_("Erreur lors de l'envoi de l'e-mail de libération d'équipe : %s"), str(e))

    @api.model
    def _cron_check_team_availability(self):
        teams = self.search([('state', '=', 'validated')])
        for team in teams:
            if all(request.state == 'done' for request in team.request_ids):
                team.action_mark_as_done()

    @api.model
    def _cron_update_occupation_rate(self):
        teams = self.search([])
        for team in teams:
            try:
                team._compute_occupation_rate()
            except Exception as e:
                team.message_post(body=_("Erreur lors de la mise à jour du taux d'occupation : %s") % str(e))

    def name_get(self):
        result = []
        for team in self:
            name = _("%s (%s membres)") % (team.name, team.total_members)
            result.append((team.id, name))
        return result

    @api.model
    def create(self, vals):
        try:
            team = super(MaintenanceTeam, self).create(vals)
            team.message_subscribe(partner_ids=team.member_ids.mapped('user_id.partner_id').ids)
            return team
        except Exception as e:
            raise UserError(_("Erreur lors de la création de l'équipe : %s") % str(e))

    def write(self, vals):
        try:
            res = super(MaintenanceTeam, self).write(vals)
            if 'member_ids' in vals:
                self.message_subscribe(partner_ids=self.member_ids.mapped('user_id.partner_id').ids)
            return res
        except Exception as e:
            raise UserError(_("Erreur lors de la modification de l'équipe : %s") % str(e))

    
    def _unlink_except_open_requests(self):
        for team in self:
            if team.request_ids.filtered(lambda r: r.state not in ['done', 'cancel']):
                raise UserError(_("Vous ne pouvez pas supprimer l'équipe %s car elle a des demandes d'intervention en cours.") % team.name)
        return super(MaintenanceTeam, self).unlink()

    def toggle_active(self):
        for team in self:
            if team.active and team.request_ids.filtered(lambda r: r.state not in ['done', 'cancel']):
                raise UserError(_("Vous ne pouvez pas archiver l'équipe %s car elle a des demandes d'intervention en cours.") % team.name)
        return super(MaintenanceTeam, self).toggle_active()

    def action_view_last_month(self):
        end_date = fields.Date.context_today(self)
        start_date = end_date - relativedelta(months=1)
        self.write({'date_start': start_date, 'date_end': end_date})
        return self.action_view_maintenance_team()

    def action_view_last_year(self):
        end_date = fields.Date.context_today(self)
        start_date = end_date - relativedelta(years=1)
        self.write({'date_start': start_date, 'date_end': end_date})
        return self.action_view_maintenance_team()

    def action_view_maintenance_team(self):
        return {
            'name': _('Équipes de Maintenance'),
            'view_mode': 'graph,pivot',
            'res_model': 'maintenance.team',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', self.ids)],
        }

    def generate_performance_chart(self):
        plt.figure(figsize=(8, 4))
        labels = ['Taux de réussite', 'Charge de travail', 'Taux d\'occupation']
        values = [self.success_rate, self.workload, self.occupation_rate]
        colors = ['#4BC0C0', '#FF6384', '#36A2EB']

        plt.bar(labels, values, color=colors)
        plt.title('Performance de l\'équipe')
        plt.ylim(0, 100)
        plt.ylabel('Pourcentage')

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()


