from odoo import models, fields, api

class ResUsersGMAO(models.Model):
    _inherit = 'res.users'

    gmao_admin = fields.Boolean(string="Administrateur général GMAO", 
                                help="Donne tous les droits sur tous les modèles GMAO")

    parts_used_profile = fields.Selection([
        ('reader', 'Lecteur'),
        ('creator', 'Créateur'),
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ], string='Profil Pièces utilisées', default='reader')

    team_profile = fields.Selection([
        ('reader', 'Lecteur'),
        ('creator', 'Créateur'),
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ], string='Profil Équipe', default='reader')

    contract_profile = fields.Selection([
        ('reader', 'Lecteur'),
        ('creator', 'Créateur'),
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ], string='Profil Contrat', default='reader')

    efficacite_energetique_profile = fields.Selection([
        ('reader', 'Lecteur'),
        ('creator', 'Créateur'),
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ], string='Profil Efficacité énergétique', default='reader')

    equipment_profile = fields.Selection([
        ('reader', 'Lecteur'),
        ('creator', 'Créateur'),
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ], string='Profil Équipement', default='reader')

    site_profile = fields.Selection([
        ('reader', 'Lecteur'),
        ('creator', 'Créateur'),
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ], string='Profil Site', default='reader')

    equipment_category_profile = fields.Selection([
        ('reader', 'Lecteur'),
        ('creator', 'Créateur'),
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ], string='Profil Catégorie d\'équipement', default='reader')
    
    request_profile = fields.Selection([
    ('reader', 'Lecteur'),
    ('user', 'Utilisateur'),
    ('admin', 'Administrateur')
], string='Profil Demande de maintenance', default='reader')

    @api.onchange('gmao_admin')
    def _onchange_gmao_admin(self):
        if self.gmao_admin:
            self.parts_used_profile = 'admin'
            self.team_profile = 'admin'
            self.contract_profile = 'admin'
            self.efficacite_energetique_profile = 'admin'
            self.equipment_profile = 'admin'
            self.site_profile = 'admin'
            self.equipment_category_profile = 'admin'
        else:
            self.parts_used_profile = 'reader'
            self.team_profile = 'reader'
            self.contract_profile = 'reader'
            self.efficacite_energetique_profile = 'reader'
            self.equipment_profile = 'reader'
            self.site_profile = 'reader'
            self.equipment_category_profile = 'reader'

    @api.onchange('parts_used_profile', 'team_profile', 'contract_profile', 'efficacite_energetique_profile', 'equipment_profile', 'site_profile', 'equipment_category_profile')
    def _onchange_profiles(self):
        self._update_group_permissions()

    def _update_group_permissions(self):
        self._update_parts_used_permissions()
        self._update_team_permissions()
        self._update_contract_permissions()
        self._update_efficacite_energetique_permissions()
        self._update_equipment_permissions()
        self._update_site_permissions()
        self._update_equipment_category_permissions()
        self._update_request__permissions()

    def _update_parts_used_permissions(self):
        self._update_profile_permissions('parts_used', 'gmao_suite.group_parts_used_')

    def _update_team_permissions(self):
        self._update_profile_permissions('team', 'gmao_suite.group_maintenance_team_')

    def _update_contract_permissions(self):
        self._update_profile_permissions('contract', 'gmao_suite.group_maintenance_contract_')

    def _update_efficacite_energetique_permissions(self):
        self._update_profile_permissions('efficacite_energetique', 'gmao_suite.group_efficacite_energetique_')

    def _update_equipment_permissions(self):
        self._update_profile_permissions('equipment', 'gmao_suite.group_maintenance_equipment_')

    def _update_site_permissions(self):
        self._update_profile_permissions('site', 'gmao_suite.group_maintenance_site_')

    def _update_equipment_category_permissions(self):
        self._update_profile_permissions('equipment_category', 'gmao_suite.group_maintenance_equipment_category_')
        
    def _update_request_permissions(self):
        self._update_profile_permissions('request', 'gmao_suite.group_request_')

    def _update_profile_permissions(self, profile_field, group_prefix):
        profile = getattr(self, f'{profile_field}_profile')
        groups_to_update = ['reader', 'creator', 'user', 'admin']
        for group in groups_to_update:
            group_xml_id = f'{group_prefix}{group}'
            group_id = self.env.ref(group_xml_id)
            if profile == group:
                self.groups_id = [(4, group_id.id)]
            else:
                self.groups_id = [(3, group_id.id)]