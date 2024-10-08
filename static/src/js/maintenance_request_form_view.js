odoo.define('gmao_suite.maintenance_request_form', function (require) {
    "use strict";

    var core = require('web.core');
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');
    var viewRegistry = require('web.view_registry');

    var _t = core._t;

    var MaintenanceRequestFormController = FormController.extend({
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            open_kpi_dashboard: '_onOpenKPIDashboard',
        }),

        _onOpenKPIDashboard: function (ev) {
            var self = this;
            this._rpc({
                model: 'maintenance.request',
                method: 'get_maintenance_kpis',
                args: [this.model.get(this.handle).res_id],
            }).then(function (result) {
                self.do_action({
                    name: _t('Maintenance KPI Dashboard'),
                    type: 'ir.actions.act_window',
                    res_model: 'maintenance.kpi.dashboard',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {
                        'default_kpi_data': JSON.stringify(result),
                    },
                });
            });
        },

        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$buttons.on('click', '.o_maintenance_start_timer', this._onStartTimer.bind(this));
                this.$buttons.on('click', '.o_maintenance_stop_timer', this._onStopTimer.bind(this));
            }
        },

        _onStartTimer: function () {
            this._rpc({
                model: 'maintenance.request',
                method: 'action_start_timer',
                args: [this.model.get(this.handle).res_id],
            }).then(this.reload.bind(this));
        },

        _onStopTimer: function () {
            this._rpc({
                model: 'maintenance.request',
                method: 'action_stop_timer',
                args: [this.model.get(this.handle).res_id],
            }).then(this.reload.bind(this));
        },

        _updateButtons: function () {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                var state = this.model.get(this.handle).data.state;
                this.$buttons.find('.o_maintenance_start_timer').toggle(state === 'new');
                this.$buttons.find('.o_maintenance_stop_timer').toggle(state === 'in_progress');
            }
        },
    });

    var MaintenanceRequestFormRenderer = FormRenderer.extend({
        _renderStatButton: function (elem) {
            var $button = this._super.apply(this, arguments);
            if (elem.tag === 'button' && elem.attrs.class === 'oe_stat_button o_maintenance_kpi_dashboard') {
                $button.on('click', this._onKPIDashboardClick.bind(this));
            }
            return $button;
        },

        _onKPIDashboardClick: function (ev) {
            ev.preventDefault();
            this.trigger_up('open_kpi_dashboard');
        },
    });

    var MaintenanceRequestFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: MaintenanceRequestFormController,
            Renderer: MaintenanceRequestFormRenderer,
        }),
    });

    viewRegistry.add('maintenance_request_form', MaintenanceRequestFormView);

    return MaintenanceRequestFormView;
});