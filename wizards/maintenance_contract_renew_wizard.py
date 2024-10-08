from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class MaintenanceContractRenewWizard(models.TransientModel):
    _name = 'maintenance.contract.renew.wizard'
    _description = "Assistant de renouvellement de contrat de maintenance"

    contract_id = fields.Many2one('maintenance.contract', string='Contrat à renouveler', required=True)
    new_start_date = fields.Date(string='Nouvelle date de début', required=True)
    new_end_date = fields.Date(string='Nouvelle date de fin', required=True)
    new_total_amount = fields.Float(string='Nouveau montant total', required=True)

    @api.model
    def default_get(self, fields):
        res = super(MaintenanceContractRenewWizard, self).default_get(fields)
        contract_id = self.env.context.get('active_id')
        if contract_id:
            try:
                contract = self.env['maintenance.contract'].browse(contract_id)
                if not contract:
                    raise UserError(_("Le contrat de maintenance n'a pas été trouvé."))
                
                # Vérification des dates
                if not contract.end_date:
                    raise UserError(_("La date de fin du contrat actuel est manquante. Impossible de calculer les nouvelles dates."))

                res.update({
                    'contract_id': contract.id,
                    'new_start_date': contract.end_date + relativedelta(days=1),
                    'new_end_date': contract.end_date + relativedelta(years=1),
                    'new_total_amount': contract.total_amount,
                })
            except Exception as e:
                raise UserError(_("Erreur lors du chargement des valeurs par défaut : %s" % str(e)))
        return res

    def action_renew_contract(self):
        self.ensure_one()

        # Vérification des champs avant de procéder
        if not self.new_start_date or not self.new_end_date or not self.new_total_amount:
            raise UserError(_("Veuillez compléter tous les champs requis avant de renouveler le contrat."))

        try:
            # Crée un nouveau contrat en tant que brouillon
            new_contract = self.contract_id.copy({
                'name': _("%s (Renouvelé)" % self.contract_id.name),
                'start_date': self.new_start_date,
                'end_date': self.new_end_date,
                'total_amount': self.new_total_amount,
                'state': 'draft',
                'previous_contract_id': self.contract_id.id,
            })

            # Expire l'ancien contrat
            self.contract_id.write({'state': 'expired'})
            self._send_renewal_notification(new_contract)

            # Retourne une vue du nouveau contrat
            return {
                'name': _('Contrat renouvelé'),
                'type': 'ir.actions.act_window',
                'res_model': 'maintenance.contract',
                'res_id': new_contract.id,
                'view_mode': 'form',
                'target': 'current',
            }

        except Exception as e:
            raise UserError(_("Erreur lors du renouvellement du contrat : %s" % str(e)))

    def _send_renewal_notification(self, new_contract):
        try:
            # Récupération du template d'email pour le renouvellement de contrat
            template = self.env.ref('gmao_suite.email_template_contract_renewal')
            if template:
                template.send_mail(new_contract.id, force_send=True)
            else:
                raise UserError(_("Le modèle d'email de renouvellement n'a pas été trouvé."))
        except Exception as e:
            raise UserError(_("Erreur lors de l'envoi de la notification de renouvellement : %s" % str(e)))
