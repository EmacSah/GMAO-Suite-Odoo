// Définition du module Odoo pour le graphique des équipes de maintenance
odoo.define('gmao_suite.maintenance_team_chart', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var _t = core._t;

    // Définition du widget MaintenanceTeamChart
    var MaintenanceTeamChart = Widget.extend({
        template: 'MaintenanceTeamChartTemplate',

        /**
         * Initialisation du widget
         * @override
         * @param {Widget} parent Le widget parent
         * @param {Object} data Les données pour le graphique
         */
        init: function (parent, data) {
            this._super(parent);
            this.data = data;
        },

        /**
         * Démarrage du widget
         * @override
         */
        start: function () {
            var self = this;
            return this._super().then(function () {
                self._renderChart();
            });
        },

        /**
         * Rendu du graphique ou affichage d'un message si pas de données
         * @private
         */
        _renderChart: function () {
            var self = this;
            var $chart = this.$('.o_maintenance_team_chart');

            // Vérification de la présence de données
            if (!this.data || !this.data.labels || this.data.labels.length === 0) {
                $chart.text(_t("Aucune donnée à afficher"));
                return;
            }

            try {
                // Création du graphique avec Chart.js
                var ctx = $chart[0].getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: this.data.labels,
                        datasets: [{
                            label: _t('Taux de réussite'),
                            data: this.data.success_rates,
                            backgroundColor: 'rgba(75, 192, 192, 0.6)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }, {
                            label: _t('Charge de travail'),
                            data: this.data.workloads,
                            backgroundColor: 'rgba(255, 159, 64, 0.6)',
                            borderColor: 'rgba(255, 159, 64, 1)',
                            borderWidth: 1
                        }, {
                            label: _t('Taux d\'occupation'),
                            data: this.data.occupation_rates,
                            backgroundColor: 'rgba(54, 162, 235, 0.6)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            yAxes: [{
                                ticks: {
                                    beginAtZero: true,
                                    callback: function(value) {
                                        return value + '%';
                                    }
                                }
                            }]
                        },
                        tooltips: {
                            callbacks: {
                                label: function(tooltipItem, data) {
                                    var label = data.datasets[tooltipItem.datasetIndex].label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    label += tooltipItem.yLabel + '%';
                                    return label;
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error(_t("Erreur lors de la création du graphique:"), error);
                $chart.text(_t("Erreur lors de la création du graphique. Veuillez réessayer plus tard ou contacter le support technique."));
            }
        },
    });

    // Ajout de l'action au registre des actions Odoo
    core.action_registry.add('maintenance_team_chart', MaintenanceTeamChart);

    return MaintenanceTeamChart;
});