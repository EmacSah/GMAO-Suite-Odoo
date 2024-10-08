# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MaintenanceSite(models.Model):
    _name = 'maintenance.site'
    _description = 'Site de maintenance'
    _rec_name = 'name'

    name = fields.Char(string='Nom du site', required=True)
    code = fields.Char(string='Code du site', required=True)
    address = fields.Char(string='Adresse')
    city_id = fields.Many2one('res.city', string='Ville', required=True)
    state_id = fields.Many2one('res.country.state', string='État/Région', related='city_id.state_id', store=True)
    country_id = fields.Many2one('res.country', string='Pays', related='city_id.country_id', store=True)
    
    latitude = fields.Float(string='Latitude', digits=(10, 8))
    longitude = fields.Float(string='Longitude', digits=(11, 8))
    distance_from_office = fields.Float(string='Distance des bureaux (km)', digits=(10, 2))

    active = fields.Boolean(default=True, string='Actif')

    @api.depends('name', 'code', 'city_id')
    def name_get(self):
        result = []
        for site in self:
            name = f"[{site.code}] {site.name} ({site.city_id.name})"
            result.append((site.id, name))
        return result

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for site in self:
            if site.latitude and (site.latitude < -90 or site.latitude > 90):
                raise ValidationError("La latitude doit être comprise entre -90 et 90.")
            if site.longitude and (site.longitude < -180 or site.longitude > 180):
                raise ValidationError("La longitude doit être comprise entre -180 et 180.")

    def compute_distance(self):
        # Cette méthode devrait être implémentée pour calculer la distance
        # entre le site et les bureaux principaux.
        # Vous pouvez utiliser une API de géolocalisation ou une formule de calcul de distance.
        pass