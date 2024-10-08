# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request

class MaintenanceTeamController(http.Controller):

    @http.route('/maintenance/team/chart_data', type='json', auth='user')
    def get_team_chart_data(self, team_id):
        team = request.env['maintenance.team'].browse(int(team_id))
        return {
            'labels': ['Taux de réussite', 'Charge de travail', 'Taux d\'occupation'],
            'datasets': [{
                'data': [team.success_rate, team.workload, team.occupation_rate],
                'backgroundColor': ['rgba(75, 192, 192, 0.6)', 'rgba(255, 159, 64, 0.6)', 'rgba(54, 162, 235, 0.6)'],
                'borderColor': ['rgba(75, 192, 192, 1)', 'rgba(255, 159, 64, 1)', 'rgba(54, 162, 235, 1)'],
                'borderWidth': 1
            }]
        }

    @http.route('/maintenance/team/update_members', type='json', auth='user')
    def update_team_members(self, team_id, member_ids):
        team = request.env['maintenance.team'].browse(int(team_id))
        team.write({
            'member_ids': [(6, 0, member_ids)]
        })
        return {'success': True}