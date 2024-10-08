# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import io
import csv
import logging

_logger = logging.getLogger(__name__)

class MaintenanceRequest(models.Model):
    _name = 'maintenance.request'
    _description = 'Demande d\'intervention de maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    # Champs de base
    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='New', index=True)
    request_number = fields.Char(string='Numéro de la demande', index=True)  # Renommé de request_id à request_number
    description = fields.Text(string='Description', required=True, translate=True)
    
    # Champs de date
    request_date = fields.Datetime(string='Date de demande', default=fields.Datetime.now, required=True, index=True)
    schedule_date = fields.Datetime(string='Date planifiée', index=True)
    start_date = fields.Datetime(string='Date de début', index=True)
    close_date = fields.Datetime(string='Date de clôture', index=True)
    
    # Champs relationnels
    equipment_id = fields.Many2one('maintenance.equipment', string='Équipement', required=True, index=True)
    category_id = fields.Many2one(related='equipment_id.category_id', string='Catégorie', store=True, index=True)
    site_id = fields.Many2one('maintenance.site', string='Site', compute='_compute_site', store=True, readonly=True, required=True, index=True)
    user_id = fields.Many2one('res.partner', string='Client', required=True, index=True)
    technician_id = fields.Many2one('hr.employee', string='Technicien assigné', index=True)
    team_id = fields.Many2one('maintenance.team', string='Équipe de maintenance', index=True)
    
    # Champs de sélection
    priority = fields.Selection([
        ('0', 'Très basse'),
        ('1', 'Basse'),
        ('2', 'Normale'),
        ('3', 'Haute'),
        ('4', 'Très haute')
    ], string='Priorité', default='2', index=True)
    
    maintenance_type = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Préventive'),
    ], string='Type de maintenance', default='corrective', required=True, index=True)
    
    state = fields.Selection([
        ('new', 'Nouvelle'),
        ('in_progress', 'En cours'),
        ('repaired', 'Réparée'),
        ('done', 'Terminée'),
        ('cancel', 'Annulée'),
    ], string='État', default='new', tracking=True, index=True)
    
    # Autres champs
    validator_id = fields.Many2one('res.users', string='Responsable de validation')
    parts_used_ids = fields.One2many('maintenance.parts.used', 'intervention_id', string='Pièces utilisées')
    duration = fields.Float(string='Durée (heures)', compute='_compute_duration', store=True)
    hourly_rate = fields.Float(string='Taux horaire', default=50.0)
    total_parts_cost = fields.Float(string='Coût total des pièces', compute='_compute_total_parts_cost', store=True)
    labor_cost = fields.Float(string='Coût de main d\'œuvre', compute='_compute_labor_cost', store=True)
    total_cost = fields.Float(string='Coût total', compute='_compute_total_cost', store=True)
    downtime = fields.Float(string='Temps d\'arrêt (heures)', compute='_compute_downtime', store=True)
    mttr = fields.Float(string='MTTR (Temps moyen de réparation)', compute='_compute_mttr', store=True)
    mtbf = fields.Float(string='MTBF (Temps moyen entre pannes)', compute='_compute_mtbf', store=True)
    contract_id = fields.Many2one('maintenance.contract', string='Contrat associé')
    devis = fields.Float(string='Devis')
    observations = fields.Text(string='Observations')
    system = fields.Selection([
        ('Plateforme Daisy', 'Plateforme Daisy'),
        ('Fichier Excel', 'Fichier Excel'),
        ('Contact Telephonique', 'Contact Téléphonique'),
        ('Mail', 'Mail'),
        ('Autre', 'Autre')
    ], string='Système', required=True, index=True)
    document_ids = fields.Many2many('ir.attachment', string='Documents attachés')
    company_id = fields.Many2one('res.company', string='Compagnie', required=True, default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True, string='Actif')

    # Nouveau champ pour stocker l'historique des changements d'état
    state_history_ids = fields.One2many('maintenance.request.state.history', 'request_id', string="Historique des états")

    @api.model
    def create(self, vals):
        # Génère un nouveau numéro de séquence pour le champ 'name' si sa valeur est 'New'
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('maintenance.request') or 'New'
        return super(MaintenanceRequest, self).create(vals)

    @api.depends('start_date', 'close_date')
    def _compute_duration(self):
        # Calcule la durée de l'intervention en heures
        for request in self:
            if request.start_date and request.close_date:
                request.duration = (request.close_date - request.start_date).total_seconds() / 3600
            else:
                request.duration = 0

    @api.depends('parts_used_ids.total_price')
    def _compute_total_parts_cost(self):
        # Calcule le coût total des pièces utilisées
        for request in self:
            request.total_parts_cost = sum(request.parts_used_ids.mapped('total_price'))

    @api.depends('duration', 'hourly_rate')
    def _compute_labor_cost(self):
        # Calcule le coût de la main d'œuvre
        for request in self:
            request.labor_cost = request.duration * request.hourly_rate

    @api.depends('total_parts_cost', 'labor_cost')
    def _compute_total_cost(self):
        # Calcule le coût total de l'intervention
        for request in self:
            request.total_cost = request.total_parts_cost + request.labor_cost

    @api.depends('schedule_date', 'close_date')
    def _compute_downtime(self):
        # Calcule le temps d'arrêt de l'équipement
        for request in self:
            if request.schedule_date and request.close_date:
                request.downtime = (request.close_date - request.schedule_date).total_seconds() / 3600
            else:
                request.downtime = 0

    @api.depends('duration', 'downtime')
    def _compute_mttr(self):
        # Calcule le Temps Moyen de Réparation (MTTR)
        for request in self:
            request.mttr = request.duration / (request.downtime or 1)

    @api.depends('equipment_id', 'request_date')
    def _compute_mtbf(self):
        # Calcule le Temps Moyen Entre Pannes (MTBF)
        for request in self:
            previous_request = self.env['maintenance.request'].search([
                ('equipment_id', '=', request.equipment_id.id),
                ('close_date', '<', request.request_date),
                ('state', '=', 'done')
            ], order='close_date desc', limit=1)
            
            if previous_request:
                time_between_failures = (request.request_date - previous_request.close_date).total_seconds() / 3600
                request.mtbf = time_between_failures
            else:
                request.mtbf = 0

    @api.constrains('schedule_date', 'close_date')
    def _check_dates(self):
        # Vérifie que la date de clôture est postérieure à la date planifiée
        for request in self:
            if request.schedule_date and request.close_date and request.schedule_date > request.close_date:
                raise ValidationError(_("La date de clôture doit être postérieure à la date planifiée pour la demande %s.") % request.name)

    def action_start_timer(self):
        self.ensure_one()
        if self.state == 'new':
            return self.action_start()
        return True

    def action_stop_timer(self):
        self.ensure_one()
        if self.state == 'in_progress':
            return self.action_done()
        return True
    
    @api.onchange('technician_id')
    def _onchange_technician(self):
        # Met à jour l'équipe de maintenance lorsque le technicien change
        if self.technician_id and self.technician_id.department_id:
            self.team_id = self.env['maintenance.team'].search([('department_id', '=', self.technician_id.department_id.id)], limit=1)

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        # Met à jour les informations liées à l'équipement lorsqu'il change
        if self.equipment_id:
            linked_contracts = self.env['maintenance.contract'].search([
                ('equipment_ids', 'in', self.equipment_id.id), 
                ('state', '=', 'active')
            ], limit=1)
            if linked_contracts:
                self.contract_id = linked_contracts.id
                self.devis = linked_contracts.monthly_amount
            else:
                self.contract_id = False
                self.devis = 0.0
                message = _("Le contrat lié à cet équipement n'est pas actif ou inexistant.")
                self.message_post(body=message)
            self.site_id = self.equipment_id.site_id

    def write(self, vals):
    # Surcharge de la méthode write pour gérer les changements d'état
        if 'state' in vals:
            for record in self:
                old_state = record.state
                new_state = vals['state']
                res = super(MaintenanceRequest, record).write(vals)
                record._create_state_history(old_state, new_state)
                record._send_state_change_notification(new_state)
        else:
            res = super(MaintenanceRequest, self).write(vals)
        return res

    def _create_state_history(self, old_state, new_state):
        # Crée un enregistrement dans l'historique des états
        self.ensure_one()
        self.env['maintenance.request.state.history'].create({
            'request_id': self.id,
            'old_state': old_state,
            'new_state': new_state,
            'change_date': fields.Datetime.now(),
            'user_id': self.env.user.id,
        })

    def _send_state_change_notification(self, new_state):
        self.ensure_one()
        template = self.env.ref('gmao_suite.email_template_maintenance_request_state_change', raise_if_not_found=False)
        if template:
            recipients = self._get_notification_recipients(new_state)
        if recipients:
            template.with_context(new_state=new_state).send_mail(self.id, email_values={'email_to': ', '.join(recipients)}, force_send=False)

def _get_notification_recipients(self, new_state):
    recipients = set()
    if new_state == 'repaired' and self.state == 'validate':
        if self.technician_id and self.technician_id.work_email:
            recipients.add(self.technician_id.work_email)
        if self.team_id:
            recipients.update(self.team_id.member_ids.mapped('work_email'))
    elif new_state in ['repaired', 'done']:
        if self.user_id and self.user_id.email:
            recipients.add(self.user_id.email)
        if self.technician_id and self.technician_id.work_email:
            recipients.add(self.technician_id.work_email)
        request_users = self.env.ref('gmao_suite.group_request_user').users
        request_admins = self.env.ref('gmao_suite.group_request_admin').users
        recipients.update(request_users.mapped('email') + request_admins.mapped('email'))
    
    # Filtrer les emails valides
    return list(filter(lambda x: x and '@' in x, recipients))

    
    
    
    def get_maintenance_kpis(self):
        return {
        'mttr': self.mttr,
        'mtbf': self.mtbf,
        'downtime': self.downtime,
        'total_cost': self.total_cost
    }
        
    def get_current_duration(self):
        if self.start_date and not self.close_date:
            return (fields.Datetime.now() - self.start_date).total_seconds() / 3600
    return self.duration
    
    
    
    def generate_detailed_report(self):
        # Génère un rapport détaillé de la demande de maintenance
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'gmao_suite.report_maintenance_request_detailed',
            'report_type': 'qweb-pdf',
            'data': {'request_id': self.id},
        }

    @api.constrains('contract_id')
    def _check_contract_state(self):
        for request in self:
            if request.contract_id and request.contract_id.state != 'active':
                message = _("Le contrat %s associé à cet équipement n'est pas actif.") % request.contract_id.name
                request.message_post(body=message)

    @api.constrains('devis')
    def _check_devis(self):
        for request in self:
            if request.devis <= 0 and not request.contract_id:
                raise ValidationError(_("Le devis doit être supérieur à 0 pour une intervention sans contrat."))

    @api.constrains('validator_id')
    def _check_validator_group(self):
        for record in self:
            if record.validator_id:
                if not (record.validator_id.has_group('gmao_suite.group_request_user') or 
                        record.validator_id.has_group('gmao_suite.group_request_admin') or
                        record.validator_id.has_group('gmao_suite.group_gmao_admin')):
                    raise ValidationError(_("Le responsable de validation doit appartenir à l'un des groupes suivants : Utilisateur de demande, Administrateur de demande ou Administrateur GMAO."))

    def action_validate(self):
        self.ensure_one()
        if self.state != 'new':
            raise UserError(_("Seules les interventions à l'état 'Nouvelle' peuvent être validées."))
        if not (self.env.user.has_group('gmao_suite.group_request_user') or self.env.user.has_group('gmao_suite.group_request_admin')):
            raise UserError(_("Vous n'avez pas les droits nécessaires pour valider cette intervention."))
        self.write({
            'state': 'to_validate',
            'validator_id': self.env.user.id
        })
        self.message_post(body=_("L'intervention %s a été validée par %s.") % (self.name, self.env.user.name))

    def action_start(self):
        self.ensure_one()
        if self.state != 'new':
            raise UserError(_("La demande doit être à l'état 'Nouvelle' pour être démarrée."))
        self.write({
            'state': 'in_progress',
            'start_date': fields.Datetime.now()
        })

    def action_repair(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("La demande doit être à l'état 'En cours' pour être marquée comme réparée."))
        self.write({'state': 'repaired'})

    def action_done(self):
        self.ensure_one()
        if self.state != 'repaired':
            raise UserError(_("La demande doit être à l'état 'Réparée' pour être terminée."))
        self.write({
            'state': 'done',
            'close_date': fields.Datetime.now()
        })
        reserved_parts = self.parts_used_ids.filtered(lambda p: p.state == 'reserved')
        if reserved_parts:
            reserved_parts.action_use()
        else:
            self.message_post(body=_("Aucune pièce réservée n'a été trouvée pour l'intervention %s.") % self.name)

    def action_cancel(self):
        self.ensure_one()
        if self.state in ['done', 'cancel']:
            raise UserError(_("Impossible d'annuler une demande terminée ou déjà annulée."))
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        self.ensure_one()
        if not self.env.user.has_group('gmao_suite.group_maintenance_manager'):
            raise UserError(_("Seuls les responsables de maintenance peuvent réinitialiser une demande."))
        if self.state != 'cancel':
            raise UserError(_("Seules les demandes annulées peuvent être réinitialisées."))
        self.write({'state': 'new'})

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} - {record.equipment_id.name} ({record.site_id.name})"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('equipment_id.name', operator, name), ('site_id.name', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': _('Copie de %s') % self.name,
            'state': 'new',
            'request_date': fields.Datetime.now(),
            'schedule_date': False,
            'start_date': False,
            'close_date': False,
        })
        return super(MaintenanceRequest, self).copy(default)

    def unlink(self):
        for request in self:
            if request.state not in ('new', 'cancel'):
                raise UserError(_("Vous ne pouvez supprimer que les demandes à l'état 'Nouvelle' ou 'Annulée'."))
        return super(MaintenanceRequest, self).unlink()

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.user.has_group('base.group_multi_company'):
            domain = domain + [('company_id', 'in', self.env.companies.ids)]
        return super(MaintenanceRequest, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)

    @api.model
    def get_graph_data(self, domain, groupby, measure, x_fields, y_fields):
        measures = [measure] if isinstance(measure, str) else measure[:3]
        x_fields = [x_fields] if isinstance(x_fields, str) else x_fields[:3]
        y_fields = [y_fields] if isinstance(y_fields, str) else y_fields[:3]

        fields = measures + x_fields + y_fields
        groupby = x_fields + y_fields

        data = self.read_group(
            domain,
            fields=fields,
            groupby=groupby,
            lazy=False
        )

        processed_data = []
        for item in data:
            processed_item = {
                'x': ' - '.join([str(item[x]) for x in x_fields]),
                'y': ' - '.join([str(item[y]) for y in y_fields]),
            }
            for measure in measures:
                processed_item[measure] = item[measure]
            processed_data.append(processed_item)

        return processed_data
        
        
    @api.model
    def get_table_data(self, domain, groupby, fields, limit=10, offset=0):
    # Récupérer le nombre total de groupes pour la pagination
        total_data = self.read_group(
            domain,
            fields=fields,
            groupby=groupby,
        lazy=False
    )
    total_count = len(total_data)

    # Appel à read_group avec limit et offset pour la pagination
    data = self.read_group(
        domain,
        fields=fields,
        groupby=groupby,
        offset=offset,
        limit=limit,
        lazy=False
    )

    processed_data = []
    for item in data:
        processed_item = {}
        for field in fields:
            processed_item[field] = item.get(field)
        for group in groupby:
            processed_item[group] = item.get(group)
        processed_data.append(processed_item)

    return {
        'data': processed_data,
        'total_count': total_count,
    }


    @api.model
    def export_graph_data(self, domain, groupby):
        data = self.read_group(
            domain,
            fields=['name', 'state', 'maintenance_type', 'duration', 'total_cost'],
            groupby=groupby,
            lazy=False
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # Écrire l'en-tête
        header = ['name', 'state', 'maintenance_type', 'duration', 'total_cost'] + groupby
        writer.writerow(header)

        # Écrire les données
        for item in data:
            row = [
                item['name'],
                item['state'],
                item['maintenance_type'],
                item['duration'],
                item['total_cost']
            ]
            for group in groupby:
                row.append(item[group])
            writer.writerow(row)

        return output.getvalue()

    @api.model
    def get_available_fields(self):
        return {
            field: self._fields[field].string
            for field in self._fields
            if self._fields[field].type in ['integer', 'float', 'monetary', 'many2one']
        }
        
    @api.model
    def _get_graph_data_bar(self):
        states = dict(self._fields['state'].selection)
        data = self.read_group([('state', '!=', False)], ['state'], ['state'])
        return {
            'labels': [states[item['state']] for item in data],
            'datasets': [{
                'label': _('Nombre de demandes'),
                'data': [item['state_count'] for item in data]
            }]
        }

    @api.model
    def _get_graph_data_pie(self):
        types = dict(self._fields['maintenance_type'].selection)
        data = self.read_group([('maintenance_type', '!=', False)], ['maintenance_type'], ['maintenance_type'])
        return {
            'labels': [types[item['maintenance_type']] for item in data],
            'datasets': [{
                'data': [item['maintenance_type_count'] for item in data]
            }]
        }

    @api.model
    def _get_graph_data_line(self):
        data = self.read_group(
            [('request_date', '!=', False)],
            ['request_date', '__count'],
            ['request_date:month']
        )
        return {
            'labels': [item['request_date:month'] for item in data],
            'datasets': [{
                'label': _('Demandes par mois'),
                'data': [item['__count'] for item in data]
            }]
        }

    @api.model
    def get_pivot_data(self):
        return self.read_group(
            [],
            ['state', 'maintenance_type', 'priority', 'site_id', 'equipment_id', 'technician_id',
                'total_cost:sum', 'duration:avg', 'downtime:sum', 'mttr:avg', 'mtbf:avg',
                'request_date:month', 'schedule_date:month', '__count'],
            ['state', 'maintenance_type', 'priority', 'site_id', 'equipment_id', 'technician_id',
                'request_date:month', 'schedule_date:month']
        )

    @api.model
    def _get_default_filters(self):
        return [
            ('request_date', '>=', fields.Date.to_string(fields.Date.today() - relativedelta(days=30))),
            ('state', '!=', 'cancel')
        ]

    @api.model
    def _get_default_group_by(self):
        return ['state', 'maintenance_type']

    def action_request_report(self):
        action = self.env.ref('gmao_suite.action_maintenance_request_report').read()[0]
        action.update({
            'context': {
                'search_default_done': 1,
                'search_default_requests': 1,
                'search_default_contract': 1,
                'group_by': ['system', 'state']
            },
        })
        return action

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'maintenance.request',
            'docs': docs,
            'data': data,
        }

    @api.model
    def _cron_archive_old_requests(self):
        archive_date = fields.Date.today() - relativedelta(years=1)
        old_requests = self.search([
            ('state', '=', 'done'),
            ('close_date', '<=', archive_date),
            ('active', '=', True)
        ])
        if old_requests:
            old_requests.write({'active': False})
            _logger.info(_("Archivage réussi de %s demandes de maintenance"), len(old_requests))

    @api.model
    def _cron_send_weekly_report(self):
        today = fields.Date.today()
        last_week = today - relativedelta(days=7)
        requests = self.search([
            ('request_date', '>=', last_week),
            ('request_date', '<=', today)
        ])
        if requests:
            template = self.env.ref('gmao_suite.email_template_weekly_report', raise_if_not_found=False)
            if template:
                template.with_context(requests=requests).send_mail(self.env.user.id, force_send=True)
                _logger.info(_("Rapport hebdomadaire envoyé avec succès."))
            else:
                _logger.error(_("Template de rapport hebdomadaire non trouvé."))

    @api.model
    def _cron_notify_late_requests(self):
        today = fields.Datetime.now()
        late_requests = self.search([
            ('schedule_date', '<', today),
            ('state', 'not in', ['done', 'cancel'])
        ])
        template = self.env.ref('gmao_suite.email_template_late_request_notification', raise_if_not_found=False)
        if template:
            for request in late_requests:
                template.send_mail(request.id, force_send=True)
            _logger.info(_("Notifications de retard envoyées pour %s demandes"), len(late_requests))
        else:
            _logger.error(_("Template de notification de retard non trouvé."))

    @api.model
    def _cron_update_mtbf(self):
        equipments = self.env['maintenance.equipment'].search([])
        for equipment in equipments:
            last_two_requests = self.search([
                ('equipment_id', '=', equipment.id),
                ('state', '=', 'done')
            ], order='close_date desc', limit=2)
            
            if len(last_two_requests) == 2:
                time_between_failures = (last_two_requests[0].request_date - last_two_requests[1].close_date).total_seconds() / 3600
                equipment.write({'mtbf': time_between_failures})

    def action_send_sms(self):
        self.ensure_one()
        template = self.env.ref('gmao_suite.sms_template_maintenance_request', raise_if_not_found=False)
        if template:
            template.send_sms(self.id, force_send=True)
        else:
            raise UserError(_("Modèle SMS non trouvé."))

    @api.model
    def create_from_equipment(self, equipment_id):
        equipment = self.env['maintenance.equipment'].browse(equipment_id)
        return self.create({
            'equipment_id': equipment.id,
            'user_id': self.env.user.partner_id.id,
            'description': _("Maintenance préventive pour %s") % equipment.name,
            'maintenance_type': 'preventive',
            'schedule_date': fields.Datetime.now(),
        })
        
class MaintenanceRequestStateHistory(models.Model):
    _name = 'maintenance.request.state.history'
    _description = 'Historique des états de la demande de maintenance'
    _order = 'change_date desc'

    request_id = fields.Many2one('maintenance.request', string='Demande de maintenance', required=True, ondelete='cascade')
    old_state = fields.Selection(related='request_id.state', string='Ancien état')
    new_state = fields.Selection(related='request_id.state', string='Nouvel état')
    change_date = fields.Datetime(string='Date de changement', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user)

    def name_get(self):
        return [(record.id, _("Changement d'état de %s à %s") % (record.old_state, record.new_state)) for record in self]