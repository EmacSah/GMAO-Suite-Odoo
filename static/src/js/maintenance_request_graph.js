odoo.define('gmao_suite.maintenance_request_graph', function (require) {
    "use strict";

    // Fonction pour télécharger les données en tant que fichier
    function download(dataurl, filename) {
        var a = document.createElement("a");
        a.href = dataurl;
        a.setAttribute("download", filename);
        a.click();
    }

    // Importation des modules nécessaires d'Odoo
    var core = require('web.core');
    var GraphView = require('web.GraphView');
    var GraphModel = require('web.GraphModel');
    var GraphRenderer = require('web.GraphRenderer');
    var GraphController = require('web.GraphController');
    var viewRegistry = require('web.view_registry');
    var _t = core._t;

    // Définition des états de maintenance avec traductions
    var MAINTENANCE_STATES = {
        new: _t('New'),
        to_validate: _t('To Validate'),
        in_progress: _t('In Progress'),
        repaired: _t('Repaired'),
        done: _t('Done'),
        cancel: _t('Cancelled')
    };

    // Extension du GraphController pour créer un contrôleur personnalisé
    var MaintenanceRequestGraphController = GraphController.extend({
        // Extension des événements pour inclure des gestionnaires personnalisés
        events: _.extend({}, GraphController.prototype.events, {
            'click .o_graph_export': '_onExportClick',
            'click .o_graph_zoom_in': '_onZoomInClick',
            'click .o_graph_zoom_out': '_onZoomOutClick',
            'click .o_graph_export_png': '_onExportPNG',
            'click .o_graph_next_page': '_onNextPageClick',
            'click .o_graph_prev_page': '_onPrevPageClick'
        }),

        // Méthode pour gérer le changement de type de graphique
        _onChangeChartType: function (ev) {
            var chartType = $(ev.currentTarget).val();
            this.renderer.updateChartType(chartType);
        },

        // Rendu des boutons dans le panneau de contrôle
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            // Ajout du bouton Exporter en PNG
            $node.append($('<button class="btn btn-secondary o_graph_export_png">' + _t("Export PNG") + '</button>'));
            // Ajout du sélecteur de type de graphique
            var $chartTypeSelector = $('<select class="o_chart_type_selector">')
                .append($('<option>', {value: 'bar', text: _t("Bar Chart")}))
                .append($('<option>', {value: 'line', text: _t("Line Chart")}))
                .append($('<option>', {value: 'pie', text: _t("Pie Chart")}));
            $chartTypeSelector.on('change', this._onChangeChartType.bind(this));
            $node.append($chartTypeSelector);

            // Ajout des boutons de pagination
            var $pagination = $('<div class="o_graph_pagination">')
                .append($('<button class="btn btn-secondary o_graph_prev_page">' + _t("Previous") + '</button>'))
                .append($('<button class="btn btn-secondary o_graph_next_page">' + _t("Next") + '</button>'));
            $node.append($pagination);
        },

        // Méthode pour gérer les erreurs
        _onError: function (error) {
            var errorMessage = error.message || _t("An unknown error occurred");
            var errorDetails = error.data && error.data.debug ? error.data.debug : '';

            // Enregistrement de l'erreur pour le débogage
            console.error("Maintenance Request Graph Error:", error);

            // Affichage d'une notification d'erreur détaillée
            this.do_warn(_t("Error"), errorMessage, {
                type: 'danger',
                sticky: true,
                title: _t("Maintenance Request Graph Error"),
            });

            // Si des détails sont disponibles, les afficher dans une boîte de dialogue
            if (errorDetails) {
                var $errorDialog = $('<div>').html(errorDetails);
                new Dialog(this, {
                    title: _t("Error Details"),
                    $content: $errorDialog,
                    buttons: [{text: _t("OK"), close: true}]
                }).open();
            }

            // Tenter de récupérer en rechargeant les données
            this.reload();
        },

        // Méthode pour gérer l'exportation en PNG
        _onExportPNG: function () {
            var svgElement = this.renderer.$('svg')[0];
            if (!svgElement) {
                this.do_warn(_t("Error"), _t("No SVG element found to export."));
                return;
            }
            var svgString = new XMLSerializer().serializeToString(svgElement);
            var canvas = document.createElement("canvas");
            canvas.width = this.renderer.$('svg').width();
            canvas.height = this.renderer.$('svg').height();
            var ctx = canvas.getContext("2d");
            var img = new Image();
            img.onload = function() {
                ctx.drawImage(img, 0, 0);
                var pngFile = canvas.toDataURL("image/png");
                download(pngFile, "maintenance_graph.png");
            };
            img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svgString);
        },

        // Méthode pour gérer le clic sur le bouton d'exportation
        _onExportClick: function () {
            var self = this;
            this._rpc({
                model: 'maintenance.request',
                method: 'export_graph_data',
                args: [this.modelParams.domain, this.modelParams.groupBy],
            }).then(function (result) {
                var blob = new Blob([result], {type: 'text/csv;charset=utf-8;'});
                var link = document.createElement("a");
                if (link.download !== undefined) {
                    var url = URL.createObjectURL(blob);
                    link.setAttribute("href", url);
                    link.setAttribute("download", "maintenance_graph_data.csv");
                    link.style.visibility = 'hidden';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
            }).guardedCatch(function (error) {
                self._onError(error);
            });
        },

        // Méthodes pour gérer le zoom avant et arrière
        _onZoomInClick: function () {
            this.renderer.zoomIn();
        },

        _onZoomOutClick: function () {
            this.renderer.zoomOut();
        },

        // Méthodes pour gérer la pagination
        _onNextPageClick: function () {
            var self = this;
            this.model.nextPage().then(function () {
                self.model.loadTableData(self.modelParams).then(function () {
                    self.renderer.renderTable();
                });
            });
        },

        _onPrevPageClick: function () {
            var self = this;
            this.model.previousPage().then(function () {
                self.model.loadTableData(self.modelParams).then(function () {
                    self.renderer.renderTable();
                });
            });
        },

    });

    // Extension du GraphRenderer pour créer un renderer personnalisé
    var MaintenanceRequestGraphRenderer = GraphRenderer.extend({
        // Extension des événements pour inclure les gestionnaires de changement d'axe
        events: _.extend({}, GraphRenderer.prototype.events, {
            'change .o_graph_x_axis': '_onAxisChange',
            'change .o_graph_y_axis': '_onAxisChange',
        }),

        // Définition des labels et couleurs des états
        stateLabels: {
            'new': _t('New'),
            'to_validate': _t('To Validate'),
            'in_progress': _t('In Progress'),
            'repaired': _t('Repaired'),
            'done': _t('Done'),
            'cancel': _t('Cancelled')
        },

        stateColors: {
            'new': '#3498db',
            'to_validate': '#f1c40f',
            'in_progress': '#e67e22',
            'repaired': '#2ecc71',
            'done': '#27ae60',
            'cancel': '#e74c3c'
        },

        // Initialisation du renderer
        init: function () {
            this._super.apply(this, arguments);
            this.zoomLevel = 1;
        },

        // Rendu du graphique
        _renderChart: function () {
            var self = this;

            return this._super.apply(this, arguments).then(function () {
                // Vérification de l'intégrité des données
                if (!self._checkDataIntegrity(self.state.data)) {
                    return;
                }

                // Personnalisation de l'infobulle
                self.chart.tooltip.contentGenerator(function (d) {
                    var tooltip = "<h3>" + d.data.name + "</h3>";
                    tooltip += "<p>" + _t("Value") + ": " + d.data.value + "</p>";
                    return tooltip;
                });

                // Définition de la couleur basée sur l'état
                self.chart.color(function (d) {
                    return self.stateColors[d.state] || '#95a5a6';
                });

                // Ajout d'une interaction lors du clic sur les éléments
                self.chart.interactiveLayer.dispatch.on("elementClick", function (e) {
                    self._loadDetails(e.data);
                });

                // Ajout de la légende
                var $legend = $('<div class="o_graph_legend">');
                _.each(self.stateColors, function (color, state) {
                    $legend.append($('<div class="o_legend_item">')
                        .append($('<span class="o_legend_color">').css('background-color', color))
                        .append($('<span class="o_legend_label">').text(self.stateLabels[state] || state))
                    );
                });
                self.$el.append($legend);

                // Rendu initial du tableau paginé
                self.renderTable();
            });
        },

        // Vérification de l'intégrité des données
        _checkDataIntegrity: function (data) {
            var errors = [];
            _.each(data, function (item) {
                if (!item.name || !item.state) {
                    errors.push(_t("Incomplete data for item: ") + (item.id || _t("Unknown")));
                }
            });
            if (errors.length) {
                this.getParent()._onError({ message: errors.join("\n") });
                return false;
            }
            return true;
        },

        // Mise à jour du type de graphique
        updateChartType: function (chartType) {
			// Vérifier si le type de graphique est pris en charge
			if (['bar', 'line', 'pie'].includes(chartType)) {
				// Mettre à jour le type de graphique dans la configuration du graphique
					this.chart.type(chartType);
				// Actualiser le graphique avec le nouveau type
			this.chart.update();
				} else {
					// Afficher une alerte si le type de graphique n'est pas valide
					this.getParent()._onError({ message: _t("Invalid chart type selected: ") + chartType });
				}
		}


        // Zoom avant sur le graphique
        zoomIn: function () {
            this.zoomLevel *= 1.1;
            this._applyZoom();
        },

        // Zoom arrière sur le graphique
        zoomOut: function () {
            this.zoomLevel /= 1.1;
            this._applyZoom();
        },

        // Application du niveau de zoom au graphique
        _applyZoom: function () {
            this.chart.scale(this.zoomLevel);
            this.chart.update();
        },

        // Chargement des détails lorsqu'un élément est cliqué
        _loadDetails: function (data) {
            var self = this;
            this._rpc({
                model: 'maintenance.request',
                method: 'read',
                args: [[data.id]],
                kwargs: { fields: ['name', 'state', 'maintenance_type', 'duration', 'total_cost', 'mttr', 'mtbf', 'downtime'] }
            }).then(function (result) {
                self._displayDetails(result[0]);
            }).guardedCatch(function (error) {
                self.getParent()._onError(error);
            });
        },

        // Affichage des détails d'un élément
        _displayDetails: function (data) {
            var $detailsTable = this.$el.find('.maintenance-details');
            if (!$detailsTable.length) {
                $detailsTable = $('<table class="table table-sm maintenance-details"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody></tbody></table>');
                this.$el.append($detailsTable);
            }
            var $tbody = $detailsTable.find('tbody').empty();
            _.each(data, function (value, key) {
                $tbody.append($('<tr>').append($('<td>').text(key)).append($('<td>').text(value)));
            });
        },

        // Gestion des événements de changement d'axe
        _onAxisChange: function (ev) {
            var $target = $(ev.target);
            var axis = $target.hasClass('o_graph_x_axis') ? 'x' : 'y';
            var index = $target.index() - 1;
            var fieldName = $target.val();
            this.trigger_up('field_changed', {
                fieldName: axis + 'FieldNames[' + index + ']',
                value: fieldName,
            });
        },

        // Rendu du tableau paginé
        renderTable: function () {
            var self = this;
            var data = this.state.tableData || [];
            var $table = this.$el.find('.maintenance-data-table');
            if (!$table.length) {
                $table = $('<table class="table maintenance-data-table"><thead><tr></tr></thead><tbody></tbody></table>');
                this.$el.append($table);
            }
            var $thead = $table.find('thead tr').empty();
            var $tbody = $table.find('tbody').empty();

            // Ajouter les en-têtes
            if (data.length > 0) {
                var fields = Object.keys(data[0]);
                fields.forEach(function (field) {
                    $thead.append($('<th>').text(field));
                });

                // Ajouter les lignes de données
                data.forEach(function (record) {
                    var $tr = $('<tr>');
                    fields.forEach(function (field) {
                        $tr.append($('<td>').text(record[field]));
                    });
                    $tbody.append($tr);
                });
            }
        },

    });

    // Définition du GraphModel personnalisé
    var MaintenanceRequestGraphModel = GraphModel.extend({

        // Méthode de chargement surchargée
        __load: function (params) {
            var self = this;
            params = _.extend({}, params, {
                limit: this.loadParams.limit,
                offset: this.loadParams.offset || 0
            });
            // Charger les données du graphique
            return this._rpc({
                model: this.modelName,
                method: 'get_graph_data',
                args: [params.domain, params.groupBy, params.measure, params.xFields, params.yFields],
            }).then(function (result) {
                self.data = result.data;
                self.totalCount = result.total_count;
                self.state.data = result.data;
                // Charger les données du tableau
                return self.loadTableData(params);
            });
        },

        // Méthode pour charger les données du tableau paginé
        loadTableData: function (params) {
            var self = this;
            params = _.extend({}, params, {
                limit: this.loadParams.limit,
                offset: this.loadParams.offset || 0
            });
            return this._rpc({
                model: this.modelName,
                method: 'get_table_data',
                args: [params.domain, params.groupBy, params.fields],
                kwargs: {
                    limit: params.limit,
                    offset: params.offset,
                },
            }).then(function (result) {
                self.tableData = result.data;
                self.totalCount = result.total_count;
                self.state.tableData = result.data;
                return result;
            });
        },

        // Méthodes pour la pagination
        nextPage: function () {
            this.loadParams.offset += this.loadParams.limit;
            return Promise.resolve();
        },

        previousPage: function () {
            this.loadParams.offset = Math.max(0, this.loadParams.offset - this.loadParams.limit);
            return Promise.resolve();
        },

        // Méthode reload pour s'assurer que groupBy est limité à 3 champs
        __reload: function (handle, params) {
            if (params.groupBy && params.groupBy.length > 3) {
                params.groupBy = params.groupBy.slice(0, 3);
            }
            return this._super(handle, params);
        },
    });

    // Définition de la GraphView personnalisée
    var MaintenanceRequestGraphView = GraphView.extend({
        config: _.extend({}, GraphView.prototype.config, {
            Controller: MaintenanceRequestGraphController,
            Renderer: MaintenanceRequestGraphRenderer,
            Model: MaintenanceRequestGraphModel,
        }),

        init: function () {
            this._super.apply(this, arguments);
            this.loadParams.limit = 10;  // Limite pour la pagination
        },
		
		changeGraphType: function(type) {
			this.renderer.updateChartType(type);
		},
    });

    // Enregistrement de la vue
    viewRegistry.add('maintenance_request_graph', MaintenanceRequestGraphView);

    return MaintenanceRequestGraphView;
});
