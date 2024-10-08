odoo.define('gmao_suite.MaintenancePartsUsedGraph', function (require) {
    "use strict";

    var core = require('web.core');
    var GraphView = require('web.GraphView');
    var GraphModel = require('web.GraphModel');
    var GraphRenderer = require('web.GraphRenderer');
    var dialogs = require('web.view_dialogs');
    var _t = core._t;

    var MaintenancePartsUsedGraphRenderer = GraphRenderer.extend({
        events: _.extend({}, GraphRenderer.prototype.events, {
            'click .customize-graph': '_onCustomizeGraph',
        }),

        /**
         * @override
         */
        _renderGraph: function () {
            var self = this;
            this._super.apply(this, arguments);

            if (this.state.data.length === 0) {
                this.$el.append($('<p>').addClass('no-data').text(_t("Aucune donnée à afficher")));
                return;
            }

            // Ajoute un bouton pour personnaliser le graphique
            var $customizeButton = $('<button>')
                .addClass('btn btn-primary customize-graph')
                .text(_t("Personnaliser le graphique"));
            this.$el.prepend($customizeButton);

            // Ajoute des tooltips détaillés
            this.$('svg .nv-series, .nv-bar, .nv-slice').tooltip({
                title: function () {
                    var data = $(this).data('originalValues');
                    if (!data) return '';
                    return self._formatTooltip(data);
                },
                html: true,
                container: 'body'
            });
        },

        _formatTooltip: function (data) {
            var tooltip = '<div class="graph-tooltip">';
            tooltip += '<p><strong>' + _t("Pièce") + ':</strong> ' + data.label + '</p>';
            tooltip += '<p><strong>' + _t("Quantité") + ':</strong> ' + data.value + '</p>';
            tooltip += '<p><strong>' + _t("Coût total") + ':</strong> ' + data.cost + '</p>';
            tooltip += '<p><strong>' + _t("Interventions") + ':</strong> ' + data.interventions + '</p>';
            tooltip += '<p><strong>' + _t("État") + ':</strong> ' + data.state + '</p>';
            tooltip += '<p><strong>' + _t("Stock minimum") + ':</strong> ' + data.min_stock + '</p>';
            tooltip += '<p><strong>' + _t("Technicien") + ':</strong> ' + data.technician + '</p>';
            tooltip += '<p><strong>' + _t("Date de retrait") + ':</strong> ' + data.withdrawal_date + '</p>';
            tooltip += '</div>';
            return tooltip;
        },

        _onCustomizeGraph: function () {
            var self = this;
            new dialogs.FormViewDialog(this, {
                res_model: 'maintenance.graph.wizard',
                title: _t("Personnaliser le graphique"),
                on_saved: function (record) {
                    var data = record.data;
                    self.trigger_up('graph_customized', {
                        measure: data.measure,
                        groupBy: data.groupby,
                        graphType: data.graph_type
                    });
                },
            }).open();
        },
    });

    var MaintenancePartsUsedGraphModel = GraphModel.extend({
        /**
         * @override
         */
        _prepareData: function () {
            var self = this;
            var result = this._super.apply(this, arguments);

            try {
                // Calculs supplémentaires
                var totalQuantity = _.reduce(result.data, function (memo, datum) {
                    return memo + datum.value;
                }, 0);
                var totalCost = _.reduce(result.data, function (memo, datum) {
                    return memo + (datum.value * datum.cost);
                }, 0);
                var avgCost = totalCost / totalQuantity;

                // Ajout des statistiques au résultat
                result.stats = {
                    totalQuantity: totalQuantity,
                    totalCost: totalCost,
                    avgCost: avgCost,
                    totalInterventions: _.reduce(result.data, function (memo, datum) {
                        return memo + datum.interventions;
                    }, 0),
                };

                // Création d'un tableau de données pour l'affichage
                result.tableData = _.map(result.data, function (datum) {
                    return {
                        label: datum.label,
                        quantity: datum.value,
                        cost: datum.cost,
                        totalCost: datum.value * datum.cost,
                        interventions: datum.interventions,
                        state: datum.state,
                        min_stock: datum.min_stock,
                        technician: datum.technician,
                        withdrawal_date: datum.withdrawal_date,
                        percentageOfTotal: (datum.value / totalQuantity) * 100
                    };
                });

                console.table(result.tableData);
            } catch (error) {
                console.error("Erreur lors de la préparation des données:", error);
                result.error = _t("Une erreur s'est produite lors de la préparation des données.");
            }

            return result;
        },
    });

    var MaintenancePartsUsedGraphView = GraphView.extend({
        config: _.extend({}, GraphView.prototype.config, {
            Model: MaintenancePartsUsedGraphModel,
            Renderer: MaintenancePartsUsedGraphRenderer,
        }),

        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.controllerParams.customizeGraph = true;
        },

        /**
         * @override
         */
        _onGraphCustomized: function (ev) {
            var options = ev.data;
            this.update(options);
        },
    });

    // Enregistre la vue personnalisée
    core.action_registry.add('maintenance_parts_used_graph', MaintenancePartsUsedGraphView);

    return MaintenancePartsUsedGraphView;
});