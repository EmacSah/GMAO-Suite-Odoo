odoo.define('gmao_suite.ConsumptionChartWidget', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var registry = require('web.field_registry');
    var core = require('web.core');
    var _t = core._t;

    var ConsumptionChartWidget = AbstractField.extend({
        template: 'ConsumptionChartWidget',

        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.chartInstance = null;
        },

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._renderChart();
            });
        },

        /**
         * @override
         */
        destroy: function () {
            if (this.chartInstance) {
                this.chartInstance.destroy();
            }
            this._super.apply(this, arguments);
        },

        /**
         * Render the chart using Chart.js
         * @private
         */
        _renderChart: function () {
            console.log("Rendering chart", this.value);
            
            var self = this;
            var chartData;
            
            try {
                chartData = JSON.parse(this.value);
            } catch (e) {
                chartData = this.value;
            }

            if (chartData === 'no_data' || chartData === _t("Aucune donnée à afficher")) {
                this.$el.html('<p>' + _t("Aucune donnée à afficher. Veuillez remplir le formulaire.") + '</p>');
                return;
            }

            var ctx = this.$el.find('canvas')[0].getContext('2d');

            // Fetch historical data
            this._rpc({
                model: 'maintenance.efficacite.energetique',
                method: 'get_historical_data',
                args: [this.res_id],
            }).then(function (data) {
                // Vérification si les données sont valides
                var hasValidData = data.consumptions.some(value => value !== 0) || 
                                  (Array.isArray(data.savings) && data.savings.length > 0 && 
                                   data.savings.some(value => value !== 0));

                if (hasValidData) {
                    // Si les données sont valides, afficher le graphique
                    self.chartInstance = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: data.labels,
                            datasets: [{
                                label: _t('Consommation (kWh)'),
                                data: data.consumptions,
                                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1
                            }, {
                                label: _t('Économies (kWh)'),
                                data: data.savings,
                                backgroundColor: 'rgba(255, 159, 64, 0.6)',
                                borderColor: 'rgba(255, 159, 64, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            title: {
                                display: true,
                                text: _t('Historique de consommation et économies')
                            },
                            scales: {
                                yAxes: [{
                                    ticks: {
                                        beginAtZero: true
                                    }
                                }]
                            }
                        }
                    });

                    // Render pie chart for current vs previous consumption
                    var pieCtx = self.$el.find('#consumptionPieChart')[0].getContext('2d');
                    new Chart(pieCtx, {
                        type: 'pie',
                        data: {
                            labels: [_t('Consommation précédente'), _t('Consommation actuelle')],
                            datasets: [{
                                data: [self.record.data.previous_consumption, self.record.data.energy_consumption],
                                backgroundColor: ['rgba(255, 99, 132, 0.6)', 'rgba(54, 162, 235, 0.6)'],
                                borderColor: ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)'],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            title: {
                                display: true,
                                text: _t('Comparaison des consommations')
                            }
                        }
                    });
                } else {
                    // Si les données ne sont pas valides, afficher un message d'indication
                    self.$el.html('<p>' + _t("Pas de données disponibles pour afficher le graphique") + '</p>');
                }
            }).catch(function () {
                // En cas d'erreur dans la récupération des données, afficher un message d'erreur
                self.$el.html('<p>' + _t("Erreur lors de la récupération des données. Veuillez réessayer plus tard.") + '</p>');
            });
        },
    });

    registry.add('consumption_chart', ConsumptionChartWidget);

    return ConsumptionChartWidget;
});