odoo.define('gmao_suite.maintenance_request_widgets', function (require) {
    "use strict";
    
    var core = require('web.core');
    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');
    var QWeb = core.qweb;
    
    var StatusColorWidget = AbstractField.extend({
        template: 'StatusColorWidget',
        events: {
            'click .status-dot': '_onStatusClick',
        },
    
        init: function () {
            this._super.apply(this, arguments);
            this.stateColors = {
                'new': '#3498db',
                'in_progress': '#f1c40f',
                'repaired': '#2ecc71',
                'done': '#27ae60',
                'cancel': '#e74c3c'
            };
        },
    
        _render: function () {
            this.$el.html(QWeb.render('StatusColorWidget', {
                status: this.value,
                color: this.stateColors[this.value] || '#95a5a6'
            }));
        },
    
        _onStatusClick: function (ev) {
            // Logique pour changer le statut si nécessaire
        }
    });
    
    var DynamicPriorityWidget = AbstractField.extend({
        template: 'DynamicPriorityWidget',
        events: {
            'click .priority-star': '_onPriorityClick',
        },
    
        _render: function () {
            this.$el.html(QWeb.render('DynamicPriorityWidget', {
                priority: this.value,
                max_priority: 4  // Assurez-vous que cela correspond à votre échelle de priorité
            }));
        },
    
        _onPriorityClick: function (ev) {
            var newPriority = $(ev.currentTarget).data('priority');
            this._setValue(newPriority.toString());
        }
    });
    
    var TimerWidget = AbstractField.extend({
        template: 'TimerWidget',
    
        init: function () {
            this._super.apply(this, arguments);
            this.duration = 0;
            this.intervalId = null;
        },
    
        start: function () {
            this._super.apply(this, arguments);
            this._startTimer();
        },
    
        _startTimer: function () {
            var self = this;
            this.intervalId = setInterval(function () {
                self._rpc({
                    model: 'maintenance.request',
                    method: 'get_current_duration',
                    args: [self.res_id],
                }).then(function (duration) {
                    self.duration = duration;
                    self._render();
                });
            }, 1000);
        },
    
        _render: function () {
            this.$el.html(QWeb.render('TimerWidget', {
                duration: this._formatDuration(this.duration)
            }));
        },
    
        _formatDuration: function (duration) {
            var hours = Math.floor(duration);
            var minutes = Math.floor((duration - hours) * 60);
            return hours + 'h ' + minutes + 'm';
        },
    
        destroy: function () {
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
            this._super.apply(this, arguments);
        }
    });
    
    var RealTimeCostWidget = AbstractField.extend({
        template: 'RealTimeCostWidget',
    
        init: function () {
            this._super.apply(this, arguments);
            this.totalCost = 0;
        },
    
        _render: function () {
            var self = this;
            this._rpc({
                model: 'maintenance.request',
                method: 'read',
                args: [[this.res_id], ['total_parts_cost', 'labor_cost', 'total_cost']],
            }).then(function (result) {
                self.totalCost = result[0].total_cost;
                self.$el.html(QWeb.render('RealTimeCostWidget', {
                    totalCost: self.totalCost.toFixed(2)
                }));
            });
        }
    });
    
    var StateHistoryWidget = AbstractField.extend({
        template: 'StateHistoryWidget',
    
        _render: function () {
            var self = this;
            this._rpc({
                model: 'maintenance.request.state.history',
                method: 'search_read',
                domain: [['request_id', '=', this.res_id]],
                fields: ['old_state', 'new_state', 'change_date', 'user_id'],
                order: 'change_date desc'
            }).then(function (history) {
                self.$el.html(QWeb.render('StateHistoryWidget', {
                    history: history
                }));
            });
        }
    });
    
    var MaintenanceKPIWidget = AbstractField.extend({
        template: 'MaintenanceKPIWidget',
    
        _render: function () {
            var self = this;
            this._rpc({
                model: 'maintenance.request',
                method: 'get_maintenance_kpis',
                args: [this.res_id],
            }).then(function (kpis) {
                self.$el.html(QWeb.render('MaintenanceKPIWidget', {
                    kpis: kpis
                }));
            });
        }
    });
    
    fieldRegistry.add('status_color', StatusColorWidget);
    fieldRegistry.add('dynamic_priority', DynamicPriorityWidget);
    fieldRegistry.add('maintenance_timer', TimerWidget);
    fieldRegistry.add('real_time_cost', RealTimeCostWidget);
    fieldRegistry.add('state_history', StateHistoryWidget);
    fieldRegistry.add('maintenance_kpi', MaintenanceKPIWidget);
    
    return {
        StatusColorWidget: StatusColorWidget,
        DynamicPriorityWidget: DynamicPriorityWidget,
        TimerWidget: TimerWidget,
        RealTimeCostWidget: RealTimeCostWidget,
        StateHistoryWidget: StateHistoryWidget,
        MaintenanceKPIWidget: MaintenanceKPIWidget
    };
    
    });