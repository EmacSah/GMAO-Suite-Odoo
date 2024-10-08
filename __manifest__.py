# __manifest__.py

{
    'name': 'GMAO Suite',
    'version': '1.1',
    'category': 'Maintenance',
    'summary': 'Gestion de Maintenance Assistée par Ordinateur',
    'description': """
        Module complet de Gestion de Maintenance Assistée par Ordinateur (GMAO) pour Odoo.
        Fonctionnalités :
        - Gestion des demandes d'intervention
        - Suivi des interventions
        - Gestion des équipements et des pièces
        - Planification de la maintenance préventive
        - Gestion des contrats et facturation
        - Analyse et reporting
    """,
    'author': '2WT',
    'website': 'https://www.2wteg.com',
    'depends': ['base', 'base_address_city', 'mail', 'stock', 'hr', 'web'],
    
    'data': [
        
        
		'security/maintenance_security.xml',
        'data/maintenance_sequence.xml',
        'data/mail_template_data.xml',
        'data/maintenance_cron.xml',
        'data/paperformat_data.xml',
        #'data/sms_cron.xml',
        #'views/sms_gateway_config_views.xml',
        #'views/sms_recipient_views.xml',
        
        #'views/sms_notification_views.xml',
        'views/maintenance_site_views.xml',
		'views/maintenance_equipment_category_views.xml',
        'views/maintenance_equipment_views.xml',
        'reports/maintenance_request_report.xml',
		'reports/maintenance_request_analysis_report.xml',
		'reports/maintenance_team_report.xml',
		'reports/maintenance_team_planning_report.xml',
        'reports/maintenance_parts_used_report.xml',
        'reports/report_maintenance_contract.xml',
        'views/maintenance_team_views.xml',
        'views/maintenance_parts_used_views.xml',
        'views/maintenance_request_views.xml',
        #'views/suivi_maintenance_views.xml',
        #'views/maintenance_preventive_views.xml',
        #'views/maintenance_delay_cause_views.xml',
		'views/maintenance_contract_views.xml',
        'views/conformite_securite_views.xml',
        'views/efficacite_energetique_views.xml',
		'views/maintenance_request_graph.xml',
		
		
		
        #'views/satisfaction_client_views.xml',
        #'views/formation_competence_views.xml',
        #'report/maintenance_reports.xml',
        #'report/maintenance_request_report.xml',
        #'report/suivi_maintenance_report.xml',
        #'report/maintenance_equipment_report.xml',
        
        #'report/maintenance_preventive_report.xml',
        #'report/performance_technicien_report.xml',
        #'report/analyse_predictive_report.xml',
        #'report/conformite_securite_report.xml',
        #'report/efficacite_energetique_report.xml',
        #'report/satisfaction_client_report.xml',
        #'report/analyse_comparative_report.xml',
        #'report/cycle_vie_equipement_report.xml',
        #'report/gestion_fournisseurs_report.xml',
        #'report/formation_competences_report.xml',
        #'wizard/maintenance_planning_wizard_views.xml',
        #'wizard/maintenance_report_wizard_views.xml',
		
		'wizards/maintenance_graph_wizard_views.xml',
        'wizards/maintenance_contract_renew_wizard_views.xml',
        'wizards/maintenance_team_wizard_views.xml',
        'wizards/maintenance_parts_used_report_wizard_views.xml',
		
        'views/res_users_views.xml',
		
		'security/ir.model.access.csv',
        'views/maintenance_menu_views.xml',
    ],
	
		
	'qweb': [
        
		'static/src/xml/maintenance_team_chart_template.xml',
        'static/src/xml/maintenance_parts_used_report_template.xml',
        'static/src/xml/maintenance_request_templates.xml',
        'static/src/xml/maintenance_request_graph_templates.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
		
		    #css files 
            
            'gmao_suite/static/src/css/consumption_chart.css',
			'gmao_suite/static/src/css/maintenance_request_widgets.css',
			'gmao_suite/static/src/css/maintenance_request_graph.css',
            'gmao_suite/static/src/css/maintenance_team_chart.css',
			'gmao_suite/static/src/css/maintenance_parts_used.css',
			'gmao_suite/static/src/css/maintenance_parts_used_report.css',
			
			#JS files
			'gmao_suite/static/src/js/consumption_chart_widget.js',
			'gmao_suite/static/src/css/maintenance_request_widgets.js',
			'gmao_suite/static/src/css/maintenance_request_graph.js',
			'gmao_suite/static/src/css/maintenance_request_form_view.js',
			'gmao_suite/static/src/css/maintenance_request_analysis_report.js',
			'gmao_suite/static/src/js/maintenance_team_chart.js',
			'gmao_suite/static/src/css/maintenance_parts_used_graph.js',
        ],
    },
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
